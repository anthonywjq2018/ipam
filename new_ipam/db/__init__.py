"""
数据库层 - 仅 MySQL
==================
使用前必须：
1. 在系统配置页面配置数据源（host/port/user/password/database）
2. 执行"初始化数据库"创建库与表
未完成前，业务接口将返回"数据源未就绪"。
"""
import json
import logging
import threading
from contextlib import contextmanager

import pymysql

from config import load_db_config, save_db_config

logger = logging.getLogger(__name__)

# 业务表清单（初始化与就绪检查使用）
REQUIRED_TABLES = ["users", "switches", "ip_mac_bindings", "scan_logs", "system_config"]

# 线程本地连接缓存：每个线程一个连接，配置变更后自动重建
_local = threading.local()


def _connect(database: str = None, cfg: dict = None):
    """建立 MySQL 连接（database=None 时不选择库，用于建库/检查）"""
    cfg = cfg or load_db_config()
    return pymysql.connect(
        host=cfg.get("host", "localhost"),
        port=int(cfg.get("port", 3306)),
        user=cfg.get("user", "root"),
        password=cfg.get("password", ""),
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=5,
    )


def get_db():
    """获取当前线程的 MySQL 连接（配置变更自动重建）"""
    cfg = load_db_config()
    key = (cfg.get("host"), cfg.get("port"), cfg.get("user"), cfg.get("database"))
    conn = getattr(_local, "conn", None)
    if conn is not None and getattr(_local, "key", None) == key:
        try:
            conn.ping(reconnect=True)
            return conn
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
    conn = _connect(cfg["database"], cfg)
    _local.conn = conn
    _local.key = key
    return conn


@contextmanager
def db_cursor(commit: bool = False):
    """便捷游标上下文：自动 commit/rollback"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def close_db(conn=None):
    """关闭连接（保持兼容，实际由线程本地管理）"""
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


# ==================== 建表语句（MySQL）====================

_TABLES_SQL = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            role VARCHAR(20) DEFAULT 'viewer',
            email VARCHAR(200) DEFAULT '',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """,
    "switches": """
        CREATE TABLE IF NOT EXISTS switches (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            ip VARCHAR(45) NOT NULL,
            port INTEGER DEFAULT 22,
            username VARCHAR(100) NOT NULL,
            password VARCHAR(255) NOT NULL,
            vendor VARCHAR(50) DEFAULT 'H3C',
            location VARCHAR(200) DEFAULT '',
            notes TEXT,
            last_seen DATETIME DEFAULT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE(ip, port)
        )
    """,
    "ip_mac_bindings": """
        CREATE TABLE IF NOT EXISTS ip_mac_bindings (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            ip_address VARCHAR(45) NOT NULL,
            mac_address VARCHAR(17) NOT NULL,
            vlan INTEGER DEFAULT 1,
            switch_id INTEGER DEFAULT NULL,
            person_name VARCHAR(100) DEFAULT '',
            phone VARCHAR(20) DEFAULT '',
            office VARCHAR(100) DEFAULT '',
            department VARCHAR(100) DEFAULT '',
            room_number VARCHAR(20) DEFAULT '',
            terminal_type VARCHAR(50) DEFAULT '',
            os_info VARCHAR(100) DEFAULT '',
            device_name VARCHAR(100) DEFAULT '',
            status VARCHAR(20) DEFAULT 'active',
            notes TEXT,
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE(ip_address, vlan, switch_id)
        )
    """,
    "scan_logs": """
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            switch_id INTEGER,
            status VARCHAR(20) DEFAULT 'success',
            entries_found INTEGER DEFAULT 0,
            new_entries INTEGER DEFAULT 0,
            updated_entries INTEGER DEFAULT 0,
            duration_seconds REAL DEFAULT 0,
            error_message TEXT,
            scan_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "system_config": """
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            config_key VARCHAR(100) UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            description VARCHAR(200) DEFAULT '',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """,
}


# ==================== 数据源状态 ====================

def check_datasource() -> dict:
    """检查数据源就绪状态（不抛异常）

    返回:
      configured      配置文件存在且关键字段已填写
      connected       MySQL 服务可连接
      database_created 目标库已创建
      tables_created  业务表已创建
      ready           全部就绪
    """
    cfg = load_db_config()
    configured = bool(cfg.get("host") and cfg.get("user") and cfg.get("database"))
    status = {
        "configured": configured,
        "connected": False,
        "database_created": False,
        "tables_created": False,
        "ready": False,
        "message": "",
    }
    if not configured:
        status["message"] = "数据源未配置"
        return status

    # 1) 服务连通性（不选库）
    try:
        conn = _connect(None, cfg)
        status["connected"] = True
        conn.close()
    except Exception as e:
        status["message"] = f"MySQL 连接失败: {e}"
        return status

    # 2) 库是否存在
    try:
        conn = _connect(None, cfg)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                (cfg["database"],),
            )
            status["database_created"] = cur.fetchone() is not None
        conn.close()
    except Exception as e:
        status["message"] = f"查询数据库失败: {e}"
        return status

    if not status["database_created"]:
        status["message"] = "数据库尚未创建，请执行初始化"
        return status

    # 3) 表是否齐全
    try:
        conn = _connect(cfg["database"], cfg)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS cnt FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN (%s)
                """ % ("%s", ",".join(["%s"] * len(REQUIRED_TABLES))),
                [cfg["database"]] + REQUIRED_TABLES,
            )
            status["tables_created"] = (cur.fetchone()["cnt"] == len(REQUIRED_TABLES))
        conn.close()
    except Exception as e:
        status["message"] = f"查询表失败: {e}"
        return status

    if not status["tables_created"]:
        status["message"] = "业务表尚未创建，请执行初始化"
        return status

    status["ready"] = True
    status["message"] = "数据源就绪"
    return status


