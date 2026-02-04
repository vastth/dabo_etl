from __future__ import annotations

import argparse
from datetime import datetime

from .config_loader import load_default_config, load_config
from .db_handler import DatabaseHandler
from .etl_processor import EtlProcessor
from .file_watcher import start_watcher
from .logger import get_logger


def run_once(csv_path: str, config_path: str | None = None) -> None:
    config = load_config(config_path) if config_path else load_default_config()
    logger = get_logger(log_dir=config.get("logging", {}).get("log_dir", "logs"))

    db = DatabaseHandler(config)
    etl = EtlProcessor(config, db)

    started_at = datetime.now()
    log_data = {
        "file_name": csv_path.split("/")[-1],
        "file_path": csv_path,
        "status": "FAILED",
        "started_at": started_at,
    }

    try:
        df_valid, meta = etl.process_file(csv_path)
        log_data.update(meta)

        delete_days = int(config.get("etl", {}).get("delete_days", 60))
        db.delete_recent_data(delete_days)

        inserted = db.insert_dabo_data(df_valid, csv_path)
        log_data["records_inserted"] = inserted
        log_data["status"] = "SUCCESS"
        log_data["finished_at"] = datetime.now()

        logger.info("Processed CSV: %s, inserted: %s", csv_path, inserted)
    except Exception as exc:  # noqa: BLE001
        log_data["message"] = str(exc)
        log_data["finished_at"] = datetime.now()
        logger.exception("Failed processing: %s", csv_path)
    finally:
        try:
            db.log_import_record(log_data)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to write import log")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dabo ETL")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--watch", action="store_true", help="Watch NAS folders")
    parser.add_argument("--file", help="Process a single CSV file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.watch:
        cfg = load_config(args.config) if args.config else load_default_config()
        start_watcher(cfg)
        return

    if args.file:
        run_once(args.file, args.config)
        return

    raise SystemExit("Please provide --watch or --file")


if __name__ == "__main__":
    main()
