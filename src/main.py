"""
主入口脚本。

提供两种运行模式：
    - `--watch`: 以守护/监听模式运行，持续监控 NAS 目录；
    - `--file <path>`: 一次性处理指定 CSV，便于手动调试与回溯。

配置加载优先级：
    - 当通过 `--config` 指定路径时使用该 YAML；
    - 否则使用项目默认位置 `config/config.yaml`。
"""

from __future__ import annotations

import argparse
from datetime import datetime

from .config_loader import load_default_config, load_config
from .db_handler import DatabaseHandler
from .etl_processor import EtlProcessor
from .file_watcher import start_watcher
from .logger import get_logger


def run_once(csv_path: str, config_path: str | None = None) -> None:
    """以一次性运行模式处理单个 CSV 文件并记录导入日志。

    适用于排查单个文件或手动回放。函数流程：
        1. 加载配置并初始化 logger/db/etl；
        2. 调用 `EtlProcessor.process_file` 执行清洗聚合并校验；
        3. 删除历史数据（由配置驱动）；
        4. 将结果写入 MySQL（`DatabaseHandler.insert_dabo_data`）；
        5. 将导入元信息写入日志表 `log_dabo_import`。
    """
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
