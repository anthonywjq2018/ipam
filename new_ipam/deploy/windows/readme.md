# IPAM Windows 绿色版使用说明

## 目录结构
```
ipam/
├── deploy/windows/
│   ├── start.bat   # 启动脚本
│   └── stop.bat    # 停止脚本
├── app.py          # 主程序
├── requirements.txt# 依赖列表
└── ...             # 其他文件
```

## 使用方法

### 首次使用
1. 确保已安装 Python 3.8+，并将其加入系统 PATH
2. 双击 `deploy/windows/start.bat` 启动应用
3. 首次运行会自动创建虚拟环境并安装依赖
4. 等待提示 "启动 IPAM 系统..." 后，浏览器应自动打开或手动访问 http://localhost:5100
5. 默认账号：`admin`，密码：`Admin@123`

### 日常使用
- 双击 `start.bat` 启动
- 关闭启动窗口或双击 `stop.bat` 停止服务

### 注意事项
- 首次运行可能需要几秒钟来创建虚拟环境和安装依赖
- 应用数据存储在 `data/` 目录下（SQLite 数据库文件为 `data/ipam.db`）
- 如需修改端口、数据库类型等配置，请编辑 `config.py` 文件
- 为了保持密钥一致（用于会话等），请不要删除 `data/secret.key` 文件

### 故障排除
- 如果提示找不到 Python，请安装 Python 并确保其在 PATH 中
- 如果端口被占用，请修改 `start.bat` 中的 `set "PORT=5100"` 为其他端口
- 查看启动窗口的输出以获得详细错误信息