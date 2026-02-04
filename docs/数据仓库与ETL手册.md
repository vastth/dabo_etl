# 何方珠宝 - 数据仓库与ETL手册

> 数仓建设方案 | ETL同步逻辑 | 调度说明

---

## 📋 目录

1. [数仓架构设计](#一数仓架构设计)
2. [分层与表结构](#二分层与表结构)
3. [ETL同步逻辑](#三etl同步逻辑)
4. [调度与监控](#四调度与监控)

---

## 一、数仓架构设计

### 1.1 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                     数据仓库架构                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Oracle生产库（伯俊ERP）                                  │
│       ↓                                                  │
│  Python ETL（每日凌晨执行）                               │
│       ↓                                                  │
│  ┌────────────────────────────────────────────────────┐  │
│  │              MySQL本地数据仓库                     │  │
│  │                                                    │  │
│  │  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐          │  │
│  │  │ODS │→ │DIM │→ │DWD │→ │DWS │→ │ADS │          │  │
│  │  │原始│  │维度│  │明细│  │汇总│  │应用│          │  │
│  │  └────┘  └────┘  └────┘  └────┘  └────┘          │  │
│  └────────────────────────────────────────────────────┘  │
│       ↓                                                  │
│  Tableau / FineBI / Excel                                │
│       ↓                                                  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  电商日报 | 库存健康度 | 月度报告 | 进销存看板     │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

### 1.2 分层说明

| 层级 | 名称 | 说明 | 示例表 |
|------|------|------|--------|
| ODS | 原始数据层 | 1:1复制源表（保留） | ods_m_retail, ods_fa_storage |
| DIM | 维度层 | 维度表 | dim_product, dim_store, dim_sku, dim_date |
| DWD | 明细事实层 | 清洗后的明细（保留） | dwd_retail_detail |
| DWS | 汇总事实层 | 按主题汇总 | dws_sales_daily, dws_inventory_daily |
| ADS | 应用层 | 面向应用 | ads_daily_report, ads_inventory_health |

---

### 1.3 星型模型设计

```
                         ┌───────────────┐
                         │  dim_date     │
                         │  日期维度      │
                         └───────┬───────┘
                                 │
┌───────────────┐       ┌───────┴───────┐       ┌───────────────┐
│  dim_store    │       │ fact_sales    │       │ dim_product   │
│  店仓维度      │◄──────│ 销售事实表    │──────►│ 商品维度       │
└───────────────┘       │               │       └───────────────┘
                        │ • date_id     │
                        │ • store_id    │
                        │ • product_id  │
                        │ • 销量        │
                        │ • 销售额      │
                        │ • 退货量      │
                        │ • 退货额      │
                        └───────────────┘
```

> 注：SKU维度来自 dim_sku（sku_id），用于SKU粒度分析。

---

## 二、分层与表结构

### 2.1 维度表设计

**dim_product（商品维度）**
```sql
CREATE TABLE dim_product (
    product_id      BIGINT PRIMARY KEY,
    product_code    VARCHAR(80),
    product_name    VARCHAR(200),
    category_id     INT,
    category_name   VARCHAR(50),
    property_id     INT,
    property_name   VARCHAR(50),
    series_id       INT,
    series_name     VARCHAR(100),
    brand_id        INT,
    brand_name      VARCHAR(50),
    price_list      DECIMAL(12,2),
    price_cost      DECIMAL(12,2),
    is_main_product CHAR(1),
    is_active       CHAR(1),
    created_at      DATETIME,
    updated_at      DATETIME
);
```

**dim_store（店仓维度）**
```sql
CREATE TABLE dim_store (
    store_id        BIGINT PRIMARY KEY,
    store_code      VARCHAR(40),
    store_name      VARCHAR(255),
    area_id         INT,
    area_name       VARCHAR(100),
    is_warehouse    TINYINT,
    is_store        TINYINT,
    is_cloud_store  CHAR(1),
    is_center       CHAR(1),
    store_type      VARCHAR(20),
    is_active       CHAR(1),
    created_at      DATETIME,
    updated_at      DATETIME
);
```

**dim_sku（SKU维度）**
```sql
CREATE TABLE dim_sku (
    sku_id            BIGINT PRIMARY KEY,
    product_id        BIGINT,
    sku_barcode       VARCHAR(80),
    sku_color         VARCHAR(60),
    sku_size          VARCHAR(60),
    is_active         CHAR(1),
    created_at        DATETIME,
    updated_at        DATETIME
);
```

**dim_date（日期维度）**
```sql
CREATE TABLE dim_date (
    date_id         INT PRIMARY KEY,
    date_value      DATE,
    date_year       INT,
    date_month      INT,
    date_day        INT,
    date_quarter    INT,
    week_of_year    INT,
    day_of_week     INT,
    day_name_cn     VARCHAR(10),
    month_name_cn   VARCHAR(10),
    is_weekend      TINYINT,
    is_holiday      TINYINT,
    holiday_name    VARCHAR(50),
    year_month      VARCHAR(7),
    created_at      DATETIME
);
```

---

### 2.2 事实表设计

**dws_sales_daily（日销售汇总）**
```sql
CREATE TABLE dws_sales_daily (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    date_id         INT,
    store_id        BIGINT,
    product_id      BIGINT,
    m_productalias_id BIGINT,
    sales_qty       INT,
    sales_amount    DECIMAL(14,2),
    sales_amount_list DECIMAL(14,2),
    return_qty      INT,
    return_amount   DECIMAL(14,2),
    net_qty         INT,
    net_amount      DECIMAL(14,2),
    order_count     INT,
    store_code      VARCHAR(32),
    is_cloud_store  CHAR(1),
    created_at      DATETIME,
    updated_at      DATETIME,
    etl_time        DATETIME,
    
    INDEX idx_date (date_id),
    INDEX idx_store (store_id),
    INDEX idx_product (product_id)
);
```

**dws_inventory_daily（日库存快照）**
```sql
CREATE TABLE dws_inventory_daily (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    date_id         INT,
    store_id        BIGINT,
    store_code      VARCHAR(32),
    is_cloud_store  CHAR(1),
    product_id      BIGINT,
    m_productalias_id BIGINT,
    qty             INT,
    qty_valid       INT,
    qty_occupy      INT,
    qtypurchaserem  BIGINT,
    created_at      DATETIME,
    etl_time        DATETIME,
    
    INDEX idx_date (date_id),
    INDEX idx_store (store_id),
    INDEX idx_product (product_id)
);
```

---

### 2.3 应用表设计

**ads_inventory_health（库存健康度）**

此表在MySQL内基于dws层计算，不从Oracle直接抽取：

```sql
-- 数据来源
库存数据 ← dws_inventory_daily (当天)
销售数据 ← dws_sales_daily (近30天)
达播销量 ← ads_dabo_daily_sales (近30天/近7天)
商品信息 ← dim_product
SKU信息 ← dim_sku
仓库信息 ← dim_store

-- 计算内容
- 周转天数 = 库存 / (30天销量 / 30)
- 库存状态（滞销/缺货/正常/过高）
- ABC分级（按销售额累计占比）
- 建议补货 = (90-周转天数)*日均销量 - 退货 - 采购欠数
- 自然销量 = 全量销量 - 达播销量（用于自然销售加速度与趋势判断）
```

---

## 三、ETL同步逻辑

### 3.1 各表同步策略

| 目标表 | 源表 | 策略 | 说明 |
|--------|------|------|------|
| dim_product | M_PRODUCT + M_DIM | 全量覆盖 | 商品信息可能改 |
| dim_sku | M_PRODUCT_ALIAS + M_ATTRIBUTESETINSTANCE | 全量覆盖 | SKU信息可能改 |
| dim_store | C_STORE + C_AREA | 全量覆盖 | 门店可能新增 |
| dws_sales_daily | M_RETAIL + M_RETAILITEM + C_STORE + M_PRODUCT | 增量（按日期） | 智能判断：凌晨查昨天，白天查今天 |
| dws_inventory_daily | FA_STORAGE + C_STORE + M_PRODUCT | 全量快照 | 每日记录当天库存 |
| ads_inventory_health | MySQL内计算 | 重新计算 | 基于dws层 |
| ads_dabo_daily_sales | CSV文件 | 文件驱动 | 监听例行/紧急目录 |
| log_dabo_import | ETL日志 | 追加写入 | 每次导入记录 |

---

### 3.2 同步时序

```
03:00  ETL开始
03:05  同步dim_product（约3分钟）
03:08  同步dim_sku（约1分钟）
03:10  同步dim_store（约1分钟）
03:12  同步dws_sales_daily（智能判断）（约5分钟）
03:17  同步dws_inventory_daily（约10分钟）
03:27  计算ads_inventory_health（约5分钟）
03:32  ETL结束
06:00  Tableau数据源刷新
实时  达播CSV监听（例行/紧急目录）
```

---

### 3.3 增量同步逻辑

**销售数据增量：**
```python
# 智能判断：凌晨查昨天，白天查今天（可通过 days_back 回溯）
current_time = datetime.now()
if include_today:
    end_dt = current_time - timedelta(days=1) if current_time.hour < 6 else current_time
else:
    end_dt = current_time - timedelta(days=1)

start_dt = end_dt - timedelta(days=days_back-1)
start_date = int(start_dt.strftime('%Y%m%d'))
end_date = int(end_dt.strftime('%Y%m%d'))

# 先删后插
mysql.execute(f"DELETE FROM dws_sales_daily WHERE date_id >= {start_date} AND date_id <= {end_date}")
df = oracle.query(sales_sql.format(start_date=start_date, end_date=end_date))
# 关键过滤：
# - 只取SKU（M_PRODUCTALIAS_ID IS NOT NULL）
# - 只取电商/云仓门店（s.CODE LIKE 'DS%' OR s.IS_ALLO2OSTORAGE='Y'）
# - 只取主销品类（M_DIM4_ID IN 134,142,139,138,141,143,133,136,140,137,144,145）
mysql.to_sql(df, 'dws_sales_daily', if_exists='append')
```

**补数逻辑：**
```python
# 如果需要补历史数据
def backfill(start_date, end_date):
    mysql.execute(f"DELETE FROM dws_sales_daily WHERE date_id >= {start_date} AND date_id <= {end_date}")
    df = oracle.query(sales_sql.format(start=start_date, end=end_date))
    mysql.to_sql(df, 'dws_sales_daily', if_exists='append')
```

---

### 3.4 库存快照逻辑

```python
# 每天记录当天库存状态
today = datetime.now().strftime('%Y%m%d')

# 删除今天旧数据（如果重跑）
mysql.execute(f"DELETE FROM dws_inventory_daily WHERE date_id = {today}")

# 抽取当前库存
df = oracle.query("""
    SELECT 
        fs.C_STORE_ID AS store_id,
        s.CODE AS store_code,
        NVL(s.IS_ALLO2OSTORAGE, 'N') AS is_cloud_store,
        fs.M_PRODUCT_ID AS product_id,
        fs.M_PRODUCTALIAS_ID AS m_productalias_id,
        fs.QTY AS qty,
        fs.QTYVALID AS qty_valid,
        NVL(fs.QTYPURCHASEREM, 0) AS qtypurchaserem
    FROM FA_STORAGE fs
        LEFT JOIN C_STORE s ON fs.C_STORE_ID = s.ID
        LEFT JOIN M_PRODUCT p ON fs.M_PRODUCT_ID = p.ID
    WHERE fs.ISACTIVE = 'Y'
      AND fs.M_PRODUCTALIAS_ID IS NOT NULL
      AND (s.CODE = '001' OR s.IS_ALLO2OSTORAGE = 'Y')
      AND p.M_DIM4_ID IN (134,142,139,138,141,143,133,136,140,137,144,145)
""")
df['date_id'] = int(today)
df['qty_occupy'] = 0

# 写入
mysql.to_sql(df, 'dws_inventory_daily', if_exists='append')
```

---

### 3.5 达播CSV同步逻辑

> 说明：达播数据ETL已独立为外部项目，本仓库仅保留流程概览与口径说明。

```
触发方式：监听例行/紧急目录
处理流程：读取CSV → 字段校验 → 清洗 → 按发货日期+SKU聚合 → SKU匹配校验
写入策略：删除近60天数据后插入
异常处理：命名不符/校验失败/重复文件 → 隔离或跳过
```

**为什么要每日快照**：
- 库存是状态数据，今天的库存明天就变了
- 快照可以分析库存趋势
- 可以追溯历史某天的库存

---

### 3.6 应用表计算逻辑

ads_inventory_health不从Oracle抽，而是在MySQL内计算：

```sql
-- 数据来源
库存数据 ← dws_inventory_daily (当天)
销售数据 ← dws_sales_daily (近30天)
达播销量 ← ads_dabo_daily_sales (近30天/近7天)
商品信息 ← dim_product
SKU信息 ← dim_sku
仓库信息 ← dim_store

-- 计算步骤
1. 汇总库存（总仓+云仓）
2. 汇总销售（近30天/近7天）
3. 计算周转天数
4. 判断库存状态
5. 计算ABC分级
6. 生成建议补货
7. 计算自然销量与自然加速度（全量销量 - 达播销量）
```

---

## 四、调度与监控

### 4.1 调度方式

**方式一：Windows任务计划程序**
```batch
@echo off
cd /d C:\Users\tianhao\PycharmProjects\hefang_dw
python scheduled_etl.py
```

**方式二：run_scheduled_etl.bat**
- 时间：每天凌晨3:00
- 日志：logs/etl_YYYYMMDD.log

---

### 4.2 异常处理

| 异常 | 处理 |
|------|------|
| Oracle连接失败 | 重试3次，失败则告警 |
| MySQL写入失败 | 回滚，记录日志 |
| 数据量异常（差>10%） | 告警，人工确认 |
| ETL超时（>1小时） | 强制终止，告警 |

---

### 4.3 监控检查

**每日检查项：**
- [ ] ETL是否成功完成
- [ ] 各表记录数是否正常
- [ ] 昨日销售额是否有数据
- [ ] 库存快照是否生成

**快速检查SQL：**
```sql
-- 查看最新数据日期
SELECT 'dws_sales_daily' AS tbl, MAX(date_id) AS latest 
FROM dws_sales_daily
UNION ALL
SELECT 'dws_inventory_daily', MAX(date_id) 
FROM dws_inventory_daily
UNION ALL
SELECT 'ads_inventory_health', MAX(snapshot_date) 
FROM ads_inventory_health;

-- 查看昨日销售额
SELECT date_id, SUM(sales_amount) AS 销售额
FROM dws_sales_daily
WHERE date_id = DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '%Y%m%d')
GROUP BY date_id;
```

---

### 4.4 数据质量检查

**验证方法：**

1. **数据源验证**
   - 总库存 vs ERP系统（差异<1%）
   - 销售额 vs 各渠道后台（差异<3%）

2. **抽样验证**
   - 仓库抽查10个SKU实物库存
   - 商品部确认滞销商品清单
   - 运营确认TOP10热销排名

3. **签字确认**
   - 商品部：类别筛选、滞销判断
   - 仓库：库存数量
   - 运营：销售数据、周转阈值

---

### 4.5 常见问题排查

**问题1：ETL执行失败**
```bash
# 查看日志
tail -f logs/etl_20260120.log

# 手动重跑
python scheduled_etl.py
```

**问题2：数据量异常**
```sql
-- 检查记录数变化
SELECT 
    DATE(etl_time) AS 日期,
    COUNT(*) AS 记录数
FROM dws_inventory_daily
GROUP BY DATE(etl_time)
ORDER BY 日期 DESC
LIMIT 7;
```

**问题3：数据对不上**
- 检查筛选条件（ISACTIVE='Y', STATUS=2）
- 检查仓库口径（总仓+云仓）
- 检查类别筛选（主销品ID列表）
- 检查日期范围

---

### 4.6 ETL配置文件

**config.py示例：**
```python
# Oracle配置
ORACLE_CONFIG = {
    'user': 'username',
    'password': 'password',
    'host': '192.168.1.100',
    'port': 1521,
    'service_name': 'ORCL'
}

# MySQL配置
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'dba',
    'password': 'password',
    'database': 'hefang_dw',
    'charset': 'utf8mb4'
}

# ETL配置
ETL_CONFIG = {
    'days_back': 1,  # 回溯天数
    'max_retries': 3,  # 最大重试次数
    'timeout': 3600,  # 超时时间（秒）
}
```

---

*文档版本: 2.1 | 更新日期: 2026-01-30 | 合并文档5、17*
