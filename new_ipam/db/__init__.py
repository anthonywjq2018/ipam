"""
数据库层 - 统一 SQLite/MySQL 管理
"""
import logging
from contextlib import contextmanager
from config import DB_TYPE, DB_PATH, DB_MYSQL_HOST, DB_MYSQL_PORT, DB_MYSQL_USER, DB_MYSQL_PASSWORD, DB_MYSQL_DATABASE

logger = logging.getLogger(__name__)

_conn = None


def get_db():
    """获取数据库连接（上下文管理器用）"""
    global _conn
    if DB_TYPE == "mysql":
        import pymysql
        if _conn is None:
            _conn = pymysql.connect(
                host=DB_MYSQL_HOST, port=DB_MYSQL_PORT,
                user=DB_MYSQL_USER, password=DB_MYSQL_PASSWORD,
                database=DB_MYSQL_DATABASE, charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor, autocommit=False,
            )
        return _conn
    else:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn


def init_db():
    """初始化数据库表结构"""
    if DB_TYPE == "mysql":
        import pymysql
        conn = pymysql.connect(
            host=DB_MYSQL_HOST, port=DB_MYSQL_PORT,
            user=DB_MYSQL_USER, password=DB_MYSQL_PASSWORD,
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
        )
        conn.execute(f"CREATE DATABASE IF NOT EXISTS {DB_MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.close()
    
    conn = get_db()
    cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
    
    if DB_TYPE == "mysql":
        # MySQL version with ON UPDATE
        users_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            role VARCHAR(20) DEFAULT 'viewer',
            email VARCHAR(200) DEFAULT '',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        switches_sql = """
        CREATE TABLE IF NOT EXISTS switches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        """
        bindings_sql = """
        CREATE TABLE IF NOT EXISTS ip_mac_bindings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        """
        logs_sql = """
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            switch_id INTEGER,
            status VARCHAR(20) DEFAULT 'success',
            entries_found INTEGER DEFAULT 0,
            new_entries INTEGER DEFAULT 0,
            updated_entries INTEGER DEFAULT 0,
            duration_seconds REAL DEFAULT 0,
            error_message TEXT,
            scan_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        config_sql = """
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key VARCHAR(100) UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            description VARCHAR(200) DEFAULT '',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
    else:
        # SQLite version without ON UPDATE
        users_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            role VARCHAR(20) DEFAULT 'viewer',
            email VARCHAR(200) DEFAULT '',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        switches_sql = """
        CREATE TABLE IF NOT EXISTS switches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ip, port)
        )
        """
        bindings_sql = """
        CREATE TABLE IF NOT EXISTS ip_mac_bindings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ip_address, vlan, switch_id)
        )
        """
        logs_sql = """
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            switch_id INTEGER,
            status VARCHAR(20) DEFAULT 'success',
            entries_found INTEGER DEFAULT 0,
            new_entries INTEGER DEFAULT 0,
            updated_entries INTEGER DEFAULT 0,
            duration_seconds REAL DEFAULT 0,
            error_message TEXT,
            scan_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        config_sql = """
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key VARCHAR(100) UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            description VARCHAR(200) DEFAULT '',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    
    for stmt in [users_sql, switches_sql, bindings_sql, logs_sql, config_sql]:
        cursor.execute(stmt)
    
    conn.commit()
    
    if DB_TYPE == "mysql":
        conn.close()
    # SQLite connection is returned by get_db and will be closed by the caller or at end of request

def close_db(conn):
    """关闭数据库连接"""
    if DB_TYPE == "mysql" and conn:
        conn.close()
    # SQLite 不需要手动关闭
