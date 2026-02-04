# 数据字典（hefang_dw）

## ads_daily_report
- 描述: 电商日报应用表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | id | bigint | NO |  |  |
| 2 | report_date | date | NO |  | 报告日期 |
| 3 | channel_id | int | YES |  | 渠道ID |
| 4 | channel_name | varchar(50) | YES |  | 渠道名称 |
| 5 | sales_amount | decimal(14,2) | YES | 0.00 | 销售额 |
| 6 | sales_qty | int | YES | 0 | 销量 |
| 7 | return_amount | decimal(14,2) | YES | 0.00 | 退货额 |
| 8 | return_qty | int | YES | 0 | 退货量 |
| 9 | net_amount | decimal(14,2) | YES | 0.00 | 净销售额 |
| 10 | net_qty | int | YES | 0 | 净销量 |
| 11 | order_count | int | YES | 0 | 订单数 |
| 12 | avg_price | decimal(10,2) | YES |  | 客单价 |
| 13 | return_rate | decimal(5,2) | YES |  | 退货率 |
| 14 | discount_rate | decimal(5,2) | YES |  | 折扣率 |
| 15 | sales_amount_yoy | decimal(14,2) | YES |  | 去年同期销售额 |
| 16 | yoy_growth | decimal(5,2) | YES |  | 同比增长率 |
| 17 | sales_amount_mom | decimal(14,2) | YES |  | 上期销售额 |
| 18 | mom_growth | decimal(5,2) | YES |  | 环比增长率 |
| 19 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |

## ads_inventory_health
- 描述: 库存健康度应用表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | id | bigint | NO |  |  |
| 2 | snapshot_date | date | NO |  | 快照日期 |
| 3 | product_id | bigint | NO |  | 商品ID |
| 4 | sku_id | bigint | YES |  | SKU主键（M_PRODUCT_ALIAS.ID） |
| 5 | sku_barcode | varchar(80) | YES |  | 条码 |
| 6 | color | varchar(50) | YES |  | SKU颜色 |
| 7 | size | varchar(50) | YES |  | SKU尺寸 |
| 8 | product_code | varchar(80) | YES |  | 商品编码 |
| 9 | product_name | varchar(200) | YES |  | 商品名称 |
| 10 | category_id | int | YES |  | 类别ID |
| 11 | category_name | varchar(50) | YES |  | 类别 |
| 12 | property_id | int | YES |  | 性质ID |
| 13 | property_name | varchar(50) | YES |  | 性质 |
| 14 | series_id | int | YES |  |  |
| 15 | series_name | varchar(100) | YES |  |  |
| 16 | price_list | decimal(12,2) | YES | 0.00 | 吊牌价 |
| 17 | total_qty | int | YES | 0 | 总库存 |
| 18 | warehouse_qty | int | YES | 0 | 总仓库存 |
| 19 | cloud_qty | int | YES | 0 | 云仓库存 |
| 20 | sales_qty_30d | int | YES | 0 | 近30天销量（全量） |
| 21 | sales_amt_30d | decimal(14,2) | YES | 0.00 | 近30天销售额（全量） |
| 22 | return_qty_30d | int | YES | 0 | 近30天退货量 |
| 23 | sales_qty_7d | int | YES | 0 | 近7天销量（全量） |
| 24 | dabo_sales_qty_30d | int | YES | 0 | 近30天达播销量 |
| 25 | dabo_sales_qty_7d | int | YES | 0 | 近7天达播销量 |
| 26 | natural_sales_qty_30d | int | YES | 0 | 近30天自然销量（全量-达播） |
| 27 | natural_sales_qty_7d | int | YES | 0 | 近7天自然销量（全量-达播） |
| 28 | daily_avg_sales | decimal(10,2) | YES |  | 日均销量30天（全量） |
| 29 | daily_avg_sales_7d | decimal(10,2) | YES | 0.00 | 近7天日均销量（全量） |
| 30 | natural_daily_avg_sales | decimal(10,2) | YES | 0.00 | 近30天自然日均销量 |
| 31 | natural_daily_avg_sales_7d | decimal(10,2) | YES | 0.00 | 近7天自然日均销量 |
| 32 | sales_velocity | decimal(5,2) | YES |  | 销售加速度（全量） |
| 33 | natural_sales_velocity | decimal(5,2) | YES |  | 自然销售加速度 |
| 34 | sales_trend | varchar(20) | YES |  | 销售趋势（全量） |
| 35 | turnover_days | decimal(10,1) | YES |  | 周转天数 |
| 36 | inventory_status | varchar(20) | YES |  | 库存状态 |
| 37 | status_priority | int | YES |  | 状态优先级 |
| 38 | sku_grade | char(1) | YES |  | SABC分级 |
| 39 | sales_rank | int | YES |  | 销售排名 |
| 40 | sales_ratio | decimal(5,2) | YES |  | 销售占比 |
| 41 | cumulative_ratio | decimal(5,2) | YES |  | 累计占比 |
| 42 | suggest_qty | int | YES | 0 | 建议补货数量 |
| 43 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |
| 44 | etl_time | datetime | YES |  | ETL时间戳 |
| 45 | purchase_rem_qty | int | YES | 0 | 采购欠数/在途库存 |
| 46 | return_amount_30d | decimal(14,2) | YES | 0.00 |  |

