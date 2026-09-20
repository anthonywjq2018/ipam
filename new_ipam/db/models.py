"""
数据模型 - 领域对象定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    display_name: str
    role: str = "viewer"
    email: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Switch:
    id: int
    name: str
    ip: str
    port: int = 22
    username: str = ""
    password_hash: str = ""
    vendor: str = "H3C"
    location: str = ""
    notes: str = ""
    last_seen: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class IPBinding:
    id: int
    ip_address: str
    mac_address: str
    vlan: int = 1
    switch_id: Optional[int] = None
    person_name: str = ""
    phone: str = ""
    office: str = ""
    department: str = ""
    room_number: str = ""
    terminal_type: str = ""
    os_info: str = ""
    device_name: str = ""
    status: str = "active"
    notes: str = ""
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ScanLog:
    id: int
    switch_id: Optional[int]
    status: str
    entries_found: int = 0
    new_entries: int = 0
    updated_entries: int = 0
    duration_seconds: float = 0
    error_message: str = ""
    scan_time: Optional[datetime] = None


@dataclass
class SystemConfig:
    config_key: str
    config_value: str
    description: str = ""
    updated_at: Optional[datetime] = None
