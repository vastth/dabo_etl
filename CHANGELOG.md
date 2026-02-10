# 更新日志

## 2026-02-02 初始化
- 创建项目结构（config/, src/, logs/, temp/）
- 添加 requirements.txt
- 添加配置模板 config/config.yaml
- 添加 MySQL 建表脚本
- 新增日志模块与配置加载
- 新增数据库处理、ETL处理、文件监听、主入口

## 2026-02-02 路径与环境变量
- NAS路径调整为实际UNC路径
- 数据库连接改为环境变量读取（MYSQL_* / ORACLE_*)
- 配置与代码适配现有环境变量

## 2026-02-02 监听与运行
- 增加启动时扫描历史CSV
- 增加运行心跳日志
- 处理后文件重命名为 dabo_data_时间戳.csv

## 2026-02-03 数据质量与防护
- 严格字段与类型校验
- 文件名校验：dabo_YYYYMMDD.csv
- 文件hash去重
- 异常文件隔离目录
- 新增运营上传指南

## 2026-02-03 文档同步
- 更新数据字典，加入 ads_dabo_daily_sales/log_dabo_import
- 更新数据结构映射与ETL手册
- SQL开发手册新增达播示例并调整编号

## 2026-02-04 稳定性与健壮性
- CSV编码回退（UTF-8-SIG/GBK）
- 数字字段规范化（去逗号/币符）
- 文件锁定等待与重试
- 去重事件防抖
- 处理耗时/文件大小/重试次数日志

## 2026-02-04 幂等与策略优化
- 新增 MySQL `ON DUPLICATE KEY UPDATE`（UPSERT）以增强写入幂等性；代码同时保留按配置删除近 N 天数据的选项（`etl.delete_days`），用于避免重复聚合导致的重复写入。
- SKU匹配率阈值低于配置则拒绝入库
- 处理重试与退避策略配置化

## 2026-02-09 告警集成与文档
- 添加企业微信机器人告警支持（可通过 `WECHAT_WEBHOOK` 环境变量或 `config/config.yaml` 配置）
- 在 `src` 中新增 `alerts.py`，并在 `main.py` / `file_watcher.py` 集成成功/失败告警
- 增加配置项：`notifications.enabled`, `notifications.timeout`, `notifications.top_n`, `notifications.max_len`
- 完成集成测试并在 README 中记录启用与测试说明
