# 何方珠宝 - SQL开发手册

> SQL模板 | 开发规范 | 常用场景 | 快速参考

---

## 📋 目录

1. [必须遵守的规则](#一必须遵守的规则)
2. [标准SQL模板](#二标准sql模板)
3. [常用分析场景](#三常用分析场景)
4. [快速参考卡片](#四快速参考卡片)

---

## 一、必须遵守的规则

### 1.1 每个查询必加的条件

```sql
-- 零售单必加
WHERE r.ISACTIVE = 'Y' AND r.STATUS = 2

-- 库存表必加
WHERE fs.ISACTIVE = 'Y'

-- 商品表必加
WHERE p.ISACTIVE = 'Y'
```

---

### 1.2 主销品类别筛选

```sql
-- 这个ID列表要背下来
AND p.M_DIM4_ID IN (134,142,139,138,141,143,133,136,140,137,144,145)
```

---

### 1.3 电商可售库存口径

```sql
-- 总仓+云仓，不要只写总仓
AND (s.CODE = '001' OR s.IS_ALLO2OSTORAGE = 'Y')
```

---

### 1.4 SKU过滤（必加）

```sql
-- 只保留SKU级别明细
AND ri.M_PRODUCTALIAS_ID IS NOT NULL
```

---

### 1.5 日期格式

```sql
-- Oracle日期是NUMBER(8)，格式YYYYMMDD
WHERE BILLDATE = 20260113
WHERE BILLDATE >= TO_NUMBER(TO_CHAR(SYSDATE-30, 'YYYYMMDD'))

-- MySQL日期
WHERE date_id = DATE_FORMAT(CURDATE(), '%Y%m%d')
WHERE date_id >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 30 DAY), '%Y%m%d')
```

---

## 二、标准SQL模板

### 2.1 标准JOIN模板（Oracle）

```sql
-- 零售数据标准写法
FROM M_RETAILITEM ri
LEFT JOIN M_RETAIL r ON ri.M_RETAIL_ID = r.ID
LEFT JOIN M_PRODUCT p ON ri.M_PRODUCT_ID = p.ID
LEFT JOIN M_DIM d4 ON p.M_DIM4_ID = d4.ID        -- 类别
LEFT JOIN M_DIM d5 ON p.M_DIM5_ID = d5.ID        -- 性质
LEFT JOIN M_DIM d6 ON p.M_DIM6_ID = d6.ID        -- 系列
LEFT JOIN C_STORE s ON r.C_STORE_ID = s.ID
WHERE r.ISACTIVE = 'Y' AND r.STATUS = 2
    AND p.M_DIM4_ID IN (134,142,139,138,141,143,133,136,140,137,144,145)
    AND ri.M_PRODUCTALIAS_ID IS NOT NULL
    AND (s.CODE LIKE 'DS%' OR s.IS_ALLO2OSTORAGE = 'Y')

-- 库存数据标准写法
FROM FA_STORAGE fs
LEFT JOIN M_PRODUCT p ON fs.M_PRODUCT_ID = p.ID
LEFT JOIN M_DIM d4 ON p.M_DIM4_ID = d4.ID
LEFT JOIN C_STORE s ON fs.C_STORE_ID = s.ID
WHERE fs.ISACTIVE = 'Y'
    AND (s.CODE = '001' OR s.IS_ALLO2OSTORAGE = 'Y')
    AND fs.M_PRODUCTALIAS_ID IS NOT NULL
    AND p.M_DIM4_ID IN (134,142,139,138,141,143,133,136,140,137,144,145)
```

---

### 2.2 销售指标计算模板

```sql
-- 销售数量（出库）
SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.QTY ELSE 0 END) AS 销售数量,

-- 退货数量（入库）
SUM(CASE WHEN r.TOT_AMT_ACTUAL < 0 THEN ABS(ri.QTY) ELSE 0 END) AS 退货数量,

-- 销售金额
SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.TOT_AMT_ACTUAL ELSE 0 END) AS 销售额,

-- 退货金额
SUM(CASE WHEN r.TOT_AMT_ACTUAL < 0 THEN ABS(ri.TOT_AMT_ACTUAL) ELSE 0 END) AS 退货额,

-- 净销量
SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.QTY ELSE 0 END) 
  - SUM(CASE WHEN r.TOT_AMT_ACTUAL < 0 THEN ABS(ri.QTY) ELSE 0 END) AS 净销量,

-- 净销售额
SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.TOT_AMT_ACTUAL ELSE 0 END)
  - SUM(CASE WHEN r.TOT_AMT_ACTUAL < 0 THEN ABS(ri.TOT_AMT_ACTUAL) ELSE 0 END) AS 净销售额,

-- 客单价
SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.TOT_AMT_ACTUAL ELSE 0 END) 
  / NULLIF(COUNT(DISTINCT CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN r.ID END), 0) AS 客单价,

-- 退货率
SUM(CASE WHEN r.TOT_AMT_ACTUAL < 0 THEN ABS(ri.TOT_AMT_ACTUAL) ELSE 0 END) 
  / NULLIF(SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.TOT_AMT_ACTUAL ELSE 0 END), 0) AS 退货率
```

---

### 2.3 库存指标计算模板

```sql
-- 周转天数（Oracle）
CASE 
    WHEN NVL(销售数量, 0) = 0 THEN 9999 
    ELSE ROUND(库存数量 / (销售数量 / 30), 1)
END AS 库存周转天数,

-- 周转天数（MySQL）
CASE 
    WHEN COALESCE(销售数量, 0) = 0 THEN 9999
    ELSE ROUND(库存数量 / (销售数量 / 30), 1)
END AS 库存周转天数,

-- 库存状态
CASE 
    WHEN 库存数量 > 0 AND 销售数量 = 0 THEN '滞销'
    WHEN 销售数量 > 0 AND 周转天数 < 30 THEN '紧急缺货'
    WHEN 销售数量 > 0 AND 周转天数 < 70 THEN '需补货'
    WHEN 销售数量 > 0 AND 周转天数 > 90 THEN '库存过高'
    ELSE '正常'
END AS 库存状态,

-- 建议补货（允许负数表示库存过剩）
CASE 
    WHEN 销售数量 = 0 THEN 0
    WHEN 周转天数 >= 90 THEN 0
    ELSE ROUND(
        (90 - 周转天数) * (销售数量 / 30) 
        - 退货数量 
        - 采购欠数
    , 0)
END AS 建议补货数量
```

---

### 2.4 常用筛选条件速查

```sql
-- 电商渠道
WHERE s.CODE LIKE 'DS%'

-- 线下门店
WHERE s.CODE LIKE 'RT%'

-- 中山总仓
WHERE s.CODE = '001'

-- 云仓
WHERE s.IS_ALLO2OSTORAGE = 'Y'

-- 总仓+云仓
WHERE (s.CODE = '001' OR s.IS_ALLO2OSTORAGE = 'Y')

-- 天猫
WHERE s.CODE = 'DS001'

-- 抖音
WHERE s.CODE = 'DS009'

-- 在售款
WHERE p.M_DIM5_ID IN (224, 296, 297)

-- 新品
WHERE p.M_DIM5_ID IN (225, 298, 299)

-- 绝版款
WHERE p.M_DIM5_ID IN (127, 126, 152)

-- 近30天
WHERE BILLDATE >= TO_NUMBER(TO_CHAR(SYSDATE-30, 'YYYYMMDD'))

-- 近7天
WHERE BILLDATE >= TO_NUMBER(TO_CHAR(SYSDATE-7, 'YYYYMMDD'))

-- 昨天
WHERE BILLDATE = TO_NUMBER(TO_CHAR(SYSDATE-1, 'YYYYMMDD'))

-- 本月
WHERE BILLDATE >= TO_NUMBER(TO_CHAR(TRUNC(SYSDATE, 'MM'), 'YYYYMMDD'))
```

---

## 三、常用分析场景

### 3.1 昨日各渠道销售

```sql
-- 业务问题：昨天各渠道卖了多少？
SELECT
    s.NAME AS 渠道,
    SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.TOT_AMT_ACTUAL ELSE 0 END) AS 销售额,
    SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.QTY ELSE 0 END) AS 销量
FROM M_RETAILITEM ri
LEFT JOIN M_RETAIL r ON ri.M_RETAIL_ID = r.ID
LEFT JOIN M_PRODUCT p ON ri.M_PRODUCT_ID = p.ID
LEFT JOIN C_STORE s ON r.C_STORE_ID = s.ID
WHERE r.ISACTIVE = 'Y' AND r.STATUS = 2
    AND r.BILLDATE = TO_NUMBER(TO_CHAR(SYSDATE-1, 'YYYYMMDD'))
    AND ri.M_PRODUCTALIAS_ID IS NOT NULL
    AND (s.CODE LIKE 'DS%' OR s.IS_ALLO2OSTORAGE = 'Y')
    AND p.M_DIM4_ID IN (134,142,139,138,141,143,133,136,140,137,144,145)
GROUP BY s.NAME
ORDER BY 销售额 DESC;
```

---

### 3.2 本月TOP10商品

```sql
-- 业务问题：这个月哪些款卖得最好？
SELECT * FROM (
    SELECT
        p.NAME AS 商品编码,
        p.VALUE AS 商品名称,
        d4.ATTRIBNAME AS 类别,
        SUM(ri.QTY) AS 销量,
        SUM(ri.TOT_AMT_ACTUAL) AS 销售额,
        ROW_NUMBER() OVER (ORDER BY SUM(ri.TOT_AMT_ACTUAL) DESC) AS 排名
    FROM M_RETAILITEM ri
    LEFT JOIN M_RETAIL r ON ri.M_RETAIL_ID = r.ID
    LEFT JOIN M_PRODUCT p ON ri.M_PRODUCT_ID = p.ID
    LEFT JOIN C_STORE s ON r.C_STORE_ID = s.ID
    LEFT JOIN M_DIM d4 ON p.M_DIM4_ID = d4.ID
    WHERE r.ISACTIVE = 'Y' AND r.STATUS = 2
        AND r.TOT_AMT_ACTUAL > 0
        AND r.BILLDATE >= TO_NUMBER(TO_CHAR(TRUNC(SYSDATE, 'MM'), 'YYYYMMDD'))
        AND ri.M_PRODUCTALIAS_ID IS NOT NULL
        AND (s.CODE LIKE 'DS%' OR s.IS_ALLO2OSTORAGE = 'Y')
        AND p.M_DIM4_ID IN (134,142,139,138,141,143,133,136,140,137,144,145)
    GROUP BY p.NAME, p.VALUE, d4.ATTRIBNAME
)
WHERE 排名 <= 10;
```

---

### 3.3 日销售趋势

```sql
-- 业务问题：最近30天销售趋势如何？
SELECT
    r.BILLDATE AS 日期,
    SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.TOT_AMT_ACTUAL ELSE 0 END) AS 销售额
FROM M_RETAILITEM ri
LEFT JOIN M_RETAIL r ON ri.M_RETAIL_ID = r.ID
LEFT JOIN M_PRODUCT p ON ri.M_PRODUCT_ID = p.ID
LEFT JOIN C_STORE s ON r.C_STORE_ID = s.ID
WHERE r.ISACTIVE = 'Y' AND r.STATUS = 2
    AND r.BILLDATE >= TO_NUMBER(TO_CHAR(SYSDATE-30, 'YYYYMMDD'))
    AND ri.M_PRODUCTALIAS_ID IS NOT NULL
    AND (s.CODE LIKE 'DS%' OR s.IS_ALLO2OSTORAGE = 'Y')
    AND p.M_DIM4_ID IN (134,142,139,138,141,143,133,136,140,137,144,145)
GROUP BY r.BILLDATE
ORDER BY r.BILLDATE;
```

---

### 3.4 达播日销售汇总

```sql
-- 业务问题：达播每天销量和销售额
SELECT
    sale_date AS 日期,
    SUM(dabo_sales_qty) AS 销量,
    SUM(dabo_revenue) AS 销售额,
    SUM(dabo_order_count) AS 订单数
FROM ads_dabo_daily_sales
WHERE sale_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY sale_date
ORDER BY sale_date;
```

---

### 3.5 缺货商品清单（MySQL）

```sql
-- 业务问题：哪些A类商品要断货了？
SELECT
    product_code AS 商品编码,
    product_name AS 商品名称,
    category_name AS 类别,
    total_qty AS 库存,
    turnover_days AS 周转天数,
    suggest_qty AS 建议补货
FROM ads_inventory_health
WHERE snapshot_date = CURDATE()
    AND sku_grade = 'A'
    AND inventory_status IN ('紧急缺货', '需补货')
ORDER BY turnover_days;
```

---

### 3.6 滞销商品清单（MySQL）

```sql
-- 业务问题：哪些货卖不动？
SELECT
    product_code AS 商品编码,
    product_name AS 商品名称,
    category_name AS 类别,
    total_qty AS 库存,
    total_qty * price_list AS 库存金额
FROM ads_inventory_health ih
LEFT JOIN dim_product p ON ih.product_id = p.product_id
WHERE snapshot_date = CURDATE()
    AND inventory_status = '滞销'
ORDER BY 库存金额 DESC;
```

---

### 3.7 各类别库存分布（MySQL）

```sql
-- 业务问题：库存在各品类怎么分布？
SELECT
    category_name AS 类别,
    SUM(total_qty) AS 库存数量,
    COUNT(*) AS SKU数,
    SUM(CASE WHEN inventory_status = '紧急缺货' THEN 1 ELSE 0 END) AS 缺货SKU
FROM ads_inventory_health
WHERE snapshot_date = CURDATE()
GROUP BY category_name
ORDER BY 库存数量 DESC;
```

---

### 3.8 同比分析（Oracle）

```sql
-- 业务问题：和去年同期比怎么样？
WITH 
today AS (
    SELECT SUM(TOT_AMT_ACTUAL) AS 销售额
    FROM M_RETAIL
    WHERE ISACTIVE = 'Y' AND STATUS = 2 AND TOT_AMT_ACTUAL > 0
        AND BILLDATE = TO_NUMBER(TO_CHAR(SYSDATE-1, 'YYYYMMDD'))
),
lastyear AS (
    SELECT SUM(TOT_AMT_ACTUAL) AS 销售额
    FROM M_RETAIL
    WHERE ISACTIVE = 'Y' AND STATUS = 2 AND TOT_AMT_ACTUAL > 0
        AND BILLDATE = TO_NUMBER(TO_CHAR(SYSDATE-365, 'YYYYMMDD'))
)
SELECT
    t.销售额 AS 昨日销售额,
    l.销售额 AS 去年同期,
    ROUND((t.销售额 - l.销售额) / NULLIF(l.销售额, 0) * 100, 2) AS 同比增长率
FROM today t, lastyear l;
```

---

### 3.9 退货分析（Oracle）

```sql
-- 业务问题：退货率高的商品有哪些？
SELECT
    p.NAME AS 商品编码,
    SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.TOT_AMT_ACTUAL ELSE 0 END) AS 销售额,
    SUM(CASE WHEN r.TOT_AMT_ACTUAL < 0 THEN ABS(ri.TOT_AMT_ACTUAL) ELSE 0 END) AS 退货额,
    ROUND(
        SUM(CASE WHEN r.TOT_AMT_ACTUAL < 0 THEN ABS(ri.TOT_AMT_ACTUAL) ELSE 0 END) /
        NULLIF(SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.TOT_AMT_ACTUAL ELSE 0 END), 0) * 100
    , 2) AS 退货率
FROM M_RETAILITEM ri
LEFT JOIN M_RETAIL r ON ri.M_RETAIL_ID = r.ID
LEFT JOIN M_PRODUCT p ON ri.M_PRODUCT_ID = p.ID
LEFT JOIN C_STORE s ON r.C_STORE_ID = s.ID
WHERE r.ISACTIVE = 'Y' AND r.STATUS = 2
    AND r.BILLDATE >= TO_NUMBER(TO_CHAR(SYSDATE-30, 'YYYYMMDD'))
    AND ri.M_PRODUCTALIAS_ID IS NOT NULL
    AND (s.CODE LIKE 'DS%' OR s.IS_ALLO2OSTORAGE = 'Y')
    AND p.M_DIM4_ID IN (134,142,139,138,141,143,133,136,140,137,144,145)
GROUP BY p.NAME
HAVING SUM(CASE WHEN r.TOT_AMT_ACTUAL > 0 THEN ri.TOT_AMT_ACTUAL ELSE 0 END) > 10000
ORDER BY 退货率 DESC;
```

---

## 四、快速参考卡片

### 4.1 开发检查清单

写完SQL后检查：
- [ ] ISACTIVE = 'Y' 加了？
- [ ] STATUS = 2 加了（零售单）？
- [ ] 主销品类别筛选了？
- [ ] SKU过滤（M_PRODUCTALIAS_ID IS NOT NULL）加了？
- [ ] 渠道口径（DS%或云仓）加了？
- [ ] 日期范围正确？
- [ ] 仓库口径是总仓+云仓？
- [ ] 正负单分开统计了？
- [ ] 空值用NVL/COALESCE处理了？

---

### 4.2 Oracle特有语法

```sql
-- 空值处理
NVL(字段, 0)

-- 字符串拼接
字段1 || '-' || 字段2

-- 日期转数字
TO_NUMBER(TO_CHAR(SYSDATE, 'YYYYMMDD'))

-- 避免除零
NULLIF(分母, 0)

-- 四舍五入
ROUND(数值, 小数位数)

-- 窗口函数
ROW_NUMBER() OVER (ORDER BY 字段 DESC)
SUM(字段) OVER (PARTITION BY 分组字段)
```

---

### 4.3 MySQL特有语法

```sql
-- 空值处理
COALESCE(字段, 0)

-- 字符串拼接
CONCAT(字段1, '-', 字段2)

-- 日期转数字
DATE_FORMAT(CURDATE(), '%Y%m%d')

-- 日期计算
DATE_SUB(CURDATE(), INTERVAL 30 DAY)

-- 四舍五入
ROUND(数值, 小数位数)
```

---

### 4.4 核心ID速查

**主销品类别：**
```
134,142,139,138,141,143,133,136,140,137,144,145
```

**在售款性质：**
```
224,296,297
```

**新品性质：**
```
225,298,299
```

**绝版款性质：**
```
127,126,152
```

---

### 4.5 常用渠道店仓

| 渠道 | 店仓CODE |
|------|----------|
| 天猫 | DS001 |
| 抖音 | DS009 |
| 京东 | DS002 |
| 小红书 | DS006 |
| 中山总仓 | 001 |

---

*文档版本: 2.1 | 更新日期: 2026-01-30 | 合并文档4、15、19*
