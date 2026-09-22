"""
系统管理服务 - 用户、权限、数据源、备份导入导出（仅 MySQL）
"""
import json
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from db import get_db, close_db, check_datasource, test_datasource, init_database
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
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO system_config (config_key, config_value, description) VALUES (%s, %s, %s)",
            (key, value, f"系统配置: {value}")
        )
        conn.commit()
        logger.info(f"系统配置 {key} 已创建")
        return key
    except Exception as e:
        logger.error(f"创建系统配置失败: {e}")
        return None


def get_system_config(key: str) -> Optional[Dict]:
    """获取系统配置"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        result = cursor.execute(
            "SELECT * FROM system_config WHERE config_key = %s", (key,)
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
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE system_config SET config_value = %s WHERE config_key = %s",
            (value, key)
        )
        conn.commit()
        logger.info(f"系统配置 {key} 已更新")
        return True
    except Exception as e:
        logger.error(f"更新系统配置失败: {e}")
        return False


def delete_system_config(key: str) -> bool:
    """删除系统配置"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM system_config WHERE config_key = %s", (key,))
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
        cursor = conn.cursor()
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
    """备份数据库（导出全部数据为 JSON 快照）"""
    return util_backup_db()


def restore_database(backup_path: Path) -> bool:
    """恢复数据库（从 JSON 快照导入）"""
    return util_restore_db(backup_path)


def cleanup_old_backups(retention_days: int = 30) -> int:
    """清理旧备份"""
    return clean_old_backups(retention_days)


def test_database_connection(db_config: Dict) -> tuple:
    """测试数据库连接（仅 MySQL）"""
    return test_datasource(db_config)


def get_datasource_status() -> Dict:
    """获取数据源就绪状态"""
    return check_datasource()


def init_db_now() -> tuple:
    """初始化数据库（建库 + 建表 + 默认管理员）"""
    return init_database()


def export_all_data() -> Dict:
    """导出所有数据（用于迁移数据库）"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        tables = ['users', 'switches', 'ip_mac_bindings', 'scan_logs', 'system_config']
        data = {}
        
        for table in tables:
            cursor.execute(f"SELECT * FROM `{table}`")
            data[table] = [dict(r) for r in cursor.fetchall()]
        
        return {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'data': data
        }
    except Exception as e:
        logger.error(f"导出数据失败: {e}")
        return {}


def import_all_data(export_data: Dict) -> tuple:
    """导入所有数据（用于迁移数据库）"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        data = export_data.get('data', {})
        
        # 按依赖顺序导入（先删后插）
        table_order = ['users', 'switches', 'ip_mac_bindings', 'scan_logs', 'system_config']
        
        for table in table_order:
            if table in data:
                cursor.execute(f"DELETE FROM `{table}`")
                rows = data[table]
                if rows:
                    columns = list(rows[0].keys())
                    placeholders = ','.join(['%s'] * len(columns))
                    col_list = ','.join(f"`{c}`" for c in columns)
                    sql = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"
                    for row in rows:
                        cursor.execute(sql, [row[c] for c in columns])
        
        conn.commit()
        return True, "导入成功"
    except Exception as e:
        logger.error(f"导入数据失败: {e}")
        return False, f"导入失败: {e}"
