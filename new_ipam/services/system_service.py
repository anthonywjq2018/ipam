from typing import List, Optional, Dict, Any, Tuple
"""
系统管理服务 - 用户、权限、数据库配置、备份导入导出
"""
import json
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from db import get_db, close_db
from db.models import User, SystemConfig
from utils.logger import logger
from utils import backup_database as util_backup_db, restore_database as util_restore_db, clean_old_backups
from services.auth_service import (
    create_user as auth_create_user, 
    get_all_users as auth_get_all_users, 
    update_user as auth_update_user, 
    delete_user as auth_delete_user, 
    get_user_by_id as auth_get_user_by_id, 
    get_user_permissions as auth_get_user_permissions
)


def create_system_config(key: str, value: str) -> str:
    """创建系统配置"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        cursor.execute(
            "INSERT INTO system_config (config_key, config_value, description) VALUES (?, ?, ?)",
            (key, value, f"系统配置: {value}")
        )
        conn.commit()
        logger.info(f"系统配置 {key}={value} 已创建")
        return key
    except Exception as e:
        logger.error(f"创建系统配置失败: {e}")
        return None


def get_system_config(key: str) -> Optional[Dict]:
    """获取系统配置"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        result = cursor.execute(
            "SELECT * FROM system_config WHERE config_key = ?", (key,)
        ).fetchone()
        if result:
            return dict(result)
        return None
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        return None


def update_system_config(key: str, value: str) -> bool:
    """更新系统配置"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        cursor.execute(
            "UPDATE system_config SET config_value = ? WHERE config_key = ?",
            (value, key)
        )
        conn.commit()
        logger.info(f"系统配置 {key}={value} 已更新")
        return True
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}")
        return False


def delete_system_config(key: str) -> bool:
    """删除系统配置"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        cursor.execute("DELETE FROM system_config WHERE config_key = ?", (key,))
        conn.commit()
        logger.info(f"系统配置 {key} 已删除")
        return True
    except Exception as e:
        logger.error(f"删除系统配置失败: {e}")
        return False


def get_all_system_configs() -> List[Dict]:
    """获取所有系统配置"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        results = cursor.execute(
            "SELECT * FROM system_config ORDER BY config_key"
        ).fetchall()
        return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"获取系统配置列表失败: {e}")
        return []


# 代理 auth_service 函数（避免循环引用）
def create_user(username: str, password: str, display_name: str, role: str = "viewer", email: str = "") -> Optional[Dict]:
    return auth_create_user(username, password, display_name, role, email)


def get_all_users() -> List[Dict]:
    return auth_get_all_users()


def update_user(user_id: int, **kwargs) -> bool:
    return auth_update_user(user_id, **kwargs)


def delete_user(user_id: int) -> bool:
    return auth_delete_user(user_id)


def get_user_by_id(user_id: int) -> Optional[Dict]:
    return auth_get_user_by_id(user_id)


def get_user_permissions(user_id: int) -> List[str]:
    return auth_get_user_permissions(user_id)


def backup_database() -> Optional[Path]:
    """备份数据库"""
    return util_backup_db()


def restore_database(backup_path: Path) -> bool:
    """恢复数据库"""
    return util_restore_db(backup_path)


def cleanup_old_backups(retention_days: int = 30) -> int:
    """清理旧备份"""
    return clean_old_backups(retention_days)


def test_database_connection(db_config: Dict) -> tuple[bool, str]:
    """测试数据库连接"""
    try:
        db_type = db_config.get('type', 'sqlite')
        
        if db_type == 'mysql':
            import pymysql
            conn = pymysql.connect(
                host=db_config.get('host', 'localhost'),
                port=int(db_config.get('port', 3306)),
                user=db_config.get('user', 'root'),
                password=db_config.get('password', ''),
                database=db_config.get('name', 'ipam'),
                charset='utf8mb4',
                connect_timeout=5,
            )
            conn.close()
        else:
            # SQLite 测试
            from config import DB_PATH
            import sqlite3
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("SELECT 1")
            conn.close()
        
        return True, "连接成功"
    except Exception as e:
        return False, f"连接失败: {e}"


def export_all_data() -> Dict:
    """导出所有数据（用于迁移数据库）"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        
        tables = ['users', 'switches', 'ip_mac_bindings', 'scan_logs', 'system_config']
        data = {}
        
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            data[table] = [dict(r) for r in cursor.fetchall()]
        
        return {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'data': data
        }
    except Exception as e:
        logger.error(f"导出数据失败: {e}")
        return {}


def import_all_data(export_data: Dict) -> tuple[bool, str]:
    """导入所有数据（用于迁移数据库）"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        
        data = export_data.get('data', {})
        
        # 禁用外键约束（SQLite）
        if 'sqlite' in str(type(conn)).lower():
            cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # 按依赖顺序导入
        table_order = ['users', 'switches', 'ip_mac_bindings', 'scan_logs', 'system_config']
        
        for table in table_order:
            if table in data:
                cursor.execute(f"DELETE FROM {table}")
                rows = data[table]
                if rows:
                    columns = rows[0].keys()
                    placeholders = ','.join(['?'] * len(columns))
                    sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                    for row in rows:
                        cursor.execute(sql, [row[c] for c in columns])
        
        # 重置自增 ID
        if 'sqlite' in str(type(conn)).lower():
            cursor.execute("PRAGMA foreign_keys = ON;")
            for table in table_order:
                cursor.execute(f"SELECT MAX(id) FROM {table}")
                max_id = cursor.fetchone()[0]
                if max_id:
                    cursor.execute(f"UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (max_id, table))
        
        conn.commit()
        return True, "导入成功"
    except Exception as e:
        logger.error(f"导入数据失败: {e}")
        return False, f"导入失败: {e}"