# IPAM - IP 地址管理系统

轻量级的 IP/MAC 地址管理工具，通过 SSH 连接交换机获取 ARP 表，支持人员信息扩展录入。

## ✨ 功能特性

- **交换机管理**：添加/编辑/删除交换机，支持 SSH 连接测试
- **ARP 扫描**：一键通过 SSH 执行 `dis arp` / `show arp` 获取 IP-MAC 绑定
- **多厂商支持**：H3C/Huawei、Cisco、锐捷等，自动解析不同格式输出
- **信息扩展**：在 IP-MAC 基础上录入姓名、手机、办公室、部门、终端类型、操作系统、设备名等
- **Web 界面**：基于 Flask + Bootstrap 5，响应式设计，支持搜索、筛选、分页
- **批量操作**：支持批量编辑、删除、CSV 导入导出
- **扫描日志**：记录每次扫描的发现/新增/更新统计
- **跨平台**：Windows/Linux/macOS 均可运行

## 📋 系统要求

- Python 3.8+
- 操作系统：Windows 10/11、Linux、macOS
- 网络可达交换机 SSH 端口（默认 22）

## 🚀 快速开始

### Windows

双击运行 `run.bat`，或在 PowerShell 中运行 `.\run.ps1`

### Linux / macOS

```bash
chmod +x run.sh
./run.sh
```

### 手动启动

```bash
# 1. 创建虚拟环境（推荐）
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库并启动
python app.py
```

启动后访问：`http://localhost:5100`

## 📖 使用指南

### 1. 添加交换机

点击「交换机管理」→「添加交换机」，填写：
- **名称**：便于识别，如「核心交换机-1F」
- **IP**：交换机管理 IP
- **用户名/密码**：SSH 登录凭据
- **厂商**：选择对应品牌（影响 ARP 命令解析）
- **位置/备注**：可选

### 2. 扫描 ARP 表

在交换机列表点击详情进入，或在详情页点击「扫描 ARP」按钮。
系统将通过 SSH 连接交换机，执行对应厂商命令：
- H3C/Huawei：`dis arp`
- Cisco：`show arp`

解析结果自动入库，新增/更新统计记录在日志中。

### 3. 完善人员信息

扫描获得基础 IP-MAC 后，点击「编辑」补充：
- **姓名、手机**：人员联系方式
- **办公室、部门**：位置信息
- **终端类型**：PC/笔记本/手机/打印机/摄像头/IoT/服务器等
- **操作系统**：Windows 11 / macOS / Linux 等
- **设备名**：主机名
- **状态**：活跃/非活跃/预留

### 4. 搜索与导出

- 「IP-MAC 绑定」页支持关键词搜索（IP/MAC/姓名/手机/办公室/设备名）
- 支持按交换机、状态筛选
- 「导出 CSV」获取完整数据，「导入 CSV」批量录入

## 🗂 项目结构

```
ipam/
├── app.py              # Flask 主程序
├── config.py           # 配置文件
├── db.py               # 数据库操作 (SQLite)
├── ssh_handler.py      # SSH 连接与 ARP 解析
├── requirements.txt    # Python 依赖
├── run.bat / run.ps1 / run.sh  # 启动脚本
├── data/               # 数据库目录 (自动创建)
│   └── ipam.db
├── templates/          # HTML 模板
│   ├── index.html      # 仪表盘
│   ├── switches.html   # 交换机列表
│   ├── switch_detail.html  # 交换机详情/ARP列表
│   ├── bindings.html   # 所有绑定列表
│   └── logs.html       # 扫描日志
└── static/
    ├── css/style.css   # 自定义样式
    └── js/             # 前端逻辑
        ├── app.js      # 通用工具
        ├── switches.js
        ├── switch_detail.js
        └── bindings.js
```

## 🔧 配置说明

编辑 `config.py` 可调整：
- `PORT`：Web 端口（默认 5100）
- `HOST`：绑定地址（默认 0.0.0.0）
- `SSH_TIMEOUT`：SSH 连接超时（默认 10秒）
- `DB_PATH`：数据库文件路径

## 📦 打包为单文件 exe (Windows)

使用 PyInstaller 打包，无需安装 Python 即可运行：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=NONE --add-data "templates;templates" --add-data "static;static" --add-data "data;data" app.py
```

生成的 `dist/app.exe` 即可直接运行（首次运行会自动创建数据目录）。

> ⚠️ 注意：打包后数据库文件在 exe 同级 `data/ipam.db`，请勿删除 data 文件夹。

## 🛠 常见问题

**Q: SSH 连接失败？**
- 检查交换机是否开启 SSH 服务：`ssh server enable`
- 确认用户名密码正确，且有执行 `dis arp` 权限
- 检查防火墙/ACL 是否放行管理 IP 访问 22 端口

**Q: ARP 解析为空？**
- 尝试在交换机手动执行 `dis arp` 确认有输出
- 部分老旧固件输出格式不同，可在 ssh_handler.py 中调整正则
- 可使用「测试连接」按钮验证 SSH 连通性

**Q: 如何备份数据？**
- 直接复制 `data/ipam.db` 文件即可
- 或使用「导出 CSV」功能导出所有绑定记录

**Q: 修改端口？**
- 编辑 `config.py` 中的 `PORT = 5100`
- 重启服务生效

## 📝 更新日志

- **v1.0** (2026-08-26)
  - 初始版本：交换机管理、ARP扫描、信息扩展、Web界面、CSV导入导出

## 📄 许可证

MIT License - 可自由使用、修改、分发

## 🤝 贡献

欢迎提交 Issue 和 PR 改进功能！