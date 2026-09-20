"""
SSH 连接与 ARP 扫描服务
"""
import paramiko
import re
import time
from typing import List, Dict, Optional, Tuple
from config import SSH_TIMEOUT
from db import get_db
from db.models import Switch, IPBinding
from utils.logger import logger


class SSHConnectionError(Exception):
    """SSH 连接错误"""
    pass


class SSHClient:
    """SSH 客户端封装"""
    
    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.client = None
        
    def connect(self):
        """建立 SSH 连接"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=SSH_TIMEOUT,
                look_for_keys=False,
                allow_agent=False,
            )
            logger.info(f"已连接到 {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"SSH 连接失败: {e}")
            raise SSHConnectionError(f"SSH 连接失败: {e}")
    
    def execute(self, command: str) -> Tuple[str, str]:
        """执行命令并返回 (stdout, stderr)"""
        if not self.client:
            raise SSHConnectionError("未建立 SSH 连接")
            
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            stdout_text = stdout.read().decode('utf-8').strip()
            stderr_text = stderr.read().decode('utf-8').strip()
            return stdout_text, stderr_text
        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            raise SSHConnectionError(f"执行命令失败: {e}")
    
    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()
    
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def parse_arp_output(output: str, vendor: str) -> List[Dict]:
    """解析 ARP 表输出"""
    bindings = []
    
    # H3C/Huawei 格式
    h3c_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+(\w{12})(\s+\S+)?'
    if vendor in ['H3C', 'Huawei', 'H3C ComwareV7']:
        for match in re.finditer(h3c_pattern, output):
            ip = match.group(1)
            mac = match.group(2)
            # 处理可选的额外信息
            if match.group(3):
                # 可能包含 VLAN 或端口信息
                pass
            bindings.append({
                'ip': ip,
                'mac': mac,
                'vendor': vendor
            })
    
    # Cisco 格式
    elif vendor in ['Cisco', 'Cisco IOS']:
        for match in re.finditer(r'(\d+\.\d+\.\d+\.\d+)\s+(\w{12})', output):
            ip = match.group(1)
            mac = match.group(2)
            bindings.append({
                'ip': ip,
                'mac': mac,
                'vendor': vendor
            })
    
    # 锐捷等其他厂商
    else:
        # 简单匹配 IP 和 MAC
        lines = [line for line in output.split('\n') if 'ARP' in line and 'IP' in line]
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                ip = parts[0]
                mac = parts[1]
                bindings.append({
                    'ip': ip,
                    'mac': mac,
                    'vendor': vendor
                })
    
    return bindings


def scan_switch_arp(switch: Switch) -> List[IPBinding]:
    """扫描交换机 ARP 表并返回绑定列表"""
    try:
        with SSHClient(switch.ip, switch.username, switch.password, switch.port) as ssh:
            # 根据厂商选择不同的 ARP 命令
            if switch.vendor in ['H3C', 'Huawei']:
                command = "dis arp"
            elif switch.vendor in ['Cisco', 'Cisco IOS']:
                command = "show arp"
            else:
                # 通用方式，尝试几种常见命令
                command = "show arp"
            
            output, err = ssh.execute(command)
            if err:
                logger.warning(f"扫描 {switch.name} 失败: {err}")
                return []
            
            bindings_data = parse_arp_output(output, switch.vendor)
            return [IPBinding(**b) for b in bindings_data]
            
    except SSHConnectionError as e:
        logger.error(f"交换机 {switch.name} 扫描失败: {e}")
        return []
    except Exception as e:
        logger.error(f"扫描交换机 {switch.name} 时出错: {e}")
        return []


def test_switch_connectivity(switch: Switch) -> bool:
    """测试交换机 SSH 连通性"""
    try:
        with SSHClient(switch.ip, switch.username, switch.password, switch.port) as ssh:
            # 尝试执行简单命令
            stdout, err = ssh.execute("whoami")
            return err == ""
    except SSHConnectionError:
        return False
    except Exception as e:
        logger.error(f"连接测试失败: {e}")
        return False