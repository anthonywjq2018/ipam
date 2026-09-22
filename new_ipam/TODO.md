# IPAM 数据源改造：去 SQLite + 添加交换机前置条件

## 目标
1. 去掉 SQLite，全部改用 MySQL
2. 使用前必须先配置数据源、创建相关表，否则禁止"添加交换机"等写操作

## 阶段 1：配置层（config.py）
- [ ] 删除 DB_TYPE / DB_PATH / sqlite 分支 / get_db_url
- [ ] 新增 data/db_config.json 动态数据源配置（env 变量为默认值）
- [ ] load_db_config() / save_db_config()

## 阶段 2：数据库层（db/__init__.py）
- [ ] 删除 SQLite 分支、PRAGMA
- [ ] 修正 MySQL 建表语句 AUTOINCREMENT -> AUTO_INCREMENT
- [ ] get_db() 动态读取配置 + 连接缓存/ping
- [ ] check_datasource()：configured / connected / database_created / tables_created
- [ ] init_database()：建库 + 建表 + 注册默认管理员（手动触发，不再启动自动执行）

## 阶段 3：Service 层 SQL 兼容
- [ ] services/*.py 全部 ? 占位符 -> %s（PyMySQL）
- [ ] system_service.test_database_connection 去 sqlite 分支
- [ ] system_service import_all_data 去 sqlite_sequence / PRAGMA
- [ ] utils backup/restore 改为 MySQL 数据导出/导入（JSON）

## 阶段 4：后端路由（app.py）
- [ ] 启动不再自动 init_db / register_default_admin
- [ ] GET /api/system/datasource/status（免登录，初始化向导用）
- [ ] POST /api/system/datasource/test（测试连接）
- [ ] POST /api/system/datasource/config（保存配置；未初始化时免登录）
- [ ] POST /api/system/datasource/init（建库+建表+默认管理员）
- [ ] add_switch / add_binding / scan 前置 require_db_ready() 检查
- [ ] /api/system/health 返回数据源状态

## 阶段 5：前端
- [ ] system.html：数据源配置卡片 + 初始化向导（测试/保存/初始化按钮，状态显示）
- [ ] switches.html：未就绪时禁用"添加交换机"并显示横幅跳转配置
- [ ] base.html：未初始化全局提示（可选）

## 阶段 6：部署与迁移
- [ ] docker-compose 加 MySQL 服务 + 健康依赖
- [ ] SQLite -> MySQL 数据迁移脚本（迁现有 1 交换机 + 4 绑定 + 用户）
- [ ] requirements.txt 去除 sqlite 依赖（sqlite 为内置，无需）
- [ ] 重建镜像、部署、浏览器实测全流程

## 约束
- 端口 5100:5100 不变
- 默认凭据 admin/Admin@123 不变（初始化时创建）
- 前端样式保持当前 IT 深色主题
