# IPAM 系统配置
# ============================

import os
import json
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# ==================== 数据源（仅 MySQL）====================
# 数据源配置保存在 data/db_config.json，可在系统配置页面动态修改。
# 环境变量仅作为首次部署的默认值写入。
DB_CONFIG_FILE = DATA_DIR / "db_config.json"

DB_MYSQL_HOST = os.environ.get("DB_MYSQL_HOST", "localhost")
DB_MYSQL_PORT = int(os.environ.get("DB_MYSQL_PORT", 3306))
DB_MYSQL_USER = os.environ.get("DB_MYSQL_USER", "root")
DB_MYSQL_PASSWORD = os.environ.get("DB_MYSQL_PASSWORD", "")
DB_MYSQL_DATABASE = os.environ.get("DB_MYSQL_DATABASE", "ipam")

DEFAULT_DB_CONFIG = {
    "host": DB_MYSQL_HOST,
    "port": DB_MYSQL_PORT,
    "user": DB_MYSQL_USER,
    "password": DB_MYSQL_PASSWORD,
    "database": DB_MYSQL_DATABASE,
}


def load_db_config() -> dict:
    """读取数据源配置（JSON 文件不存在时用环境变量默认值）"""
    try:
        if DB_CONFIG_FILE.exists():
            cfg = json.loads(DB_CONFIG_FILE.read_text(encoding="utf-8"))
            # 与默认值合并，保证字段齐全
            merged = dict(DEFAULT_DB_CONFIG)
            merged.update({k: v for k, v in cfg.items() if k in DEFAULT_DB_CONFIG})
            return merged
    except Exception:
        pass
    return dict(DEFAULT_DB_CONFIG)


def save_db_config(cfg: dict) -> dict:
    """保存数据源配置到 JSON 文件"""
    merged = dict(DEFAULT_DB_CONFIG)
    merged.update({k: v for k, v in (cfg or {}).items() if k in DEFAULT_DB_CONFIG})
    merged["port"] = int(merged["port"]) if merged.get("port") else 3306
    DB_CONFIG_FILE.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return merged


# ==================== Web 服务 ====================
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
