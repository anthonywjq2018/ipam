from typing import List, Optional, Dict, Any
"""
认证与授权服务
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from db import get_db, close_db
from db.models import User
from utils import hash_password as util_hash_password, verify_password as util_verify_password
from utils.logger import logger


def hash_password(password: str) -> str:
    return util_hash_password(password)


def verify_password(password: str, password_hash: str) -> bool:
    return util_verify_password(password, password_hash)


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """验证用户登录"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        result = cursor.execute(
            "SELECT * FROM users WHERE username = %s AND is_active = 1",
            (username,)
        ).fetchone()
        
        if result and verify_password(password, result['password_hash']):
            logger.info(f"用户 {username} 登录成功")
            return dict(result)
        return None
    except Exception as e:
        logger.error(f"用户认证失败: {e}")
        return None


def create_user(username: str, password: str, display_name: str, 
                role: str = "viewer", email: str = "") -> Optional[User]:
    """创建新用户"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        existing = cursor.execute(
            "SELECT id FROM users WHERE username = %s", (username,)
        ).fetchone()
        if existing:
            logger.warning(f"用户名 {username} 已存在")
            return None
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, display_name, role, email) VALUES (%s, %s, %s, %s, %s)",
            (username, hash_password(password), display_name, role, email)
        )
        conn.commit()
        
        user_id = cursor.lastrowid
        logger.info(f"创建用户 {username} 成功")
        return User(id=user_id, username=username, password_hash=hash_password(password),
                    display_name=display_name, role=role, email=email)
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        return None


def get_all_users() -> List[Dict]:
    """获取所有用户"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        results = cursor.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return []


def update_user(user_id: int, **kwargs) -> bool:
    """更新用户信息"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if 'password' in kwargs:
            kwargs['password_hash'] = hash_password(kwargs.pop('password'))
        
        fields = ", ".join([f"{k} = %s" for k in kwargs])
        kwargs['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        kwargs['user_id'] = user_id
        
        cursor.execute(
            f"UPDATE users SET {fields}, updated_at = %s WHERE id = %s",
            (kwargs['updated_at'], user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        return False


def delete_user(user_id: int) -> bool:
    """删除用户"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        return False


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """根据 ID 获取用户"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        result = cursor.execute(
            "SELECT * FROM users WHERE id = %s", (user_id,)
        ).fetchone()
        return dict(result) if result else None
    except Exception as e:
        logger.error(f"获取用户失败: {e}")
        return None


def get_user_permissions(user_id: int) -> List[str]:
    """获取用户权限列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        result = cursor.execute(
            "SELECT role FROM users WHERE id = %s", (user_id,)
        ).fetchone()
        if result:
            role = result['role']
            if role == 'admin':
                return ['user:read', 'user:write', 'user:delete', 'switch:read', 'switch:write', 
                        'binding:read', 'binding:write', 'binding:delete', 'system:read', 'system:write',
                        'scan:execute', 'backup:execute']
            elif role == 'operator':
                return ['switch:read', 'switch:write', 'binding:read', 'binding:write', 
                        'scan:execute', 'backup:execute']
            else:
                return ['switch:read', 'binding:read']
        return []
    except Exception as e:
        logger.error(f"获取权限失败: {e}")
        return []


def has_permission(user_id: int, permission: str) -> bool:
    """检查用户是否有某权限"""
    return permission in get_user_permissions(user_id)