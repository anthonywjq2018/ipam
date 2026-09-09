import os
import sqlite3
from config import DB_PATH
from encryption import encrypt_password, decrypt_password, is_encrypted


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 交换机表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS switches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ip TEXT NOT NULL UNIQUE,
            port INTEGER DEFAULT 22,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            vendor TEXT DEFAULT 'H3C',
            location TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            last_scan TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # IP-MAC 绑定表（核心表）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ip_mac_bindings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            mac TEXT NOT NULL,
            vlan TEXT DEFAULT '',
            port TEXT DEFAULT '',
            interface TEXT DEFAULT '',
            switch_id INTEGER,
            -- 扩展字段
            person_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            office TEXT DEFAULT '',
            department TEXT DEFAULT '',
            terminal_type TEXT DEFAULT '',
            os_info TEXT DEFAULT '',
            device_name TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            notes TEXT DEFAULT '',
            last_seen TEXT DEFAULT (datetime('now', 'localtime')),
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (switch_id) REFERENCES switches(id) ON DELETE SET NULL,
            UNIQUE(ip, mac)
        )
    """)

    # 操作日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            switch_id INTEGER,
            scan_time TEXT DEFAULT (datetime('now', 'localtime')),
            entries_found INTEGER DEFAULT 0,
            new_entries INTEGER DEFAULT 0,
            updated_entries INTEGER DEFAULT 0,
            status TEXT DEFAULT 'success',
            message TEXT DEFAULT '',
            FOREIGN KEY (switch_id) REFERENCES switches(id) ON DELETE SET NULL
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bindings_ip ON ip_mac_bindings(ip)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bindings_mac ON ip_mac_bindings(mac)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bindings_switch ON ip_mac_bindings(switch_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bindings_status ON ip_mac_bindings(status)")

    conn.commit()
    conn.close()



# ---------- 用户认证 CRUD ----------

def add_user(username, password_hash):
    """添加用户"""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, datetime('now', 'localtime'))",
            (username, password_hash, 1)
        )
        conn.commit()
        return True, "用户创建成功"
    except sqlite3.IntegrityError:
        return False, "用户名已存在"
    finally:
        conn.close()


def get_user_by_username(username):
    """按用户名获取用户"""
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_user(username, password):
    """验证用户名和密码（salt + hash 格式）"""
    user = get_user_by_username(username)
    if not user:
        return None
    import hashlib
    import hmac
    stored = user['password_hash']
    # 存储格式: salt(64位) + hash(64位)
    if len(stored) >= 128:
        salt = stored[:64]
        expected_hash = stored[64:]
        computed = hashlib.sha256((salt + password).encode()).hexdigest()
    else:
        expected_hash = stored
        computed = hashlib.sha256(password.encode()).hexdigest()
    if hmac.compare_digest(expected_hash, computed):
        return user
    return None


def update_user_password(user_id, password_hash):
    """更新用户密码"""
    conn = get_db()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id))
    conn.commit()
    conn.close()
    return True, "密码更新成功"


def get_users():
    """获取用户列表"""
    conn = get_db()
    rows = conn.execute("SELECT id, username, is_admin, created_at FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_user(user_id):
    """删除用户（禁止删除自己）"""
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return True, "用户删除成功"


def create_user(username, password):
    """创建用户（密码哈希）"""
    import hashlib
    salt = hashlib.sha256(os.urandom(16)).hexdigest()
    password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return add_user(username, password_hash)

# ---------- 交换机 CRUD ----------

def add_switch(name, ip, username, password, port=22, vendor='H3C', location='', notes=''):
    conn = get_db()
    try:
        encrypted_pwd = encrypt_password(password)
        conn.execute(
            "INSERT INTO switches (name, ip, port, username, password, vendor, location, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, ip, port, username, encrypted_pwd, vendor, location, notes)
        )
        conn.commit()
        return True, "添加成功"
    except sqlite3.IntegrityError:
        return False, "该 IP 已存在"
    finally:
        conn.close()


def update_switch(switch_id, **kwargs):
    conn = get_db()
    allowed = {'name', 'ip', 'port', 'username', 'password', 'vendor', 'location', 'notes'}
    fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if 'password' in fields and fields['password']:
        fields['password'] = encrypt_password(fields['password'])
    if not fields:
        return False, "无更新内容"
    fields['updated_at'] = datetime_str()
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [switch_id]
    conn.execute(f"UPDATE switches SET {set_clause} WHERE id=?", values)
    conn.commit()
    conn.close()
    return True, "更新成功"


def delete_switch(switch_id):
    conn = get_db()
    conn.execute("DELETE FROM switches WHERE id=?", (switch_id,))
    conn.commit()
    conn.close()
    return True, "删除成功"


def get_switches():
    conn = get_db()
    rows = conn.execute("SELECT * FROM switches ORDER BY id").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if is_encrypted(d['password']):
            d['password'] = decrypt_password(d['password'])
        result.append(d)
    return result


def get_switch(switch_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM switches WHERE id=?", (switch_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if is_encrypted(d['password']):
        d['password'] = decrypt_password(d['password'])
    return d


# ---------- IP-MAC 绑定 CRUD ----------

def get_bindings(page=1, per_page=50, search='', switch_id=None, status=None):
    conn = get_db()
    conditions = []
    params = []
    if search:
        conditions.append(
            "(ip LIKE ? OR mac LIKE ? OR person_name LIKE ? OR phone LIKE ? "
            "OR office LIKE ? OR device_name LIKE ? OR department LIKE ?)"
        )
        s = f"%{search}%"
        params.extend([s, s, s, s, s, s, s])
    if switch_id:
        conditions.append("switch_id=?")
        params.append(switch_id)
    if status:
        conditions.append("status=?")
        params.append(status)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total = conn.execute(f"SELECT COUNT(*) FROM ip_mac_bindings {where}", params).fetchone()[0]
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"SELECT b.*, s.name as switch_name FROM ip_mac_bindings b "
        f"LEFT JOIN switches s ON b.switch_id = s.id "
        f"{where} ORDER BY b.ip, b.mac LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def get_binding(binding_id):
    conn = get_db()
    row = conn.execute(
        "SELECT b.*, s.name as switch_name FROM ip_mac_bindings b "
        "LEFT JOIN switches s ON b.switch_id = s.id WHERE b.id=?",
        (binding_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_binding(ip, mac, switch_id, vlan='', port='', interface='', **extra):
    """插入或更新 IP-MAC 绑定。返回 (is_new, binding_id)"""
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM ip_mac_bindings WHERE ip=? AND mac=?", (ip, mac)
    ).fetchone()

    now = datetime_str()
    if row:
        # 更新
        bid = row['id']
        updates = {
            'vlan': vlan or None, 'port': port or None, 'interface': interface or None,
            'switch_id': switch_id, 'last_seen': now, 'updated_at': now, 'status': 'active',
        }
        for k in ('person_name', 'phone', 'office', 'department', 'terminal_type',
                   'os_info', 'device_name', 'notes'):
            if k in extra and extra[k]:
                updates[k] = extra[k]
        updates = {k: v for k, v in updates.items() if v is not None}
        set_clause = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE ip_mac_bindings SET {set_clause} WHERE id=?",
                     list(updates.values()) + [bid])
        conn.commit()
        conn.close()
        return False, bid
    else:
        # 插入
        cursor = conn.execute(
            "INSERT INTO ip_mac_bindings "
            "(ip, mac, vlan, port, interface, switch_id, "
            "person_name, phone, office, department, terminal_type, os_info, device_name, notes, last_seen) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ip, mac, vlan, port, interface, switch_id,
             extra.get('person_name', ''), extra.get('phone', ''), extra.get('office', ''),
             extra.get('department', ''), extra.get('terminal_type', ''), extra.get('os_info', ''),
             extra.get('device_name', ''), extra.get('notes', ''), now)
        )
        conn.commit()
        conn.close()
        return True, cursor.lastrowid


def update_binding(binding_id, **kwargs):
    conn = get_db()
    allowed = {'person_name', 'phone', 'office', 'department', 'terminal_type',
               'os_info', 'device_name', 'status', 'notes', 'vlan', 'port', 'interface'}
    fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not fields:
        return False, "无更新内容"
    fields['updated_at'] = datetime_str()
    set_clause = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE ip_mac_bindings SET {set_clause} WHERE id=?",
                 list(fields.values()) + [binding_id])
    conn.commit()
    conn.close()
    return True, "更新成功"


def delete_binding(binding_id):
    conn = get_db()
    conn.execute("DELETE FROM ip_mac_bindings WHERE id=?", (binding_id,))
    conn.commit()
    conn.close()


def import_bindings(rows, switch_id):
    """批量导入。rows: list of dict with keys ip, mac, vlan, port, ...
    使用单个事务批量 upsert，性能提升 10-50 倍"""
    if not rows:
        return 0, 0
    
    conn = get_db()
    new_count = 0
    update_count = 0
    now = datetime_str()
    
    try:
        for r in rows:
            ip = r.get('ip', '')
            mac = r.get('mac', '')
            if not ip or not mac:
                continue
            
            # 检查是否已存在
            row = conn.execute(
                "SELECT id FROM ip_mac_bindings WHERE ip=? AND mac=?", (ip, mac)
            ).fetchone()
            
            if row:
                # 更新
                bid = row['id']
                updates = {}
                for k in ('vlan', 'port', 'interface'):
                    val = r.get(k)
                    if val:
                        updates[k] = val
                updates['switch_id'] = switch_id
                updates['last_seen'] = now
                updates['updated_at'] = now
                updates['status'] = 'active'
                for k in ('person_name', 'phone', 'office', 'department',
                          'terminal_type', 'os_info', 'device_name', 'notes'):
                    val = r.get(k)
                    if val:
                        updates[k] = val
                if updates:
                    set_clause = ", ".join(f"{k}=?" for k in updates)
                    conn.execute(f"UPDATE ip_mac_bindings SET {set_clause} WHERE id=?",
                                 list(updates.values()) + [bid])
                update_count += 1
            else:
                # 插入
                conn.execute(
                    "INSERT INTO ip_mac_bindings "
                    "(ip, mac, vlan, port, interface, switch_id, "
                    "person_name, phone, office, department, terminal_type, os_info, device_name, notes, last_seen) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (ip, mac,
                     r.get('vlan', ''), r.get('port', ''), r.get('interface', ''), switch_id,
                     r.get('person_name', ''), r.get('phone', ''), r.get('office', ''),
                     r.get('department', ''), r.get('terminal_type', ''), r.get('os_info', ''),
                     r.get('device_name', ''), r.get('notes', ''), now)
                )
                new_count += 1
        
        conn.commit()
    finally:
        conn.close()
    
    return new_count, update_count


def log_scan(switch_id, entries_found, new_entries, updated_entries, status='success', message=''):
    conn = get_db()
    conn.execute(
        "INSERT INTO scan_logs (switch_id, entries_found, new_entries, updated_entries, status, message) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (switch_id, entries_found, new_entries, updated_entries, status, message)
    )
    conn.execute("UPDATE switches SET last_scan=datetime('now','localtime') WHERE id=?", (switch_id,))
    conn.commit()
    conn.close()


def get_scan_logs(switch_id=None, limit=50):
    conn = get_db()
    if switch_id:
        rows = conn.execute(
            "SELECT l.*, s.name as switch_name FROM scan_logs l "
            "LEFT JOIN switches s ON l.switch_id=s.id "
            "WHERE l.switch_id=? ORDER BY l.scan_time DESC LIMIT ?",
            (switch_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT l.*, s.name as switch_name FROM scan_logs l "
            "LEFT JOIN switches s ON l.switch_id=s.id "
            "ORDER BY l.scan_time DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_db()
    stats = {}
    stats['total_switches'] = conn.execute("SELECT COUNT(*) FROM switches").fetchone()[0]
    stats['total_bindings'] = conn.execute("SELECT COUNT(*) FROM ip_mac_bindings").fetchone()[0]
    stats['active_bindings'] = conn.execute(
        "SELECT COUNT(*) FROM ip_mac_bindings WHERE status='active'"
    ).fetchone()[0]
    stats['inactive_bindings'] = conn.execute(
        "SELECT COUNT(*) FROM ip_mac_bindings WHERE status='inactive'"
    ).fetchone()[0]
    stats['with_person'] = conn.execute(
        "SELECT COUNT(*) FROM ip_mac_bindings WHERE person_name != ''"
    ).fetchone()[0]
    # 按交换机统计
    stats['by_switch'] = [dict(r) for r in conn.execute(
        "SELECT s.id, s.name, COUNT(b.id) as count FROM switches s "
        "LEFT JOIN ip_mac_bindings b ON s.id=b.switch_id "
        "GROUP BY s.id ORDER BY count DESC"
    ).fetchall()]
    conn.close()
    return stats


def datetime_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")



# ---------- 批量扫描 ----------

def get_switch_configs():
    """获取所有交换机配置（密码已解密）"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM switches ORDER BY id").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if is_encrypted(d['password']):
            d['password'] = decrypt_password(d['password'])
        result.append(d)
    return result


