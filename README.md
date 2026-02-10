# 达播数据ETL

## 项目简介
处理达播订单CSV数据，清洗并聚合到MySQL应用表，支持NAS目录监听、去重、异常隔离。

## 目录结构
- config/: 配置文件
- docs/: 业务与数仓文档
- logs/: 运行日志
- sql/: 建表SQL
- src/: 源代码
- temp/: 临时文件（如hash记录）

## 环境依赖
- Python 3.8+
- 依赖见 requirements.txt

## 配置说明
编辑 config/config.yaml：
- nas: 例行/紧急/已处理/隔离目录
- mysql/oracle: 从环境变量读取连接信息

环境变量（示例）：
- MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB / MYSQL_CHARSET
- ORACLE_HOST / ORACLE_PORT / ORACLE_SERVICE / ORACLE_USER / ORACLE_PASSWORD
- 或直接提供 ORACLE_DSN

告警（企业微信机器人）
 - 项目支持通过企业微信机器人发送处理结果告警（成功/失败）。
 - 优先从环境变量 `WECHAT_WEBHOOK` 读取 webhook 地址；如未设置，可在 `config/config.yaml` 中配置 `notifications.wechat_webhook`。
 - 若不配置或环境变量为空，则不会发送告警。

设置示例：
 - PowerShell (Windows):
 ```powershell
 $Env:WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx"
 ```
 - Bash (Linux/macOS):
 ```bash
 export WECHAT_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx"
 ```

说明：告警文本包含文件名、处理时间、插入条数、SKU 匹配率与 top SKU 分布摘要，便于快速确认数据状态。

测试说明：
- 我们已完成企业微信告警的集成测试（2026-02-09），包括成功与失败两种场景验证。
- 我们已完成企业微信告警的集成测试（2026-02-09），包括成功与失败两种场景验证。
- 默认告警为启用，配置项 `notifications.enabled` 默认为 `true`；若希望禁用，请将其设置为 `false`。
- 你可以直接在 `config/config.yaml` 中设置 `notifications.wechat_webhook`，或通过环境变量 `WECHAT_WEBHOOK` 提供 webhook（环境变量优先）。
- 测试要点：确保 `WECHAT_WEBHOOK` 指向企业微信机器人 webhook 且 webhook 已被允许接收消息。

## 建表
执行 [sql/create_tables_mysql.sql](sql/create_tables_mysql.sql) 创建：
- ads_dabo_daily_sales
- log_dabo_import

## 运行方式
监听模式：
- python -m src.main --watch

单文件模式：
- python -m src.main --file <csv_path>

## 文件规则
- 仅接受文件名格式：dabo_YYYYMMDD.csv
- 重复文件（hash一致）自动跳过
- 异常文件移动到隔离目录

## 日志
- 日志输出到 logs/
- 按天与大小轮转
- 心跳日志用于确认监听在运行
