# IPAM 系统配置
# ============================

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# 数据库配置
# DB_TYPE: "sqlite" 或 "mysql"
# 默认 SQLite 本地存储（无网络依赖）
DB_TYPE = os.environ.get("DB_TYPE", "sqlite")

# SQLite
DB_PATH = DATA_DIR / "ipam.db"

# MySQL (可选，部署时填写)
DB_MYSQL_HOST = os.environ.get("DB_MYSQL_HOST", "localhost")
DB_MYSQL_PORT = int(os.environ.get("DB_MYSQL_PORT", 3306))
DB_MYSQL_USER = os.environ.get("DB_MYSQL_USER", "root")
DB_MYSQL_PASSWORD = os.environ.get("DB_MYSQL_PASSWORD", "")
DB_MYSQL_DATABASE = os.environ.get("DB_MYSQL_DATABASE", "ipam")

# Web 服务
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5100))
DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

# SSH 连接
SSH_TIMEOUT = int(os.environ.get("SSH_TIMEOUT", 10))

# 扫描
ARP_SCAN_TIMEOUT = int(os.environ.get("ARP_SCAN_TIMEOUT", 30))

# 备份
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", 30))

# 确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def get_db_url():
    """获取数据库连接字符串"""
    if DB_TYPE == "mysql":
        return (f"mysql+pymysql://{DB_MYSQL_USER}:{DB_MYSQL_PASSWORD}"
                f"@{DB_MYSQL_HOST}:{DB_MYSQL_PORT}/{DB_MYSQL_DATABASE}")
    return f"sqlite:///{DB_PATH}"