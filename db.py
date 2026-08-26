import sqlite3
from config import DB_PATH


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


# ---------- 交换机 CRUD ----------

def add_switch(name, ip, username, password, port=22, vendor='H3C', location='', notes=''):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO switches (name, ip, port, username, password, vendor, location, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, ip, port, username, password, vendor, location, notes)
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
    return [dict(r) for r in rows]


def get_switch(switch_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM switches WHERE id=?", (switch_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


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
    """批量导入。rows: list of dict with keys ip, mac, vlan, port, ..."""
    new_count = 0
    update_count = 0
    for r in rows:
        is_new, _ = upsert_binding(
            ip=r.get('ip', ''), mac=r.get('mac', ''), switch_id=switch_id,
            vlan=r.get('vlan', ''), port=r.get('port', ''), interface=r.get('interface', ''),
            person_name=r.get('person_name', ''), phone=r.get('phone', ''),
            office=r.get('office', ''), department=r.get('department', ''),
            terminal_type=r.get('terminal_type', ''), os_info=r.get('os_info', ''),
            device_name=r.get('device_name', ''), notes=r.get('notes', ''),
        )
        if is_new:
            new_count += 1
        else:
            update_count += 1
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
        "SELECT s.name, COUNT(b.id) as count FROM switches s "
        "LEFT JOIN ip_mac_bindings b ON s.id=b.switch_id "
        "GROUP BY s.id ORDER BY count DESC"
    ).fetchall()]
    conn.close()
    return stats


def datetime_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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
