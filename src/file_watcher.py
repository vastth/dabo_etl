"""
文件监听与 CSV 处理模块。

职责：
- 监听 NAS（或本地目录）中新到的 CSV 文件；
- 对新文件做基本校验（文件名、就绪状态、hash 去重）；
- 将文件交给 `EtlProcessor` 清洗/聚合并写入数据库；
- 根据处理结果将文件移动到 `processed` 或 `quarantine` 目录，并记录导入日志。

设计与运行要点：
- 使用 watchdog 外挂监听文件创建事件，并在启动时对 watch 目录做一次扫描以处理启动前遗留的文件；
- 使用 `_in_progress` 集合进行事件去抖，避免同一文件被并发事件触发两次处理；
- 使用文件 hash 存储（temp/file_hashes.json）避免重复内容的再次导入；
- 在遇到无法解析或处理的异常时，将文件移动到隔离目录并记录失败原因，便于人工排查。
"""

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
try:
    from .alerts import send_wechat_alert
except Exception:  # pragma: no cover - optional at runtime
    send_wechat_alert = None


@dataclass
class WatcherConfig:
    """简单的配置数据类（当前未大量使用，但保留以便将来扩展）。"""
    watch_paths: List[str]
    processed_path: str
    poll_interval: float = 1.0


class CsvHandler(FileSystemEventHandler):
    """处理 CSV 文件创建事件的 Handler。

    主要成员说明：
        - `config`: 完整配置字典；
        - `logger`: 日志记录器；
        - `db`: `DatabaseHandler` 实例用于写库与查询 SKU；
        - `etl`: `EtlProcessor` 实例用于清洗/聚合；
        - `hash_store_path`: 本地存储已处理文件 hash 的 JSON 文件路径；
        - `_in_progress`: 内存集合用于去抖正在处理的文件路径，避免重复处理。
    """

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
        """校验文件名是否符合 `dabo_YYYYMMDD.csv` 的约定并验证日期段是否合法。"""
        name = os.path.basename(file_path)
        if not re.match(r"^dabo_\d{8}\.csv$", name):
            return False
        try:
            datetime.strptime(name[5:13], "%Y%m%d")
        except ValueError:
            return False
        return True

    def on_created(self, event) -> None:
        """watchdog 的回调：当文件在监控目录被创建时触发。

        流程：
            - 忽略目录事件与非 CSV 文件；
            - 使用 `_in_progress` 去抖；
            - 等待文件可读后交由 `process_file` 处理；
            - 不管成功或失败，最后从 `_in_progress` 中移除路径。
        """
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
        """处理单个文件的主流程：校验文件名 → 就绪检查 → hash 去重 → ETL → 写库 → 移动文件与记录日志。

        在出错情况下，会将文件移动到隔离目录（quarantine）并记录失败原因，便于人工排查与重试。
        """
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

        # 文件名校验
        if not self._is_valid_filename(file_path):
            log_data["status"] = "REJECTED_NAME"
            log_data["message"] = "Invalid file name"
            log_data["finished_at"] = datetime.now()
            self.logger.warning("Rejected file name: %s", file_path)
            self._move_to_quarantine(file_path, suffix="bad_name")
            self._safe_log_import(log_data)
            return

        # 再次就绪检查（因为 on_created 可能仅表示文件创建，未写入完毕）
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

        # 内容去重：根据文件内容 hash 跳过重复内容的文件
        file_hash = self._compute_hash(file_path)
        if self._is_duplicate_hash(file_hash):
            log_data["status"] = "SKIPPED_DUPLICATE"
            log_data["message"] = "Duplicate file hash"
            log_data["finished_at"] = datetime.now()
            self.logger.warning("Skipped duplicate file: %s", file_path)
            # 已处理但内容重复的文件也移动到 processed，避免重复堆积
            self._move_to_processed(file_path)
            self._safe_log_import(log_data)
            return

        # 重试配置（ETL 内部或文件 IO 异常可触发重试）
        retry_cfg = self.config.get("etl", {})
        max_retries = int(retry_cfg.get("retry_count", 0))
        delay = float(retry_cfg.get("retry_delay_seconds", 1))

        attempt = 0
        while True:
            try:
                # 执行 ETL，获得最终写库的 DataFrame 与元信息
                df_valid, meta = self.etl.process_file(file_path)
                log_data.update(meta)

                # 删除历史数据（按配置保留天数）以避免重复聚合导致错计
                delete_days = int(self.config.get("etl", {}).get("delete_days", 60))
                self.db.delete_recent_data(delete_days)

                # 写库：DatabaseHandler 内部使用事务与 UPSERT 保证幂等
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
                # 发送成功告警（可选）
                try:
                    notif_cfg = self.config.get("notifications", {})
                    enabled = bool(notif_cfg.get("enabled", False))
                    webhook = os.environ.get("WECHAT_WEBHOOK") or notif_cfg.get("wechat_webhook")
                    timeout = int(notif_cfg.get("timeout", 10))
                    top_n = int(notif_cfg.get("top_n", 5))
                    max_len = int(notif_cfg.get("max_len", 1500))
                    if enabled and webhook and send_wechat_alert:
                        try:
                            top = (
                                df_valid.sort_values("dabo_sales_qty", ascending=False)
                                .head(top_n)
                                .loc[:, ["product_alias_code", "dabo_sales_qty", "dabo_order_count", "dabo_revenue"]]
                            )
                            lines = [
                                f"{r.product_alias_code}: qty={int(r.dabo_sales_qty)}, orders={int(r.dabo_order_count)}, rev={r.dabo_revenue:.2f}"
                                for r in top.itertuples()
                            ]
                            dist = "\n".join(lines) if lines else "(no data)"
                        except Exception:
                            dist = "(failed to summarize distribution)"
                        finished = log_data.get("finished_at")
                        ts = finished.isoformat(sep=" ", timespec="seconds") if finished else ""
                        sku_match_rate = log_data.get("sku_match_rate")
                        sku_rate_str = f"{sku_match_rate:.2%}" if sku_match_rate is not None else "N/A"
                        msg = (
                            f"达播数据已更新\n文件: {log_data.get('file_name')}\n时间: {ts}\n"
                            f"插入: {log_data.get('records_inserted')}\nsku_match_rate: {sku_rate_str}\n"
                            f"Top SKUs:\n{dist}"
                        )
                        send_wechat_alert(webhook, msg, max_len=max_len, timeout=timeout)
                except Exception:
                    self.logger.exception("Failed to send wechat alert in watcher")

                self._move_to_processed(file_path)
                self._save_hash(file_hash)
                break
            except (PermissionError, OSError, IOError) as exc:
                # 针对文件被锁或网络文件系统 IO 错误做重试与退避
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
                # 失败告警（可选）
                try:
                    notif_cfg = self.config.get("notifications", {})
                    enabled = bool(notif_cfg.get("enabled", False))
                    webhook = os.environ.get("WECHAT_WEBHOOK") or notif_cfg.get("wechat_webhook")
                    timeout = int(notif_cfg.get("timeout", 10))
                    max_len = int(notif_cfg.get("max_len", 1500))
                    if enabled and webhook and send_wechat_alert:
                        finished = log_data.get("finished_at")
                        ts = finished.isoformat(sep=" ", timespec="seconds") if finished else ""
                        msg = (
                            f"达播数据上传失败\n文件: {log_data.get('file_name')}\n时间: {ts}\n错误: {log_data.get('message')}"
                        )
                        send_wechat_alert(webhook, msg, max_len=max_len, timeout=timeout)
                except Exception:
                    self.logger.exception("Failed to send failure wechat alert in watcher")
                break
            except Exception as exc:  # noqa: BLE001
                # 其他错误（例如数据验证失败）直接隔离并记录
                log_data["message"] = str(exc)
                log_data["finished_at"] = datetime.now()
                self.logger.exception("Failed processing: %s", file_path)
                self._move_to_quarantine(file_path, suffix="error")
                # 失败告警（可选）
                try:
                    notif_cfg = self.config.get("notifications", {})
                    enabled = bool(notif_cfg.get("enabled", False))
                    webhook = os.environ.get("WECHAT_WEBHOOK") or notif_cfg.get("wechat_webhook")
                    timeout = int(notif_cfg.get("timeout", 10))
                    max_len = int(notif_cfg.get("max_len", 1500))
                    if enabled and webhook and send_wechat_alert:
                        finished = log_data.get("finished_at")
                        ts = finished.isoformat(sep=" ", timespec="seconds") if finished else ""
                        msg = (
                            f"达播数据上传失败\n文件: {log_data.get('file_name')}\n时间: {ts}\n错误: {log_data.get('message')}"
                        )
                        send_wechat_alert(webhook, msg, max_len=max_len, timeout=timeout)
                except Exception:
                    self.logger.exception("Failed to send failure wechat alert in watcher")
                break
        self._safe_log_import(log_data)

    def _safe_log_import(self, log_data: Dict[str, Any]) -> None:
        """尝试写入导入日志；若写日志失败只记录异常，不影响主流程（防止二次错误破坏文件流）。"""
        try:
            self.db.log_import_record(log_data)
        except Exception:  # noqa: BLE001
            self.logger.exception("Failed to write import log")

    def _compute_hash(self, file_path: str) -> str:
        """按文件内容计算 SHA256，用于去重判断。以流式方式读取文件以节省内存。"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _wait_for_ready(self, file_path: str, retries: int = 10, delay: float = 1.0) -> bool:
        """等待文件可读（非被占用）并返回是否就绪。

        在网络文件系统上，文件创建事件可能在写入尚未完成时触发，
        本函数通过尝试以二进制模式打开文件来检测是否已释放写锁。
        """
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
            # 读取失败（例如文件损坏）时返回空字典，避免处理流程中断
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
        """将文件移动到隔离目录，文件名后缀用于标识问题类型（如 bad_name/locked/error）。"""
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
    """启动并管理 watchdog observer 的帮助类。

    使用 `start()` 启动 observer 并在启动后扫描已有文件以保证不漏处理。
    """
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
        """启动时扫描目录并处理已存在的 CSV 文件（防止启动期间遗漏）。"""
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
