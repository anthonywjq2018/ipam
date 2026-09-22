from typing import List, Optional, Tuple, Dict, Any
"""
工具模块
"""
import hashlib
import json
import os
import re
import ipaddress
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    return hash_password(password) == password_hash


def generate_token(length: int = 32) -> str:
    """生成随机 token"""
    return os.urandom(length).hex()


def is_valid_ip(ip: str) -> bool:
    """验证 IP 地址格式"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_mac(mac: str) -> bool:
    """验证 MAC 地址格式"""
    return bool(re.match(r'^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$', mac))


def calculate_ip_range(ip: str, subnet_mask: str = "255.255.255.0") -> int:
    """计算子网内可用 IP 数量"""
    try:
        network = ipaddress.ip_network(f"{ip}/{subnet_mask}", strict=False)
        return network.num_addresses - 2  # 排除网络地址和广播地址
    except ValueError:
        return 0


def get_ip_octets(ip: str) -> List[int]:
    """获取 IP 的 4 个字节"""
    parts = ip.split('.')
    return [int(p) for p in parts if p.isdigit()]


def ip_to_int(ip: str) -> int:
    """IP 地址转整数"""
    return int(ipaddress.ip_address(ip))


def int_to_ip(num: int) -> str:
    """整数转 IP 地址"""
    return str(ipaddress.ip_address(num))


def get_subnet_range(ip: str, mask: str = "255.255.255.0") -> Tuple[int, int]:
    """获取子网范围"""
    network = ipaddress.ip_network(f"{ip}/{mask}", strict=False)
    return int(network.network_address), int(network.broadcast_address)


def format_datetime(dt: Optional[datetime]) -> str:
    """格式化时间"""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(dt: Optional[datetime]) -> str:
    """格式化日期"""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d")


def time_ago(dt: datetime) -> str:
    """计算时间差"""
    delta = datetime.now() - dt
    if delta.days > 0:
        return f"{delta.days}天前"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours}小时前"
    minutes = delta.seconds // 60
    if minutes > 0:
        return f"{minutes}分钟前"
    return "刚刚"


def sanitize_filename(filename: str) -> str:
    """清理文件名"""
    return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)


def ensure_dir(path: Path):
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)


def get_db_size() -> int:
    """获取数据库大小（字节，MySQL 无文件概念，返回 0）"""
    return 0


def export_to_csv(bindings: List[Dict], filepath: Path) -> bool:
    """导出数据到 CSV"""
    import csv
    try:
        ensure_dir(filepath.parent)
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'ip_address', 'mac_address', 'vlan', 'person_name',
                'phone', 'office', 'department', 'room_number',
                'terminal_type', 'os_info', 'device_name', 'status', 'notes'
            ])
            writer.writeheader()
            writer.writerows(bindings)
        return True
    except Exception as e:
        logger.error(f"导出 CSV 失败: {e}")
        return False


def import_from_csv(filepath: Path) -> List[Dict]:
    """从 CSV 导入数据"""
    import csv
    bindings = []
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                bindings.append(row)
        return bindings
    except Exception as e:
        logger.error(f"导入 CSV 失败: {e}")
        return []


def backup_database() -> Path:
    """备份数据库：导出全部业务数据为 JSON 快照"""
    from config import BACKUP_DIR
    ensure_dir(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"ipam_backup_{timestamp}.json"
    try:
        from services.system_service import export_all_data
        data = export_all_data()
        backup_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    except Exception as e:
        logger.error(f"备份数据库失败: {e}")
    return backup_path


def restore_database(backup_path: Path) -> bool:
    """恢复数据库：从 JSON 快照导入"""
    try:
        if not backup_path.exists():
            return False
        from services.system_service import import_all_data
        data = json.loads(backup_path.read_text(encoding="utf-8"))
        ok, msg = import_all_data(data)
        if not ok:
            logger.error(f"恢复数据库失败: {msg}")
        return ok
    except Exception as e:
        logger.error(f"恢复数据库失败: {e}")
        return False


def clean_old_backups(retention_days: int = 30):
    """清理旧备份"""
    from config import BACKUP_DIR
    cutoff = datetime.now() - timedelta(days=retention_days)
    for f in BACKUP_DIR.glob("*.json"):
        if f.stat().st_mtime < cutoff.timestamp():
            f.unlink()
            logger.info(f"清理旧备份: {f.name}")


def get_terminal_types() -> List[str]:
    """获取终端类型列表"""
    return [
        "PC", "笔记本", "手机", "打印机", "摄像头",
        "服务器", "IoT", "交换机", "路由器", "其他"
    ]


def get_status_types() -> List[str]:
    """获取状态类型列表"""
    return ["active", "inactive", "reserved"]


def get_vendors() -> List[str]:
    """获取交换机厂商列表"""
    return ["H3C", "Huawei", "Cisco", "锐捷", "中兴", "其他"]


def get_default_fields() -> List[str]:
    """获取默认字段列表"""
    return [
        "ip_address", "mac_address", "vlan", "person_name",
        "phone", "office", "department", "room_number",
        "terminal_type", "os_info", "device_name", "status", "notes"
    ]