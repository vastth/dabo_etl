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

import os
import argparse
from datetime import datetime

from .config_loader import load_default_config, load_config
from .db_handler import DatabaseHandler
from .etl_processor import EtlProcessor
from .file_watcher import start_watcher
from .logger import get_logger
try:
    from .alerts import send_wechat_alert
except Exception:  # pragma: no cover - optional dependency at runtime
    send_wechat_alert = None


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
        # 发送企业微信告警（若配置了 webhook）
        # 注意：告警配置支持环境变量覆盖（`WECHAT_WEBHOOK` 优先），以便在不同环境安全地注入密钥。
        try:
            notif_cfg = config.get("notifications", {})
            enabled = bool(notif_cfg.get("enabled", False))
            webhook = os.environ.get("WECHAT_WEBHOOK") or notif_cfg.get("wechat_webhook")
            timeout = int(notif_cfg.get("timeout", 10))
            top_n = int(notif_cfg.get("top_n", 5))
            max_len = int(notif_cfg.get("max_len", 1500))
            if enabled and webhook and send_wechat_alert:
                # 构建数据分布摘要：取插入的 topN SKU
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
            logger.exception("Failed to send wechat alert in run_once")
    except Exception as exc:  # noqa: BLE001
        log_data["message"] = str(exc)
        log_data["finished_at"] = datetime.now()
        logger.exception("Failed processing: %s", csv_path)
        # 处理失败也发告警（若配置）
        try:
            notif_cfg = config.get("notifications", {})
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
            logger.exception("Failed to send failure wechat alert in run_once")
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
