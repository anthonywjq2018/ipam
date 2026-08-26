"""
SSH 模块 - 连接交换机并解析 ARP 表
支持 H3C / Huawei / Cisco 等常见厂商命令格式
"""
import re
import paramiko


def connect_switch(ip, username, password, port=22, timeout=10):
    """SSH 登录交换机，返回 ssh client"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, port=port, username=username, password=password,
                   timeout=timeout, allow_agent=False, look_for_keys=False)
    return client


def run_command(client, command, timeout=30):
    """执行命令并返回输出"""
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    return output, error


def disconnect_switch(client):
    """关闭 SSH 连接"""
    if client:
        try:
            client.close()
        except Exception:
            pass


# ==================== ARP 解析器 ====================

def parse_h3c_arp(output):
    """
    解析 H3C/Huawei 风格的 dis arp 输出
    
    典型格式:
    IP Address      MAC Address     VLAN    Interface         Aging
    192.168.1.1     000f-e2xx-xxxx  1       GE1/0/1           20
    """
    entries = []
    lines = output.strip().split('\n')
    
    # 跳过标题行和空行，找数据行
    for line in lines:
        line = line.strip()
        if not line or line.startswith('IP Address') or line.startswith('-') or \
           line.startswith('Type') or 'ARP' in line.upper() and 'Address' in line:
            continue
        
        # 尝试多种分隔方式（空格/tab/多空格）
        parts = re.split(r'\s{2,}|\t+', line)
        if len(parts) >= 4:
            ip = parts[0].strip()
            mac = parts[1].strip()
            vlan = parts[2].strip() if len(parts) > 2 else ''
            interface = parts[3].strip() if len(parts) > 3 else ''
            
            if _is_valid_ip(ip) and _is_valid_mac(mac):
                entries.append({
                    'ip': ip,
                    'mac': mac.upper(),
                    'vlan': vlan,
                    'interface': interface,
                    'port': '',  # 可通过 LLDP 进一步获取
                })
    
    return entries


def parse_cisco_arp(output):
    """
    解析 Cisco 风格的 show arp 输出
    
    典型格式:
    Protocol  Address      Age (min)  Hardware Addr   Type   Interface
    Internet  192.168.1.1     -       000f.e2xx.xxxx  ARPA   Vlan10
    """
    entries = []
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line or 'Protocol' in line or '---' in line:
            continue
        parts = re.split(r'\s{2,}|\t+', line)
        if len(parts) >= 5:
            ip = parts[1].strip()
            mac = parts[3].strip()
            interface = parts[5].strip() if len(parts) > 5 else ''
            vlan_match = re.search(r'Vlan(\d+)', interface)
            vlan = vlan_match.group(1) if vlan_match else ''
            if _is_valid_ip(ip) and _is_valid_mac(mac):
                entries.append({
                    'ip': ip,
                    'mac': mac.upper(),
                    'vlan': vlan,
                    'interface': interface,
                    'port': '',
                })
    return entries


def parse_generic_arp(output):
    """
    通用 ARP 解析 - 尝试从任意格式中提取 IP-MAC 对
    """
    entries = []
    ip_mac_pattern = re.compile(
        r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+'
        r'([0-9a-fA-F]{4}[\.\-][0-9a-fA-F]{4}[\.\-][0-9a-fA-F]{4})'
    )
    for line in output.split('\n'):
        matches = ip_mac_pattern.findall(line)
        for ip, mac in matches:
            if _is_valid_ip(ip) and _is_valid_mac(mac):
                entries.append({
                    'ip': ip,
                    'mac': mac.upper(),
                    'vlan': '',
                    'interface': '',
                    'port': '',
                })
    return entries


def parse_arp_output(output, vendor='H3C'):
    """根据厂商选择解析器"""
    if vendor.upper() in ('H3C', 'HUAWEI', 'HP', 'HPE'):
        entries = parse_h3c_arp(output)
    elif vendor.upper() in ('CISCO', 'CISCO IOS'):
        entries = parse_cisco_arp(output)
    else:
        entries = parse_generic_arp(output)
    
    # 如果专用解析器没结果，用通用解析器兜底
    if not entries:
        entries = parse_generic_arp(output)
    
    # 去重（按 IP+MAC）
    seen = set()
    unique = []
    for e in entries:
        key = (e['ip'], e['mac'])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    
    return unique


def _is_valid_ip(ip):
    """校验 IP 地址格式"""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def _is_valid_mac(mac):
    """校验 MAC 地址格式"""
    clean = mac.replace('-', '').replace(':', '').replace('.', '')
    return len(clean) == 12 and all(c in '0123456789abcdefABCDEF' for c in clean)


# ==================== 一键扫描 ====================

def scan_switch(switch_config, vendor='H3C'):
    """
    完整扫描流程：连接 → 执行 dis arp → 解析 → 返回结果
    
    switch_config: dict with keys: ip, port, username, password
    vendor: H3C / Cisco / Huawei
    
    返回: (entries_list, raw_output, error_message)
    """
    client = None
    try:
        client = connect_switch(
            ip=switch_config['ip'],
            username=switch_config['username'],
            password=switch_config['password'],
            port=switch_config.get('port', 22),
        )
        
        # 根据厂商选择命令
        if vendor.upper() in ('CISCO',):
            cmd = 'show arp'
        else:
            cmd = 'dis arp'
        
        output, error = run_command(client, cmd)
        
        if not output.strip() and error.strip():
            return [], '', f"命令执行失败: {error}"
        
        entries = parse_arp_output(output, vendor)
        return entries, output, None
        
    except paramiko.AuthenticationException:
        return [], '', "SSH 认证失败，请检查用户名和密码"
    except paramiko.SSHException as e:
        return [], '', f"SSH 连接错误: {str(e)}"
    except Exception as e:
        return [], '', f"扫描失败: {str(e)}"
    finally:
        disconnect_switch(client)
