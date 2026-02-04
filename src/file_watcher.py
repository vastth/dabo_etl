from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config_loader import load_default_config
from .db_handler import DatabaseHandler
from .etl_processor import EtlProcessor
from .logger import get_logger


@dataclass
class WatcherConfig:
    watch_paths: List[str]
    processed_path: str
    poll_interval: float = 1.0


class CsvHandler(FileSystemEventHandler):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__()
        self.config = config
        self.logger = get_logger()
        self.db = DatabaseHandler(config)
        self.etl = EtlProcessor(config, self.db)
        self.hash_store_path = os.path.join("temp", "file_hashes.json")
        self._in_progress: set[str] = set()

    def _is_csv(self, path: str) -> bool:
        return path.lower().endswith(".csv")

    def _is_valid_filename(self, file_path: str) -> bool:
        name = os.path.basename(file_path)
        if not re.match(r"^dabo_\d{8}\.csv$", name):
            return False
        try:
            datetime.strptime(name[5:13], "%Y%m%d")
        except ValueError:
            return False
        return True

    def on_created(self, event) -> None:
        if event.is_directory:
            return

        file_path = event.src_path
        if not self._is_csv(file_path):
            return

        if file_path in self._in_progress:
            self.logger.info("Skip duplicate event: %s", file_path)
            return

        self.logger.info("Detected new CSV: %s", file_path)
        self._in_progress.add(file_path)
        try:
            if self._wait_for_ready(file_path):
                self.process_file(file_path)
            else:
                if not os.path.exists(file_path):
                    self.logger.info("File disappeared before processing: %s", file_path)
                else:
                    self.logger.warning("File not ready after retries: %s", file_path)
        finally:
            self._in_progress.discard(file_path)

    def process_file(self, file_path: str) -> None:
        started_at = datetime.now()
        file_size = None
        if os.path.exists(file_path):
            try:
                file_size = os.path.getsize(file_path)
            except OSError:
                file_size = None
        log_data: Dict[str, Any] = {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "status": "FAILED",
            "started_at": started_at,
            "records_total": 0,
            "records_after_filter": 0,
            "records_inserted": 0,
        }

        if not self._is_valid_filename(file_path):
            log_data["status"] = "REJECTED_NAME"
            log_data["message"] = "Invalid file name"
            log_data["finished_at"] = datetime.now()
            self.logger.warning("Rejected file name: %s", file_path)
            self._move_to_quarantine(file_path, suffix="bad_name")
            self._safe_log_import(log_data)
            return

        if not self._wait_for_ready(file_path):
            if not os.path.exists(file_path):
                log_data["status"] = "SKIPPED_MISSING"
                log_data["message"] = "File missing"
                log_data["finished_at"] = datetime.now()
                self.logger.info("File missing before processing: %s", file_path)
                self._safe_log_import(log_data)
                return

            log_data["status"] = "RETRY_TIMEOUT"
            log_data["message"] = "File not ready (locked)"
            log_data["finished_at"] = datetime.now()
            self.logger.warning("File not ready for processing: %s", file_path)
            self._move_to_quarantine(file_path, suffix="locked")
            self._safe_log_import(log_data)
            return

        file_hash = self._compute_hash(file_path)
        if self._is_duplicate_hash(file_hash):
            log_data["status"] = "SKIPPED_DUPLICATE"
            log_data["message"] = "Duplicate file hash"
            log_data["finished_at"] = datetime.now()
            self.logger.warning("Skipped duplicate file: %s", file_path)
            self._move_to_processed(file_path)
            self._safe_log_import(log_data)
            return

        retry_cfg = self.config.get("etl", {})
        max_retries = int(retry_cfg.get("retry_count", 0))
        delay = float(retry_cfg.get("retry_delay_seconds", 1))

        attempt = 0
        while True:
            try:
                df_valid, meta = self.etl.process_file(file_path)
                log_data.update(meta)

                delete_days = int(self.config.get("etl", {}).get("delete_days", 60))
                self.db.delete_recent_data(delete_days)

                inserted = self.db.insert_dabo_data(df_valid, file_path)
                log_data["records_inserted"] = inserted
                log_data["status"] = "SUCCESS"
                log_data["finished_at"] = datetime.now()

                duration_ms = int((log_data["finished_at"] - started_at).total_seconds() * 1000)
                metric_msg = f"duration_ms={duration_ms}"
                if file_size is not None:
                    metric_msg += f", file_size={file_size}"
                metric_msg += f", retries={attempt}"
                log_data["message"] = metric_msg

                self.logger.info(
                    "Processed CSV: %s, inserted: %s, %s", file_path, inserted, metric_msg
                )
                self._move_to_processed(file_path)
                self._save_hash(file_hash)
                break
            except (PermissionError, OSError, IOError) as exc:
                if attempt < max_retries:
                    attempt += 1
                    self.logger.warning(
                        "Retry %s/%s after error: %s", attempt, max_retries, exc
                    )
                    time.sleep(delay * attempt)
                    continue
                log_data["message"] = str(exc)
                log_data["finished_at"] = datetime.now()
                self.logger.exception("Failed processing after retries: %s", file_path)
                self._move_to_quarantine(file_path, suffix="error")
                break
            except Exception as exc:  # noqa: BLE001
                log_data["message"] = str(exc)
                log_data["finished_at"] = datetime.now()
                self.logger.exception("Failed processing: %s", file_path)
                self._move_to_quarantine(file_path, suffix="error")
                break
        self._safe_log_import(log_data)

    def _safe_log_import(self, log_data: Dict[str, Any]) -> None:
        try:
            self.db.log_import_record(log_data)
        except Exception:  # noqa: BLE001
            self.logger.exception("Failed to write import log")

    def _compute_hash(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _wait_for_ready(self, file_path: str, retries: int = 10, delay: float = 1.0) -> bool:
        for _ in range(retries):
            try:
                with open(file_path, "rb"):
                    return True
            except PermissionError:
                time.sleep(delay)
            except FileNotFoundError:
                time.sleep(delay)
        return False

    def _load_hash_store(self) -> Dict[str, Any]:
        if not os.path.exists(self.hash_store_path):
            return {}
        try:
            with open(self.hash_store_path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:  # noqa: BLE001
            return {}

    def _save_hash(self, file_hash: str) -> None:
        os.makedirs(os.path.dirname(self.hash_store_path), exist_ok=True)
        store = self._load_hash_store()
        store[file_hash] = {
            "processed_at": datetime.now().isoformat(timespec="seconds"),
        }
        with open(self.hash_store_path, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)

    def _is_duplicate_hash(self, file_hash: str) -> bool:
        store = self._load_hash_store()
        return file_hash in store

    def _move_to_quarantine(self, file_path: str, suffix: str) -> None:
        quarantine_dir = self.config.get("nas", {}).get("quarantine_path")
        if not quarantine_dir:
            return

        os.makedirs(quarantine_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_name = f"dabo_data_{ts}_{suffix}.csv"
        target_path = os.path.join(quarantine_dir, target_name)
        shutil.move(file_path, target_path)
        self.logger.info("Moved to quarantine: %s", target_path)

    def _move_to_processed(self, file_path: str) -> None:
        processed_dir = self.config.get("nas", {}).get("processed_path")
        if not processed_dir:
            return

        os.makedirs(processed_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_name = f"dabo_data_{ts}.csv"
        target_path = os.path.join(processed_dir, target_name)
        shutil.move(file_path, target_path)
        self.logger.info("Moved to processed: %s", target_path)


@dataclass
class FileWatcher:
    config: Dict[str, Any]

    def start(self) -> None:
        nas_cfg = self.config.get("nas", {})
        watch_paths = [
            nas_cfg.get("routine_update_path"),
            nas_cfg.get("urgent_update_path"),
        ]
        watch_paths = [p for p in watch_paths if p]

        processed_path = nas_cfg.get("processed_path", "")
        if not watch_paths:
            raise ValueError("No watch paths configured")

        handler = CsvHandler(self.config)
        observer = Observer()
        for path in watch_paths:
            os.makedirs(path, exist_ok=True)
            observer.schedule(handler, path, recursive=False)

        observer.start()
        self._scan_existing(handler, watch_paths)
        self._run_loop(observer)

    def _scan_existing(self, handler: CsvHandler, watch_paths: List[str]) -> None:
        logger = get_logger()
        for path in watch_paths:
            try:
                for name in os.listdir(path):
                    file_path = os.path.join(path, name)
                    if os.path.isfile(file_path) and handler._is_csv(file_path):
                        logger.info("Startup scan found CSV: %s", file_path)
                        handler.process_file(file_path)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to scan path: %s", path)

    def _run_loop(self, observer: Observer) -> None:
        logger = get_logger()
        logger.info("Watcher running")
        try:
            while True:
                time.sleep(30)
                logger.info("Watcher heartbeat")
        except KeyboardInterrupt:
            logger.info("Stopping watcher...")
            observer.stop()
        observer.join()


def start_watcher(config: Dict[str, Any] | None = None) -> None:
    cfg = config or load_default_config()
    watcher = FileWatcher(cfg)
    watcher.start()
