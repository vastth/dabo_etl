# 架构与审计指南（ARCHITECTURE AND AUDIT GUIDE）

本文档面向数据架构师/审计员，概述 `dabo_etl` 的数据流、关键文件位置、审计要点与运行/排障步骤。

## 1. 高层架构
- 数据源：NAS 目录中按规则命名的 CSV 文件（`dabo_YYYYMMDD.csv`）。
- 处理：`src.file_watcher` 监听并触发 `src.etl_processor` 完整 ETL 流程。
- 校验：ETL 使用 `src.db_handler` 从 Oracle 拉取有效 SKU 列表以验证匹配率。
- 存储：结果写入 MySQL 表 `ads_dabo_daily_sales`（使用 UPSERT 保证幂等）。
- 日志：导入元信息写入 `log_dabo_import` 表，运行日志写到 `logs/`。
- 告警：可选通过企业微信机器人发送，配置来源为 `config/config.yaml`，并支持环境变量 `WECHAT_WEBHOOK` 覆盖。

## 2. 关键文件索引
- ETL 处理：`src/etl_processor.py`
- 数据库操作：`src/db_handler.py`
- 文件监听与流程控制：`src/file_watcher.py`
- CLI 与单次运行：`src/main.py`
- 告警：`src/alerts.py`
- 配置：`config/config.yaml`
- 审计/数据字典：`docs/mysql_data_dictionary.md`

## 3. 数据流（序列）
1. 文件到达 NAS；`file_watcher` 捕获 `on_created` 事件。
2. 文件名校验（`dabo_YYYYMMDD.csv`）与就绪检查（文件可读）。
3. 内容去重：计算 SHA256 并参考 `temp/file_hashes.json` 跳过重复内容。
4. `EtlProcessor.read_csv` -> `clean_and_filter` -> `aggregate` -> `validate_sku`。
5. 删除 MySQL 中最近 N 天数据（由 `etl.delete_days` 配置控制），再调用 `insert_dabo_data` 写入（单事务、UPSERT）。
6. 写入 `log_dabo_import`，并移动文件到 `processed` 或 `quarantine`。
7. 若配置启用，发送企业微信告警（成功/失败摘要）。

## 4. 审计检查表（Checklist）
- 文件层面：确认 `processed` 与 `quarantine` 目录中该文件的移动记录与时间戳是否一致。
- 日志层面：检查 `log_dabo_import` 中对应 `file_name` 的记录：`status`, `records_total`, `records_inserted`, `sku_match_rate`。
- 数据一致性：核对 `ads_dabo_daily_sales` 中受影响的 `sale_date` / `product_alias_code` 行数与 `records_inserted`。
- SKU 匹配：若 `sku_match_rate` 异常偏低，审查 `M_PRODUCT_ALIAS` 表（Oracle）与源文件中的 SKU 列表是否存在版本差异或编码问题。
- 告警：审查 `logs/` 中关于告警发送的记录，确认 webhook 是否返回 `errcode==0`。

## 5. 常见故障与排障步骤
1. 文件被跳过为重复（SKIPPED_DUPLICATE）：
   - 检查 `temp/file_hashes.json` 是否包含该文件的 hash；若误判请清理对应 hash 并手动重跑。
2. 文件移至隔离（quarantine）：
   - 查看 `log_dabo_import.message` 中的错误摘要，常见为解析错误或 SKU 匹配率低；根据错误类型手动修正文件或联系业务方。
3. 写库失败/回滚：
   - 检查 `logs/` 的 exception 信息；确认 MySQL 配置、网络以及表结构与约束（唯一键）是否正确。
4. 告警未接收：
   - 验证 `WECHAT_WEBHOOK` 是否配置且可访问；查看 `src/alerts.py` 的发送日志与企业微信返回值。

## 6. 安全与部署建议
- 不要将 webhook 或数据库明文凭证提交到仓库，使用 `*_env` 配置项或 CI/CD 机密注入环境变量。
- 在高可用或并发场景中，将 `temp/file_hashes.json` 替换为中央存储（Redis / DB）以避免竞态。
- 将告警发送改为异步（消息队列或后台线程）以避免阻塞主流程。

## 7. 建议的改进清单（供未来迭代）
- 告警：实现异步发送 + 重试 + 聚合策略；增加告警级别（INFO/WARN/CRITICAL）。
- 测试：为 `alerts` 模块添加单元测试（mock requests），为 ETL 添加端到端测试用例（小型样例 CSV）。
- 监控：导出关键指标（处理时延、失败率、SKU 匹配率）到 Prometheus 或其他监控系统。

----
_文档由代码注释与仓库结构同步生成，审计时可按上文索引快速定位实现。_
