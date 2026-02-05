"""
ETL 处理器 (EtlProcessor)

此模块负责将源 CSV 文件读取为 pandas.DataFrame，执行清洗、严格类型校验、聚合以及 SKU 验证，
并返回最终可写入数据库的聚合结果与元信息（meta）。

面向新人要点：
- 读取支持 UTF-8 BOM (`utf-8-sig`)，若失败回退到 `gbk`，以兼容常见的 Windows 导出 CSV 编码；
- 清洗步骤包含列重命名、订单状态过滤、字符串修剪、数值标准化（去逗号/货币符）、以及时间字段解析；
- `_validate_strict` 在清洗前验证字段能否被正确解析，若发现无法解析的行则抛出异常，调用方应将该文件隔离；
- 聚合以 `sale_date` 与 `product_alias_code` 为键，计算销售数量、订单数与收入总和；
- `validate_sku` 使用 `DatabaseHandler.get_valid_sku_set()` 获取有效 SKU 列表并计算匹配率，可配置阈值拒绝低匹配率的数据。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import pandas as pd

from .db_handler import DatabaseHandler


@dataclass
class EtlProcessor:
    """封装具体 ETL 流程的类。

    属性:
        config: 配置字典（通常来自 config_loader.load_default_config()），其中 `etl` 节用于控制允许的订单状态、SKU 匹配阈值等。
        db: DatabaseHandler 实例，用于访问数据字典/校验表并在需要时写入或查询数据库。
    """

    config: Dict[str, Any]
    db: DatabaseHandler

    def _get_etl_config(self) -> Dict[str, Any]:
        return self.config.get("etl", {})

    def read_csv(self, file_path: str) -> pd.DataFrame:
        """读取 CSV 并返回字符串类型的 DataFrame。

        实现细节：先尝试使用 `utf-8-sig`（处理可能存在 BOM 的 UTF-8 文件），若发生 `UnicodeDecodeError` 则回退到 `gbk`，
        以兼容部分 Windows 导出的 Excel CSV 文件。
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV not found: {file_path}")

        try:
            return pd.read_csv(file_path, dtype=str, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(file_path, dtype=str, encoding="gbk")

    def clean_and_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """对原始 DataFrame 执行列重命名、字段校验、类型转换与过滤，返回清洗后的 DataFrame。

        步骤说明：
            1. 列名映射（中文列名 -> 代码列名）；
            2. 检查必需列是否存在，否则抛出异常；
            3. 严格校验数值/时间字段的可解析性（`_validate_strict`）；
            4. 按配置的 `order_status_allowlist` 过滤订单状态；
            5. 标准化 `product_alias_code`、将 `qty` 和 `revenue` 转为数值，`ship_time` 转为时间；
            6. 生成 `sale_date`（仅日期部分）以用于后续聚合。
        """
        cfg = self._get_etl_config()
        allowlist = set(cfg.get("order_status_allowlist", ["已完成", "已发货"]))

        rename_map = {
            "主订单编号": "main_order_id",
            "子订单编号": "sub_order_id",
            "商家编码": "product_alias_code",
            "商品数量": "qty",
            "订单状态": "order_status",
            "发货时间": "ship_time",
            "商家收入金额": "revenue",
        }

        df = df.rename(columns=rename_map)

        required = set(rename_map.values())
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        # 先做严格验证，确保关键字段可被解析
        self._validate_strict(df)

        # 只保留需要的订单状态
        df["order_status"] = df["order_status"].astype(str).str.strip()
        df = df[df["order_status"].isin(allowlist)].copy()

        # 清理 SKU 字段中的制表符/空白
        df["product_alias_code"] = (
            df["product_alias_code"].astype(str).str.replace("\t", "", regex=False).str.strip()
        )

        # 数值字段先做规范化（去逗号/货币符）再转换为数值类型
        df["qty"] = (
            pd.to_numeric(self._normalize_number_series(df["qty"]), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        df["revenue"] = (
            pd.to_numeric(self._normalize_number_series(df["revenue"]), errors="coerce")
            .fillna(0.0)
        )

        # 解析发货时间，丢弃无法解析的行
        df["ship_time"] = pd.to_datetime(df["ship_time"], errors="coerce")
        df = df[df["ship_time"].notna()].copy()
        df["sale_date"] = df["ship_time"].dt.date

        return df

    def _validate_strict(self, df: pd.DataFrame) -> None:
        """在做类型转换前执行严格检查，发现无法解析的行时抛出异常。

        这样可以使调用方（如文件处理器）在遇到格式不正确的文件时将其隔离，而不是部分导入脏数据。
        """
        def _count_invalid(series: pd.Series, parsed: pd.Series) -> int:
            return int((series.notna() & parsed.isna()).sum())

        qty_raw = pd.to_numeric(self._normalize_number_series(df["qty"]), errors="coerce")
        revenue_raw = pd.to_numeric(self._normalize_number_series(df["revenue"]), errors="coerce")
        ship_time_raw = pd.to_datetime(df["ship_time"], errors="coerce")

        invalid_qty = _count_invalid(df["qty"], qty_raw)
        invalid_revenue = _count_invalid(df["revenue"], revenue_raw)
        invalid_ship_time = _count_invalid(df["ship_time"], ship_time_raw)

        if invalid_qty or invalid_revenue or invalid_ship_time:
            raise ValueError(
                "Invalid data types: "
                f"qty={invalid_qty}, revenue={invalid_revenue}, ship_time={invalid_ship_time}"
            )

    @staticmethod
    def _normalize_number_series(series: pd.Series) -> pd.Series:
        """规范化数值字符串：去掉千分位逗号与人民币符号并去除首尾空白。

        返回仍然是字符串 Series，便于后续使用 `pd.to_numeric(..., errors='coerce')`。
        """
        return (
            series.astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("¥", "", regex=False)
            .str.replace("￥", "", regex=False)
            .str.strip()
        )

    def aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """按照 `sale_date` 与 `product_alias_code` 分组并聚合为写库结构。

        聚合结果列：
            - `dabo_sales_qty`: 商品数量求和；
            - `dabo_order_count`: 以 `sub_order_id` 去重计数；
            - `dabo_revenue`: 收入求和。
        """
        grouped = df.groupby(["sale_date", "product_alias_code"], as_index=False)
        result = grouped.agg(
            dabo_sales_qty=("qty", "sum"),
            dabo_order_count=("sub_order_id", "nunique"),
            dabo_revenue=("revenue", "sum"),
        )

        return result

    def validate_sku(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
        """使用 Oracle 中的 SKU 列表校验聚合结果，并根据配置返回匹配率。

        返回值:
            (filtered_df, match_rate)
        当匹配率低于配置阈值时抛出 `ValueError`，调用方可据此触发告警或隔离文件。
        """
        valid_set = self.db.get_valid_sku_set()
        threshold = float(self._get_etl_config().get("sku_match_threshold", 0))
        if df.empty:
            return df, 1.0

        df = df.copy()
        df["_is_valid"] = df["product_alias_code"].isin(valid_set)

        total = len(df)
        matched = int(df["_is_valid"].sum())
        match_rate = matched / total if total else 1.0

        df = df[df["_is_valid"]].drop(columns=["_is_valid"])
        if threshold and match_rate < threshold:
            # 低匹配率通常意味着文件与数仓维表不匹配，应人工介入
            raise ValueError(
                f"SKU match rate below threshold: {match_rate:.4f} < {threshold:.4f}"
            )
        return df, match_rate

    def process_file(self, file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """执行完整的文件处理流程并返回最终写库的 DataFrame 与元信息字典。

        元信息 (`meta`) 包含原始记录数、过滤后记录数、最终写入条数与 SKU 匹配率，便于上层记录日志。
        """
        df_raw = self.read_csv(file_path)
        total = len(df_raw)

        df_clean = self.clean_and_filter(df_raw)
        after_filter = len(df_clean)

        df_agg = self.aggregate(df_clean)
        df_valid, match_rate = self.validate_sku(df_agg)

        meta = {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "records_total": total,
            "records_after_filter": after_filter,
            "records_inserted": len(df_valid),
            "sku_match_rate": match_rate,
        }

        return df_valid, meta
