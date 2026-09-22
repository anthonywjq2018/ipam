#!/usr/bin/env python3
"""从旧版 SQLite 数据库导出全部数据为 JSON（供迁移到 MySQL 使用）。

用法: python3 scripts/export_sqlite.py [sqlite路径] > export.json
默认路径: data/ipam.db
"""
import json
import sqlite3
import sys
from pathlib import Path

TABLES = ["users", "switches", "ip_mac_bindings", "scan_logs", "system_config"]


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/ipam.db"
    if not Path(db_path).exists():
        print(f"文件不存在: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    data = {}
    for table in TABLES:
        try:
            cur.execute(f"SELECT * FROM {table}")
            rows = [dict(r) for r in cur.fetchall()]
        except sqlite3.OperationalError:
            rows = []  # 表不存在
        data[table] = rows

    conn.close()

    export = {
        "version": "1.0",
        "exported_from": "sqlite",
        "tables": data,
    }
    # restore 接口需要 data 字段
    export["data"] = data
    print(json.dumps(export, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