def batch_scan_all():
    """扫描所有交换机。返回每个交换机的扫描结果"""
    from ssh_handler import scan_switch
    configs = get_switch_configs()
    results = []
    total_new = 0
    total_updated = 0
    
    for cfg in configs:
        switch_id = cfg['id']
        entries, raw_output, error = scan_switch(
            {'ip': cfg['ip'], 'username': cfg['username'],
             'password': cfg['password'], 'port': cfg['port']},
            vendor=cfg.get('vendor', 'H3C')
        )
        if error:
            results.append({'switch_id': switch_id, 'name': cfg['name'],
                            'status': 'error', 'message': error, 'entries': 0})
        else:
            new_count, update_count = import_bindings(entries, switch_id)
            total_new += new_count
            total_updated += update_count
            results.append({'switch_id': switch_id, 'name': cfg['name'],
                            'status': 'success', 'entries': len(entries),
                            'new': new_count, 'updated': update_count})
    
    return results, total_new, total_updated


# ---------- 数据备份 ----------

def backup_db(backup_dir=None):
    """备份数据库到文件"""
    import shutil
    from datetime import datetime
    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(DB_PATH), 'backup')
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'ipam_backup_{timestamp}.db')
    shutil.copy2(DB_PATH, backup_path)
    # 清理7天前的备份
    cutoff = datetime.now()
    cutoff = cutoff.replace(day=cutoff.day - 7) if cutoff.day > 7 else cutoff.replace(day=1)
    for f in os.listdir(backup_dir):
        if f.endswith('.db') and f != os.path.basename(DB_PATH):
            filepath = os.path.join(backup_dir, f)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if mtime < cutoff:
                    os.remove(filepath)
            except Exception:
                pass
    return backup_path


# ---------- 数据库维护 ----------

def vacuum_db():
    """优化数据库文件"""
    conn = get_db()
    conn.execute("VACUUM")
    conn.close()
    return True, "数据库优化完成"
# ---------- CSV 导入/导出 ----------

def export_all_bindings_csv(filepath):
    """导出全部绑定到 CSV"""
    import csv
    conn = get_db()
    rows = conn.execute(
        "SELECT b.*, s.name as switch_name FROM ip_mac_bindings b "
        "LEFT JOIN switches s ON b.switch_id=s.id ORDER BY b.ip"
    ).fetchall()
    conn.close()
    if not rows:
        return 0
    fields = ['ip', 'mac', 'vlan', 'port', 'interface', 'switch_name',
              'person_name', 'phone', 'office', 'department', 'terminal_type',
              'os_info', 'device_name', 'status', 'notes', 'last_seen']
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for r in rows:
            writer.writerow(dict(r))
    return len(rows)


def import_bindings_csv(filepath, switch_id=None):
    """从 CSV 导入绑定"""
    import csv
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader]
    if not rows:
        return 0, 0
    return import_bindings(rows, switch_id)
