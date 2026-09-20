from typing import List, Optional, Dict, Any, Tuple
"""
交换机管理服务
"""
from typing import List, Optional, Dict
from datetime import datetime
from db import get_db
from db.models import Switch
from utils.logger import logger
from ssh import test_switch_connectivity, scan_switch_arp, SSHConnectionError


def add_switch(switch_data: Dict) -> tuple[bool, str]:
    """添加交换机"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        
        # 检查 IP+端口是否已存在
        existing = cursor.execute(
            "SELECT id FROM switches WHERE ip = ? AND port = ?",
            (switch_data['ip'], switch_data.get('port', 22))
        ).fetchone()
        if existing:
            return False, "该 IP+端口已存在"
        
        # 插入交换机
        cursor.execute(
            """
            INSERT INTO switches 
            (name, ip, port, username, password, vendor, location, notes) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                switch_data['name'],
                switch_data['ip'],
                switch_data.get('port', 22),
                switch_data['username'],
                switch_data['password'],  # TODO: 加密存储
                switch_data.get('vendor', 'H3C'),
                switch_data.get('location', ''),
                switch_data.get('notes', '')
            )
        )
        switch_id = cursor.lastrowid
        conn.commit()
        
        logger.info(f"交换机 {switch_data['name']} 添加成功 (ID: {switch_id})")
        return True, "添加成功"
    except Exception as e:
        logger.error(f"添加交换机失败: {e}")
        return False, f"操作失败: {e}"


def update_switch(switch_id: int, switch_data: Dict) -> tuple[bool, str]:
    """更新交换机"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        
        fields = []
        values = []
        for k, v in switch_data.items():
            if k != 'id':
                fields.append(f"{k} = ?")
                values.append(v)
        
        if fields:
            fields_str = ", ".join(fields)
            values.append(switch_id)
            cursor.execute(
                f"UPDATE switches SET {fields_str}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            conn.commit()
            logger.info(f"交换机 ID {switch_id} 更新成功")
            return True, "更新成功"
        return False, "无有效更新字段"
    except Exception as e:
        logger.error(f"更新交换机失败: {e}")
        return False, f"操作失败: {e}"


def delete_switch(switch_id: int) -> tuple[bool, str]:
    """删除交换机"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        
        # 检查是否有绑定记录
        bindings = cursor.execute(
            "SELECT COUNT(*) FROM ip_mac_bindings WHERE switch_id = ?",
            (switch_id,)
        ).fetchone()[0]
        if bindings > 0:
            return False, "存在绑定记录，请先删除或迁移绑定"
        
        cursor.execute("DELETE FROM switches WHERE id = ?", (switch_id,))
        conn.commit()
        
        logger.info(f"交换机 ID {switch_id} 删除成功")
        return True, "删除成功"
    except Exception as e:
        logger.error(f"删除交换机失败: {e}")
        return False, f"操作失败: {e}"


def get_switches(include_inactive: bool = False) -> List[Dict]:
    """获取交换机列表"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        query = "SELECT * FROM switches"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY created_at DESC"
        
        results = cursor.execute(query).fetchall()
        return [dict(r) for r in results]
    except Exception as e:
        logger.error(f"获取交换机列表失败: {e}")
        return []


def get_switch_by_id(switch_id: int) -> Optional[Dict]:
    """根据 ID 获取交换机"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        result = cursor.execute(
            "SELECT * FROM switches WHERE id = ?", (switch_id,)
        ).fetchone()
        return dict(result) if result else None
    except Exception as e:
        logger.error(f"获取交换机失败: {e}")
        return None


def test_switch_connection(switch_id: int) -> tuple[bool, str]:
    """测试交换机连通性"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        result = cursor.execute(
            "SELECT * FROM switches WHERE id = ?", (switch_id,)
        ).fetchone()
        
        if not result:
            return False, "交换机不存在"
        
        switch = Switch(
            id=result['id'],
            name=result['name'],
            ip=result['ip'],
            port=result['port'],
            username=result['username'],
            password=result['password'],  # 已加密，实际使用时需解密
            vendor=result['vendor'],
            location=result['location'],
            notes=result['notes'],
            is_active=result['is_active']
        )
        
        if test_switch_connectivity(switch):
            logger.info(f"交换机 {switch.name} 连通性测试成功")
            return True, "连接正常"
        else:
            logger.warning(f"交换机 {switch.name} 连通性测试失败")
            return False, "连接失败，请检查网络、用户名密码或交换机状态"
    except Exception as e:
        logger.error(f"测试交换机连通性异常: {e}")
        return False, f"测试异常: {e}"


def scan_switch(switch_id: int) -> tuple[bool, str, List[Dict]]:
    """扫描交换机 ARP 表并更新绑定"""
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        
        # 获取交换机信息
        switch_row = cursor.execute(
            "SELECT * FROM switches WHERE id = ?", (switch_id,)
        ).fetchone()
        if not switch_row:
            return False, "交换机不存在", []
        
        switch = Switch(
            id=switch_row['id'],
            name=switch_row['name'],
            ip=switch_row['ip'],
            port=switch_row['port'],
            username=switch_row['username'],
            password=switch_row['password'],  # 已加密，实际使用时需解密
            vendor=switch_row['vendor'],
            location=switch_row['location'],
            notes=switch_row['notes'],
            is_active=switch_row['is_active']
        )
        
        # 扫描 ARP 表
        bindings = scan_switch_arp(switch)
        
        # 更新交换机最后扫描时间
        cursor.execute(
            "UPDATE switches SET last_seen = CURRENT_TIMESTAMP WHERE id = ?",
            (switch_id,)
        )
        conn.commit()
        
        logger.info(f"交换机 {switch.name} 扫描完成，发现 {len(bindings)} 条记录")
        return True, f"扫描完成，发现 {len(bindings)} 条记录", [b.__dict__ for b in bindings]
    except Exception as e:
        logger.error(f"扫描交换机失败: {e}")
        return False, f"扫描失败: {e}", []


def update_binding_from_arp(bindings: List[Dict], switch_id: int) -> int:
    """从 ARP 扫描结果更新 IP-MAC 绑定"""
    if not bindings:
        return 0
    
    try:
        conn = get_db()
        cursor = conn.cursor() if conn.__class__.__name__ == 'Connection' else conn
        
        updated_count = 0
        for b in bindings:
            ip = b['ip'] if isinstance(b, dict) else b.ip_address
            mac = b['mac'] if isinstance(b, dict) else b.mac_address
            
            # 检查是否存在
            existing = cursor.execute(
                "SELECT id FROM ip_mac_bindings WHERE ip_address = ? AND switch_id = ?",
                (ip, switch_id)
            ).fetchone()
            
            if existing:
                # 更新已有记录
                cursor.execute(
                    """
                    UPDATE ip_mac_bindings 
                    SET mac_address = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                    """,
                    (mac, existing['id'])
                )
                updated_count += 1
            else:
                # 插入新记录
                cursor.execute(
                    """
                    INSERT INTO ip_mac_bindings 
                    (ip_address, mac_address, switch_id, first_seen, last_seen, created_at, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (ip, mac, switch_id)
                )
                updated_count += 1
        
        conn.commit()
        logger.info(f"更新了 {updated_count} 条 IP-MAC 绑定记录")
        return updated_count
    except Exception as e:
        logger.error(f"更新 IP-MAC 绑定失败: {e}")
        return 0