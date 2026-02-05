"""
数据库处理工具集 (DatabaseHandler)

此模块封装了对 MySQL 与 Oracle 的基本访问操作，供 ETL 流程调用：
- 使用配置字典构造 MySQL SQLAlchemy 引擎（支持通过环境变量覆盖配置项）；
- 使用配置字典创建 Oracle 连接（或通过 DSN 字符串）；
- 提供常用操作：删除最近 N 天数据、批量插入（带 UPSERT 行为）、查询有效 SKU 列表、记录导入日志。

注意与设计要点：
- 对数据库操作使用事务上下文（`engine.begin()`）确保幂等且事务一致性；
- `insert_dabo_data` 使用 MySQL 的 `ON DUPLICATE KEY UPDATE` 实现幂等写入；
- 配置优先级：环境变量覆盖配置文件中的明文字段（支持 `*_env` 指定环境变量名）。
"""

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
    """数据库访问封装。

    属性:
        config: 从 `config_loader` 得到的配置字典，形如 {
            "mysql": {"user_env": "MYSQL_USER", "password_env": "MYSQL_PASSWORD", ...},
            "oracle": {...}
        }

    使用说明:
        - 实例化后可反复调用其方法；方法内部会在需要时建立连接/引擎并自动关闭。避免长期持有裸连接。
        - 所有对外暴露的方法返回基本的原始类型（int, set 等），方便上层记录日志与指标。
    """

    config: Dict[str, Any]

    def get_mysql_engine(self) -> Engine:
        """根据配置构造并返回 SQLAlchemy MySQL 引擎。

        支持通过配置中的 `*_env` 字段指定环境变量名以覆盖配置文件中的明文值，
        例如在配置里可写 `user_env: MYSQL_USER`。当环境变量存在时优先使用环境变量。

        返回:
            SQLAlchemy `Engine` 对象，调用方应在短期内使用并让上下文管理器提交/回滚事务。

        异常:
            ValueError: 当必须的 MySQL 配置项缺失时抛出。
        """
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
            # 明确的错误便于在启动时快速失败并告知缺少配置
            raise ValueError("MySQL config is incomplete")

        url = (
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
            f"?charset={charset}"
        )
        # pool_pre_ping 用于检测失效连接并在使用前复活，future=True 启用 SQLAlchemy 2.0 风格
        return create_engine(url, pool_pre_ping=True, future=True)

    def get_oracle_connection(self) -> oracledb.Connection:
        """根据配置返回一个 Oracle 连接（oracledb.Connection）。

        支持两种配置方式：直接提供 `dsn`，或分别提供 `host/port/service`。
        同样优先使用环境变量覆盖配置项。
        """
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

        # 调用者负责在使用完后关闭或将连接作为上下文管理器使用
        return oracledb.connect(user=user, password=password, dsn=dsn)

    def delete_recent_data(self, days: int) -> int:
        """删除 `ads_dabo_daily_sales` 表中最近 `days` 天的数据并返回受影响行数。

        如果 `days <= 0`，函数将什么也不做并返回 0（安全守护）。
        此方法在一个事务中执行删除，事务提交由 `engine.begin()` 管理。
        """
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
        """将经过清洗与聚合的 DataFrame 批量写入 MySQL 表 `ads_dabo_daily_sales`。

        行为说明：
            - 要求 DataFrame 包含特定列（见 `required_cols`）。
            - 使用 `ON DUPLICATE KEY UPDATE` 实现基于主键/唯一键的幂等写入：重复导入相同键时会更新数值并刷新 `updated_at`。
            - 在单个事务中执行批量插入以保证一致性。

        参数:
            df: 包含要插入数据的 pandas.DataFrame。
            source_file: 源文件路径，仅用于日志或未来扩展（当前函数不直接写入日志表）。

        返回:
            插入/更新的记录数（基于传入 DataFrame 的行数）。

        异常:
            ValueError: 当缺少必须列时抛出。
        """
        required_cols = {
            "sale_date",
            "product_alias_code",
            "dabo_sales_qty",
            "dabo_order_count",
            "dabo_revenue",
        }
        missing = required_cols - set(df.columns)
        if missing:
            # 向上层抛出清晰的异常，便于在文件级别被捕获并移入隔离区
            raise ValueError(f"Missing columns: {sorted(missing)}")

        if df.empty:
            return 0

        # 将 DataFrame 转为字典列表，供 SQLAlchemy 的 executemany 使用
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
            # executemany: SQLAlchemy 将根据 records 批量执行，提高效率
            conn.execute(sql, records)

        return len(records)

    def get_valid_sku_set(self) -> Set[str]:
        """从 Oracle 的 `M_PRODUCT_ALIAS` 表加载所有 SKU（NO 字段），返回一个字符串集合。

        返回的 SKU 会被 `str().strip()` 以便在后续匹配中忽略前后空格和非字符串类型。
        如果查询结果包含 None 或空行，将被过滤掉。
        """
        sql = "SELECT NO FROM M_PRODUCT_ALIAS"
        with self.get_oracle_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()

        return {str(row[0]).strip() for row in rows if row and row[0] is not None}

    def log_import_record(self, log_data: Dict[str, Any]) -> int:
        """将一次文件导入的元信息写入 `log_dabo_import` 表。

        接受一个包含若干字段的字典 `log_data`，函数会从中按列列表抽取需要插入的字段，
        并在一个事务中执行插入。返回受影响行数（通常为 1）。

        字段约定（部分）：
            - file_name, file_path: 源文件名与路径
            - records_total: 原始记录数
            - records_after_filter: 清洗/过滤后剩余记录数
            - records_inserted: 实际写入数据库的行数
            - sku_match_rate: SKU 匹配率（0-1 或百分比字符串）
            - status: 'success' / 'failed' 等
            - message: 失败时的错误信息或简短说明
            - started_at / finished_at: 时间戳
        """
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
