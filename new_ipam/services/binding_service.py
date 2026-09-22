from typing import List, Optional, Dict, Any, Tuple
"""
IP-MAC 绑定管理服务
"""
from typing import List, Optional, Dict
from datetime import datetime
from db import get_db
from db.models import IPBinding
from utils.logger import logger


def get_bindings(page: int = 1, per_page: int = 50, search: str = "", 
                 switch_id: int = None, status: str = "", vlan: int = None) -> tuple[List[Dict], int]:
    """获取 IP-MAC 绑定列表（支持筛选）"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if search:
            conditions.append("(ip_address LIKE %s OR mac_address LIKE %s OR person_name LIKE %s OR phone LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])
        if switch_id:
            conditions.append("switch_id = %s")
            params.append(switch_id)
        if status:
            conditions.append("status = %s")
            params.append(status)
        if vlan:
            conditions.append("vlan = %s")
            params.append(vlan)
        
        where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 总数
        total = cursor.execute(
            "SELECT COUNT(*) AS cnt FROM ip_mac_bindings" + where_sql,
            params
        ).fetchone()["cnt"]
        
        # 列表
        offset = (page - 1) * per_page
        query = (
            "SELECT b.*, s.name AS switch_name "
            "FROM ip_mac_bindings b "
            "LEFT JOIN switches s ON b.switch_id = s.id"
            + where_sql + 
            " ORDER BY b.last_seen DESC LIMIT %s OFFSET %s"
        )
        query_params = params + [per_page, offset]
        
        results = cursor.execute(query, query_params).fetchall()
        return [dict(r) for r in results], total
    except Exception as e:
        logger.error(f"获取绑定列表失败: {e}")
        return [], 0


def get_binding_by_id(binding_id: int) -> Optional[Dict]:
    """根据 ID 获取绑定"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        result = cursor.execute(
            "SELECT * FROM ip_mac_bindings WHERE id = %s", (binding_id,)
        ).fetchone()
        return dict(result) if result else None
    except Exception as e:
        logger.error(f"获取绑定失败: {e}")
        return None


def get_bindings_by_switch(switch_id: int) -> List[Dict]:
    """获取指定交换机的绑定列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        results = cursor.execute(
            "SELECT * FROM ip_mac_bindings WHERE switch_id = %s ORDER BY ip_address",
            (switch_id,)
        ).fetchall()
        return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"获取交换机绑定失败: {e}")
        return []


def add_binding(binding_data: Dict) -> tuple[bool, str]:
    """添加绑定"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查重复
        existing = cursor.execute(
            "SELECT id FROM ip_mac_bindings WHERE ip_address = %s AND switch_id = %s",
            (binding_data['ip_address'], binding_data.get('switch_id'))
        ).fetchone()
        if existing:
            return False, "该 IP 已存在绑定记录"
        
        cursor.execute(
            """
            INSERT INTO ip_mac_bindings 
            (ip_address, mac_address, vlan, switch_id, person_name, phone, office,
             department, room_number, terminal_type, os_info, device_name,
             status, notes, first_seen, last_seen, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                binding_data['ip_address'],
                binding_data.get('mac_address', ''),
                binding_data.get('vlan', 1),
                binding_data.get('switch_id'),
                binding_data.get('person_name', ''),
                binding_data.get('phone', ''),
                binding_data.get('office', ''),
                binding_data.get('department', ''),
                binding_data.get('room_number', ''),
                binding_data.get('terminal_type', ''),
                binding_data.get('os_info', ''),
                binding_data.get('device_name', ''),
                binding_data.get('status', 'active'),
                binding_data.get('notes', '')
            )
        )
        conn.commit()
        logger.info(f"绑定 {binding_data['ip_address']} 添加成功")
        return True, "添加成功"
    except Exception as e:
        logger.error(f"添加绑定失败: {e}")
        return False, f"操作失败: {e}"


def update_binding(binding_id: int, binding_data: Dict) -> tuple[bool, str]:
    """更新绑定"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        fields = []
        values = []
        for k, v in binding_data.items():
            if k != 'id':
                fields.append(f"{k} = %s")
                values.append(v)
        
        if fields:
            values.append(binding_id)
            cursor.execute(
                f"UPDATE ip_mac_bindings SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                values
            )
            conn.commit()
            logger.info(f"绑定 ID {binding_id} 更新成功")
            return True, "更新成功"
        return False, "无有效更新字段"
    except Exception as e:
        logger.error(f"更新绑定失败: {e}")
        return False, f"操作失败: {e}"


def delete_binding(binding_id: int) -> tuple[bool, str]:
    """删除绑定"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ip_mac_bindings WHERE id = %s", (binding_id,))
        conn.commit()
        logger.info(f"绑定 ID {binding_id} 删除成功")
        return True, "删除成功"
    except Exception as e:
        logger.error(f"删除绑定失败: {e}")
        return False, f"操作失败: {e}"


def delete_bindings_by_switch(switch_id: int) -> int:
    """删除指定交换机下的所有绑定"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ip_mac_bindings WHERE switch_id = %s", (switch_id,))
        conn.commit()
        count = cursor.rowcount
        logger.info(f"已删除交换机 {switch_id} 下的 {count} 条绑定")
        return count
    except Exception as e:
        logger.error(f"批量删除绑定失败: {e}")
        return 0