## ads_sales_summary
- 描述: 销售汇总应用表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | id | bigint | NO |  |  |
| 2 | report_date | date | NO |  | 报告日期 |
| 3 | granularity | varchar(20) | NO |  | 粒度 |
| 4 | channel_id | int | YES |  | 渠道ID |
| 5 | channel_name | varchar(50) | YES |  | 渠道名称 |
| 6 | category_id | int | YES |  | 类别ID |
| 7 | category_name | varchar(50) | YES |  | 类别名称 |
| 8 | sales_amount | decimal(14,2) | YES | 0.00 | 销售额 |
| 9 | sales_qty | int | YES | 0 | 销量 |
| 10 | return_amount | decimal(14,2) | YES | 0.00 | 退货额 |
| 11 | return_qty | int | YES | 0 | 退货量 |
| 12 | net_amount | decimal(14,2) | YES | 0.00 | 净销售额 |
| 13 | order_count | int | YES | 0 | 订单数 |
| 14 | sku_count | int | YES | 0 | 动销SKU数 |
| 15 | avg_price | decimal(10,2) | YES |  | 客单价 |
| 16 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |

## ads_dabo_daily_sales
- 描述: 达播日销售应用表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | sale_date | date | NO |  | 发货日期 |
| 2 | product_alias_code | varchar(80) | NO |  | SKU条码 |
| 3 | dabo_sales_qty | int | NO | 0 | 销量 |
| 4 | dabo_order_count | int | NO | 0 | 订单数 |
| 5 | dabo_revenue | decimal(14,2) | NO | 0.00 | 实收金额 |
| 6 | created_at | datetime | NO | CURRENT_TIMESTAMP |  |
| 7 | updated_at | datetime | NO | CURRENT_TIMESTAMP |  |

## log_dabo_import
- 描述: 达播CSV导入日志

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | id | bigint | NO |  |  |
| 2 | file_name | varchar(255) | NO |  | 文件名 |
| 3 | file_path | varchar(500) | YES |  | 文件路径 |
| 4 | records_total | int | NO | 0 | 原始行数 |
| 5 | records_after_filter | int | NO | 0 | 过滤后行数 |
| 6 | records_inserted | int | NO | 0 | 写入行数 |
| 7 | sku_match_rate | decimal(5,4) | YES |  | SKU匹配率 |
| 8 | status | varchar(20) | NO |  | 状态 |
| 9 | message | varchar(1000) | YES |  | 错误信息 |
| 10 | started_at | datetime | YES |  | 开始时间 |
| 11 | finished_at | datetime | YES |  | 结束时间 |
| 12 | created_at | datetime | NO | CURRENT_TIMESTAMP |  |

## dim_category
- 描述: 类别维度表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | category_id | int | NO |  | 类别ID |
| 2 | category_name | varchar(50) | NO |  | 类别名称 |
| 3 | is_main_product | char(1) | YES | Y | 是否主销品类别 |
| 4 | sort_order | int | YES | 0 | 排序 |
| 5 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |

## dim_channel
- 描述: 电商渠道维度表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | channel_id | int | NO |  | 渠道ID |
| 2 | channel_name | varchar(50) | NO |  | 渠道名称 |
| 3 | channel_code | varchar(20) | YES |  | 渠道编码 |
| 4 | store_code | varchar(40) | YES |  | 对应店仓编码 |
| 5 | is_main | tinyint | YES | 0 | 是否主要渠道 |
| 6 | platform_type | varchar(20) | YES |  | 平台类型 |
| 7 | is_active | char(1) | YES | Y | 是否有效 |
| 8 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |

