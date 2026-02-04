# 达播数据ETL项目需求文档

## 项目背景
我需要处理达播（直播带货）订单数据，净化库存看板的销量计算。

## 数据源
- CSV文件从NAS获取
- 运营手动导出上传
- 两个文件夹：例行更新（每周）、紧急更新（达播期间每天）

## 数据结构
CSV字段：
- 主订单编号: 19位数字
- 子订单编号: 19位数字
- 商家编码: SKU条码，对应MySQL的M_PRODUCT_ALIAS.NO
- 商品数量: 销量
- 订单状态: 筛选"已完成"和"已发货"
- 发货时间: 转为日期格式
- 商家收入金额: 实收金额

## 处理流程
1. 监控NAS文件夹（/mnt/dabo_data/例行更新 和 /mnt/dabo_data/紧急更新）
2. 发现CSV文件后读取
3. 筛选订单状态为"已完成"和"已发货"
4. 清洗商家编码（去除\t等）
5. 按发货日期+商家编码聚合
6. 验证SKU匹配率（与Oracle的M_PRODUCT_ALIAS.NO对比）
7. 删除MySQL近60天的旧数据
8. 插入新数据到ads_dabo_daily_sales表
9. 记录处理日志到log_dabo_import表
10. 移动文件到已处理文件夹

## 数据库
MySQL目标表：ads_dabo_daily_sales
- sale_date: DATE
- product_alias_code: VARCHAR(100)
- dabo_sales_qty: INT
- dabo_order_count: INT  
- dabo_revenue: DECIMAL(12,2)

Oracle查询表：M_PRODUCT_ALIAS (用于SKU验证)

## 技术栈
- Python 3.8+
- pandas
- SQLAlchemy
- pymysql
- oracledb

## 配置文件
使用YAML配置文件存储：
- NAS路径
- MySQL/Oracle连接信息
- 处理参数（SKU匹配阈值、删除天数范围等）