def is_db_ready() -> bool:
    """业务接口前置检查：数据源是否就绪"""
    return check_datasource()["ready"]


def test_datasource(cfg: dict) -> tuple:
    """测试给定配置能否连接 MySQL（不保存）"""
    try:
        conn = _connect(None, cfg)
        conn.close()
        return True, "MySQL 连接成功"
    except Exception as e:
        return False, f"连接失败: {e}"


def init_database() -> tuple:
    """初始化数据库：建库 + 建表 + 注册默认管理员

    Returns: (ok, message)
    """
    cfg = load_db_config()
    if not (cfg.get("host") and cfg.get("user") and cfg.get("database")):
        return False, "数据源未配置，请先保存配置"

    # 建库
    try:
        conn = _connect(None, cfg)
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        conn.close()
    except Exception as e:
        return False, f"创建数据库失败: {e}"

    # 建表
    try:
        conn = _connect(cfg["database"], cfg)
        with conn.cursor() as cur:
            for name, sql in _TABLES_SQL.items():
                cur.execute(sql)
        conn.commit()
        conn.close()
    except Exception as e:
        return False, f"创建表失败: {e}"

    # 注册默认管理员
    try:
        from services.auth_service import hash_password
        conn = _connect(cfg["database"], cfg)
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", ("admin",))
            if cur.fetchone() is None:
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, display_name, role, email, is_active)
                    VALUES (%s, %s, %s, %s, %s, 1)
                    """,
                    ("admin", hash_password("Admin@123"), "系统管理员", "admin", "admin@ipam.local"),
                )
                conn.commit()
                logger.info("默认管理员 admin/Admin@123 已创建")
        conn.close()
    except Exception as e:
        return False, f"注册默认管理员失败: {e}"

    # 清除线程本地连接缓存，让后续请求用新库重建
    conn = getattr(_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None

    return True, "数据库初始化成功，默认管理员 admin/Admin@123"


# 兼容旧引用
def init_db():
    """兼容入口：未初始化时不自动建表，由系统配置页面手动触发"""
    status = check_datasource()
    if not status["ready"]:
        logger.warning("数据源未就绪，请在系统配置页面完成初始化")
        return
    # 就绪则保证表存在
    init_database()