## dim_date
- 描述: 日期维度表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | date_id | int | NO |  | 日期ID格式YYYYMMDD |
| 2 | date_value | date | NO |  | 日期 |
| 3 | date_year | int | NO |  | 年 |
| 4 | date_month | int | NO |  | 月 |
| 5 | date_day | int | NO |  | 日 |
| 6 | date_quarter | int | NO |  | 季度 |
| 7 | week_of_year | int | NO |  | 年周数 |
| 8 | day_of_week | int | NO |  | 周几1到7 |
| 9 | day_name_cn | varchar(10) | YES |  | 周几中文 |
| 10 | month_name_cn | varchar(10) | YES |  | 月份中文 |
| 11 | is_weekend | tinyint | YES | 0 | 是否周末 |
| 12 | is_holiday | tinyint | YES | 0 | 是否节假日 |
| 13 | holiday_name | varchar(50) | YES |  | 节假日名称 |
| 14 | year_month | varchar(7) | YES |  | 年月格式YYYY-MM |
| 15 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |

## dim_product
- 描述: 商品维度表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | product_id | bigint | NO |  | 商品ID |
| 2 | product_code | varchar(80) | NO |  | 商品编码款号 |
| 3 | product_name | varchar(200) | YES |  | 商品名称 |
| 4 | category_id | int | YES |  | 类别ID |
| 5 | category_name | varchar(50) | YES |  | 类别名称 |
| 6 | property_id | int | YES |  | 性质ID |
| 7 | property_name | varchar(50) | YES |  | 性质名称 |
| 8 | series_id | int | YES |  | 系列ID |
| 9 | series_name | varchar(100) | YES |  | 系列名称 |
| 10 | brand_id | int | YES |  | 品牌ID |
| 11 | brand_name | varchar(50) | YES |  | 品牌名称 |
| 12 | year_id | int | YES |  | 年份ID |
| 13 | year_name | varchar(20) | YES |  | 年份 |
| 14 | price_list | decimal(12,2) | YES |  | 吊牌价 |
| 15 | price_cost | decimal(12,2) | YES |  | 成本价 |
| 16 | is_main_product | char(1) | YES | Y | 是否主销品 |
| 17 | is_active | char(1) | YES | Y | 是否有效 |
| 18 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |
| 19 | updated_at | datetime | YES | CURRENT_TIMESTAMP |  |
| 20 | material | text | YES |  |  |

## dim_product_attr

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | product_id | bigint | YES |  |  |
| 2 | color | text | YES |  |  |
| 3 | size | text | YES |  |  |

## dim_sku
- 描述: SKU维度表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | sku_id | bigint | NO |  | SKU主键 |
| 2 | sku_barcode | varchar(80) | YES |  | 条码 |
| 3 | product_id | bigint | YES |  | 货号ID |
| 4 | sku_color | varchar(50) | YES |  | 颜色 |
| 5 | sku_size | varchar(50) | YES |  | 尺寸 |
| 6 | is_active | char(1) | YES | Y | 是否有效 |
| 7 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |
| 8 | updated_at | datetime | YES | CURRENT_TIMESTAMP |  |

## dim_store
- 描述: 店仓维度表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | store_id | bigint | NO |  | 店仓ID |
| 2 | store_code | varchar(40) | NO |  | 店仓编码 |
| 3 | store_name | varchar(255) | YES |  | 店仓名称 |
| 4 | area_id | int | YES |  | 区域ID |
| 5 | area_name | varchar(100) | YES |  | 区域名称 |
| 6 | is_warehouse | tinyint | YES | 0 | 是否仓库 |
| 7 | is_store | tinyint | YES | 0 | 是否门店 |
| 8 | is_cloud_store | char(1) | YES | N | 是否云仓 |
| 9 | is_center | char(1) | YES | N | 是否物流中心 |
| 10 | store_type | varchar(20) | YES |  | 类型 |
| 11 | is_active | char(1) | YES | Y | 是否有效 |
| 12 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |
| 13 | updated_at | datetime | YES | CURRENT_TIMESTAMP |  |

## dws_inventory_daily
- 描述: 日库存快照表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | id | bigint | NO |  |  |
| 2 | date_id | int | NO |  | 日期ID |
| 3 | store_id | bigint | NO |  | 店仓ID |
| 4 | store_code | varchar(40) | YES |  | 店仓编码 |
| 5 | is_cloud_store | char(1) | YES | N | 是否云仓(Y/N) |
| 6 | product_id | bigint | NO |  | 商品ID |
| 7 | m_productalias_id | bigint | YES |  | SKU ID（条码） |
| 8 | qty | int | YES | 0 | 库存数量 |
| 9 | qty_valid | int | YES | 0 | 可用库存 |
| 10 | qty_occupy | int | YES | 0 | 占用数量 |
| 11 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |
| 12 | etl_time | datetime | YES |  | ETL时间戳 |
| 13 | qtypurchaserem | bigint | YES | 0 | 采购欠数/在途 |

