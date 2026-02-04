from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, Set

import oracledb
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import os


@dataclass
class DatabaseHandler:
    config: Dict[str, Any]

    def get_mysql_engine(self) -> Engine:
        mysql_cfg = self.config.get("mysql", {})
        user = os.getenv(mysql_cfg.get("user_env", "")) or mysql_cfg.get("user")
        password = os.getenv(mysql_cfg.get("password_env", "")) or mysql_cfg.get("password")
        host = (
            os.getenv(mysql_cfg.get("host_env", ""))
            or mysql_cfg.get("host")
            or mysql_cfg.get("host_default", "127.0.0.1")
        )
        port = (
            os.getenv(mysql_cfg.get("port_env", ""))
            or mysql_cfg.get("port")
            or mysql_cfg.get("port_default", 3306)
        )
        database = os.getenv(mysql_cfg.get("database_env", "")) or mysql_cfg.get("database")
        charset = (
            os.getenv(mysql_cfg.get("charset_env", ""))
            or mysql_cfg.get("charset")
            or "utf8mb4"
        )

        if not user or not password or not database:
            raise ValueError("MySQL config is incomplete")

        url = (
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
            f"?charset={charset}"
        )
        return create_engine(url, pool_pre_ping=True, future=True)

    def get_oracle_connection(self) -> oracledb.Connection:
        oracle_cfg = self.config.get("oracle", {})
        user = os.getenv(oracle_cfg.get("user_env", "")) or oracle_cfg.get("user")
        password = os.getenv(oracle_cfg.get("password_env", "")) or oracle_cfg.get("password")
        dsn = os.getenv(oracle_cfg.get("dsn_env", "")) or oracle_cfg.get("dsn")
        if not dsn:
            host = os.getenv(oracle_cfg.get("host_env", "")) or oracle_cfg.get("host")
            port = os.getenv(oracle_cfg.get("port_env", "")) or oracle_cfg.get("port")
            service = os.getenv(oracle_cfg.get("service_env", "")) or oracle_cfg.get("service")
            if host and port and service:
                dsn = f"{host}:{port}/{service}"

        if not user or not password or not dsn:
            raise ValueError("Oracle config is incomplete")

        return oracledb.connect(user=user, password=password, dsn=dsn)

    def delete_recent_data(self, days: int) -> int:
        if days <= 0:
            return 0

        sql = text(
            """
            DELETE FROM ads_dabo_daily_sales
            WHERE sale_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
            """
        )
        engine = self.get_mysql_engine()
        with engine.begin() as conn:
            result = conn.execute(sql, {"days": days})
            return result.rowcount or 0

    def insert_dabo_data(self, df: pd.DataFrame, source_file: str) -> int:
        required_cols = {
            "sale_date",
            "product_alias_code",
            "dabo_sales_qty",
            "dabo_order_count",
            "dabo_revenue",
        }
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")

        if df.empty:
            return 0

        records = df[list(required_cols)].to_dict("records")
        sql = text(
            """
            INSERT INTO ads_dabo_daily_sales
            (sale_date, product_alias_code, dabo_sales_qty, dabo_order_count, dabo_revenue)
            VALUES (:sale_date, :product_alias_code, :dabo_sales_qty, :dabo_order_count, :dabo_revenue)
                        ON DUPLICATE KEY UPDATE
                            dabo_sales_qty = VALUES(dabo_sales_qty),
                            dabo_order_count = VALUES(dabo_order_count),
                            dabo_revenue = VALUES(dabo_revenue),
                            updated_at = CURRENT_TIMESTAMP
            """
        )

        engine = self.get_mysql_engine()
        with engine.begin() as conn:
            conn.execute(sql, records)

        return len(records)

    def get_valid_sku_set(self) -> Set[str]:
        sql = "SELECT NO FROM M_PRODUCT_ALIAS"
        with self.get_oracle_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()

        return {str(row[0]).strip() for row in rows if row and row[0] is not None}

    def log_import_record(self, log_data: Dict[str, Any]) -> int:
        columns = [
            "file_name",
            "file_path",
            "records_total",
            "records_after_filter",
            "records_inserted",
            "sku_match_rate",
            "status",
            "message",
            "started_at",
            "finished_at",
        ]

        payload = {k: log_data.get(k) for k in columns}

        sql = text(
            """
            INSERT INTO log_dabo_import
            (file_name, file_path, records_total, records_after_filter, records_inserted,
             sku_match_rate, status, message, started_at, finished_at)
            VALUES (:file_name, :file_path, :records_total, :records_after_filter, :records_inserted,
                    :sku_match_rate, :status, :message, :started_at, :finished_at)
            """
        )

        engine = self.get_mysql_engine()
        with engine.begin() as conn:
            result = conn.execute(sql, payload)
            return result.rowcount or 0