def get_bindings_by_vlan(switch_id: int, vlan: int) -> List[Dict]:
    """获取指定交换机和 VLAN 下的绑定"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        results = cursor.execute(
            """
            SELECT * FROM ip_mac_bindings 
            WHERE switch_id = %s AND vlan = %s 
            ORDER BY ip_address
            """,
            (switch_id, vlan)
        ).fetchall()
        return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"获取 VLAN 绑定失败: {e}")
        return []


def get_vlans_by_switch(switch_id: int) -> List[int]:
    """获取指定交换机下的 VLAN 列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        results = cursor.execute(
            "SELECT DISTINCT vlan FROM ip_mac_bindings WHERE switch_id = %s ORDER BY vlan",
            (switch_id,)
        ).fetchall()
        return [r['vlan'] for r in results]
    except Exception as e:
        logger.error(f"获取 VLAN 列表失败: {e}")
        return []


def get_binding_summary(switch_id: int = None) -> Dict:
    """获取绑定统计信息"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if switch_id:
            total = cursor.execute(
                "SELECT COUNT(*) AS cnt FROM ip_mac_bindings WHERE switch_id = %s",
                (switch_id,)
            ).fetchone()["cnt"]
            active = cursor.execute(
                "SELECT COUNT(*) AS cnt FROM ip_mac_bindings WHERE switch_id = %s AND status = 'active'",
                (switch_id,)
            ).fetchone()["cnt"]
            inactive = cursor.execute(
                "SELECT COUNT(*) AS cnt FROM ip_mac_bindings WHERE switch_id = %s AND status = 'inactive'",
                (switch_id,)
            ).fetchone()["cnt"]
        else:
            total = cursor.execute("SELECT COUNT(*) AS cnt FROM ip_mac_bindings").fetchone()["cnt"]
            active = cursor.execute(
                "SELECT COUNT(*) AS cnt FROM ip_mac_bindings WHERE status = 'active'"
            ).fetchone()["cnt"]
            inactive = cursor.execute(
                "SELECT COUNT(*) AS cnt FROM ip_mac_bindings WHERE status = 'inactive'"
            ).fetchone()["cnt"]
        
        return {
            'total': total,
            'active': active,
            'inactive': inactive,
            'unknown': max(0, total - active - inactive)
        }
    except Exception as e:
        logger.error(f"获取绑定统计失败: {e}")
        return {'total': 0, 'active': 0, 'inactive': 0, 'unknown': 0}


def get_bindings_export() -> List[Dict]:
    """获取导出格式的绑定列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        results = cursor.execute(
            """
            SELECT b.*, s.name AS switch_name 
            FROM ip_mac_bindings b 
            LEFT JOIN switches s ON b.switch_id = s.id
            ORDER BY b.ip_address
            """
        ).fetchall()
        return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"获取导出列表失败: {e}")
        return []


def get_bindings_import() -> List[Dict]:
    """获取导入格式的绑定列表（与 get_bindings_export 相同）"""
    return get_bindings_export()