## dws_sales_daily
- 描述: 日销售汇总表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | id | bigint | NO |  |  |
| 2 | date_id | int | NO |  | 日期ID |
| 3 | store_id | bigint | NO |  | 店仓ID |
| 4 | product_id | bigint | NO |  | 商品ID |
| 5 | m_productalias_id | bigint | YES |  | SKU ID（条码） |
| 6 | sales_qty | int | YES | 0 | 销售数量 |
| 7 | sales_amount | decimal(14,2) | YES | 0.00 | 销售金额 |
| 8 | sales_amount_list | decimal(14,2) | YES | 0.00 | 吊牌金额 |
| 9 | return_qty | int | YES | 0 | 退货数量 |
| 10 | return_amount | decimal(14,2) | YES | 0.00 | 退货金额 |
| 11 | net_qty | int | YES | 0 | 净销量 |
| 12 | net_amount | decimal(14,2) | YES | 0.00 | 净销售额 |
| 13 | order_count | int | YES | 0 | 订单数 |
| 14 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |
| 15 | updated_at | datetime | YES | CURRENT_TIMESTAMP |  |
| 16 | etl_time | datetime | YES |  | ETL时间戳 |
| 17 | store_code | varchar(32) | YES |  | 源店仓编码（如 DS001） |
| 18 | is_cloud_store | char(1) | YES | N | 是否云仓(Y/N) |

## etl_log
- 描述: ETL执行日志表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | id | bigint | NO |  |  |
| 2 | job_name | varchar(100) | NO |  | 任务名称 |
| 3 | job_type | varchar(50) | YES |  | 任务类型 |
| 4 | source_table | varchar(100) | YES |  | 源表 |
| 5 | target_table | varchar(100) | YES |  | 目标表 |
| 6 | start_time | datetime | YES |  | 开始时间 |
| 7 | end_time | datetime | YES |  | 结束时间 |
| 8 | rows_read | int | YES | 0 | 读取行数 |
| 9 | rows_written | int | YES | 0 | 写入行数 |
| 10 | status | varchar(20) | YES |  | 状态 |
| 11 | error_message | text | YES |  | 错误信息 |
| 12 | created_at | datetime | YES | CURRENT_TIMESTAMP |  |

## ods_fa_storage
- 描述: ODS-实时库存表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | id | bigint | NO |  | 库存记录ID |
| 2 | c_store_id | bigint | YES |  |  |
| 3 | m_product_id | bigint | YES |  |  |
| 4 | m_productalias_id | bigint | YES |  |  |
| 5 | qty | decimal(18,4) | YES |  |  |
| 6 | qtyvalid | decimal(18,4) | YES |  |  |
| 7 | qtyoccupy | decimal(18,4) | YES |  |  |
| 8 | pricelist | decimal(18,2) | YES |  |  |
| 9 | isactive | char(1) | YES |  |  |
| 10 | etl_batch_id | varchar(32) | NO |  |  |
| 11 | etl_loaded_at | datetime | YES | CURRENT_TIMESTAMP |  |

## ods_m_retail
- 描述: ODS-零售单主表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | id | bigint | NO |  | 零售单ID |
| 2 | docno | varchar(40) | YES |  |  |
| 3 | billdate | int | YES |  | YYYYMMDD |
| 4 | c_store_id | bigint | YES |  |  |
| 5 | tot_amt_actual | decimal(18,2) | YES |  |  |
| 6 | tot_amt_list | decimal(18,2) | YES |  |  |
| 7 | tot_qty | decimal(18,4) | YES |  |  |
| 8 | status | int | YES |  |  |
| 9 | isactive | char(1) | YES |  |  |
| 10 | created | datetime | YES |  |  |
| 11 | etl_batch_id | bigint | NO | 0 |  |
| 12 | etl_loaded_at | datetime | YES | CURRENT_TIMESTAMP |  |

## ods_m_retailitem
- 描述: ODS-零售单明细表

| 序号 | 字段名 | 类型 | 可空 | 默认值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | id | bigint | NO |  | 明细ID |
| 2 | m_retail_id | bigint | YES |  |  |
| 3 | m_product_id | bigint | YES |  |  |
| 4 | m_productalias_id | bigint | YES |  |  |
| 5 | qty | decimal(18,4) | YES |  |  |
| 6 | pricelist | decimal(18,2) | YES |  |  |
| 7 | priceactual | decimal(18,2) | YES |  |  |
| 8 | tot_amt_actual | decimal(18,2) | YES |  |  |
| 9 | tot_amt_list | decimal(18,2) | YES |  |  |
| 10 | etl_batch_id | varchar(32) | NO |  |  |
| 11 | etl_loaded_at | datetime | YES | CURRENT_TIMESTAMP |  |
