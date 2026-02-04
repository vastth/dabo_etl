from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import pandas as pd

from .db_handler import DatabaseHandler


@dataclass
class EtlProcessor:
    config: Dict[str, Any]
    db: DatabaseHandler

    def _get_etl_config(self) -> Dict[str, Any]:
        return self.config.get("etl", {})

    def read_csv(self, file_path: str) -> pd.DataFrame:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV not found: {file_path}")

        try:
            return pd.read_csv(file_path, dtype=str, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(file_path, dtype=str, encoding="gbk")

    def clean_and_filter(self, df: pd.DataFrame) -> pd.DataFrame:
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

        self._validate_strict(df)

        df["order_status"] = df["order_status"].astype(str).str.strip()
        df = df[df["order_status"].isin(allowlist)].copy()

        df["product_alias_code"] = (
            df["product_alias_code"].astype(str).str.replace("\t", "", regex=False).str.strip()
        )

        df["qty"] = (
            pd.to_numeric(self._normalize_number_series(df["qty"]), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        df["revenue"] = (
            pd.to_numeric(self._normalize_number_series(df["revenue"]), errors="coerce")
            .fillna(0.0)
        )

        df["ship_time"] = pd.to_datetime(df["ship_time"], errors="coerce")
        df = df[df["ship_time"].notna()].copy()
        df["sale_date"] = df["ship_time"].dt.date

        return df

    def _validate_strict(self, df: pd.DataFrame) -> None:
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
        return (
            series.astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("¥", "", regex=False)
            .str.replace("￥", "", regex=False)
            .str.strip()
        )

    def aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        grouped = df.groupby(["sale_date", "product_alias_code"], as_index=False)
        result = grouped.agg(
            dabo_sales_qty=("qty", "sum"),
            dabo_order_count=("sub_order_id", "nunique"),
            dabo_revenue=("revenue", "sum"),
        )

        return result

    def validate_sku(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
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
            raise ValueError(
                f"SKU match rate below threshold: {match_rate:.4f} < {threshold:.4f}"
            )
        return df, match_rate

    def process_file(self, file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
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
