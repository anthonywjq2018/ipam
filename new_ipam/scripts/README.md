# 从 SQLite 迁移到 MySQL

本脚本将旧版 SQLite 数据库（`data/ipam.db`）中的数据导出为 JSON，
再通过系统配置页面的「导入备份」功能导入 MySQL，或直接调用导入接口。

## 使用方法

```bash
# 1. 在旧系统（SQLite 版）执行导出
python3 scripts/export_sqlite.py > ipam_export.json

# 2. 启动新版（MySQL 版）并完成数据源初始化后，导入：
#    方式一：系统配置页面 -> 导入备份 -> 选择 ipam_export.json
#    方式二：调用接口
curl -X POST -u admin:Admin@123 \
  -F "file=@ipam_export.json" \
  http://localhost:5100/api/system/restore
```

导出内容包括：用户、交换机、IP-MAC 绑定、扫描日志、系统配置。
