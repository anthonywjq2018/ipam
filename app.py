"""
IPAM - IP 地址管理系统
Flask Web 服务
"""
import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from db import init_db, get_db, add_switch, update_switch, delete_switch, get_switches, get_switch
from db import get_bindings, get_binding, update_binding, delete_binding, import_bindings, log_scan
from db import get_scan_logs, get_stats, export_all_bindings_csv, import_bindings_csv
from ssh_handler import scan_switch

app = Flask(__name__)
app.secret_key = os.urandom(24)


# ==================== 页面路由 ====================

@app.route('/')
def index():
    stats = get_stats()
    return render_template('index.html', stats=stats)


@app.route('/switches')
def switches_page():
    switches = get_switches()
    return render_template('switches.html', switches=switches)


@app.route('/switches/<int:switch_id>')
def switch_detail(switch_id):
    switch = get_switch(switch_id)
    if not switch:
        return redirect(url_for('switches_page'))
    bindings, total = get_bindings(switch_id=switch_id, per_page=9999)
    logs = get_scan_logs(switch_id=switch_id, limit=20)
    return render_template('switch_detail.html', switch=switch, bindings=bindings, logs=logs, total=total)


@app.route('/bindings')
def bindings_page():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    switch_id = request.args.get('switch_id', None, type=int)
    status = request.args.get('status', '')
    bindings, total = get_bindings(page=page, search=search, switch_id=switch_id, status=status)
    switches = get_switches()
    total_pages = (total + 49) // 50
    return render_template('bindings.html', bindings=bindings, total=total,
                           page=page, total_pages=total_pages, search=search,
                           switches=switches, current_switch=switch_id, current_status=status)


@app.route('/logs')
def logs_page():
    logs = get_scan_logs(limit=100)
    return render_template('logs.html', logs=logs)


# ==================== API 路由 ====================

# --- 交换机 API ---

@app.route('/api/switches', methods=['POST'])
def api_add_switch():
    data = request.json or request.form
    ok, msg = add_switch(
        name=data.get('name', ''),
        ip=data.get('ip', ''),
        username=data.get('username', ''),
        password=data.get('password', ''),
        port=int(data.get('port', 22)),
        vendor=data.get('vendor', 'H3C'),
        location=data.get('location', ''),
        notes=data.get('notes', ''),
    )
    return jsonify({'ok': ok, 'message': msg})


@app.route('/api/switches/<int:switch_id>', methods=['PUT'])
def api_update_switch(switch_id):
    data = request.json or request.form
    ok, msg = update_switch(switch_id, **data)
    return jsonify({'ok': ok, 'message': msg})


@app.route('/api/switches/<int:switch_id>', methods=['DELETE'])
def api_delete_switch(switch_id):
    ok, msg = delete_switch(switch_id)
    return jsonify({'ok': ok, 'message': msg})


@app.route('/api/switches/<int:switch_id>/test', methods=['POST'])
def api_test_switch(switch_id):
    """测试 SSH 连接"""
    switch = get_switch(switch_id)
    if not switch:
        return jsonify({'ok': False, 'message': '交换机不存在'})
    from ssh_handler import connect_switch, disconnect_switch
    client = None
    try:
        client = connect_switch(switch['ip'], switch['username'], switch['password'],
                                port=switch['port'])
        return jsonify({'ok': True, 'message': '连接成功 ✓'})
    except Exception as e:
        return jsonify({'ok': False, 'message': f'连接失败: {str(e)}'})
    finally:
        disconnect_switch(client)


# --- 扫描 API ---

@app.route('/api/scan/<int:switch_id>', methods=['POST'])
def api_scan_switch(switch_id):
    """扫描交换机 ARP 表"""
    switch = get_switch(switch_id)
    if not switch:
        return jsonify({'ok': False, 'message': '交换机不存在'})
    
    entries, raw_output, error = scan_switch(
        {'ip': switch['ip'], 'username': switch['username'],
         'password': switch['password'], 'port': switch['port']},
        vendor=switch.get('vendor', 'H3C')
    )
    
    if error:
        log_scan(switch_id, 0, 0, 0, status='error', message=error)
        return jsonify({'ok': False, 'message': error, 'entries': []})
    
    # 保存到数据库
    new_count, update_count = import_bindings(entries, switch_id)
    log_scan(switch_id, len(entries), new_count, update_count)
    
    return jsonify({
        'ok': True,
        'message': f'扫描完成: 发现 {len(entries)} 条记录, 新增 {new_count} 条, 更新 {update_count} 条',
        'entries': entries,
        'new': new_count,
        'updated': update_count,
        'total': len(entries),
    })


# --- 绑定 API ---

@app.route('/api/bindings/<int:binding_id>', methods=['PUT'])
def api_update_binding(binding_id):
    data = request.json or request.form
    ok, msg = update_binding(binding_id, **data)
    return jsonify({'ok': ok, 'message': msg})


@app.route('/api/bindings/<int:binding_id>', methods=['DELETE'])
def api_delete_binding(binding_id):
    delete_binding(binding_id)
    return jsonify({'ok': True, 'message': '删除成功'})


@app.route('/api/bindings/batch-delete', methods=['POST'])
def api_batch_delete_bindings():
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({'ok': False, 'message': '请选择要删除的记录'})
    conn = get_db()
    placeholders = ','.join(['?'] * len(ids))
    conn.execute(f"DELETE FROM ip_mac_bindings WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': f'已删除 {len(ids)} 条记录'})


# --- CSV 导入/导出 ---

@app.route('/api/export/csv')
def api_export_csv():
    filepath = os.path.join(app.root_path, 'data', 'export.csv')
    count = export_all_bindings_csv(filepath)
    if count == 0:
        return jsonify({'ok': False, 'message': '无数据可导出'})
    return send_file(filepath, as_attachment=True,
                     download_name=f'ipam_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')


@app.route('/api/import/csv', methods=['POST'])
def api_import_csv():
    file = request.files.get('file')
    switch_id = request.form.get('switch_id', None, type=int)
    if not file:
        return jsonify({'ok': False, 'message': '请选择文件'})
    filepath = os.path.join(app.root_path, 'data', 'import.csv')
    file.save(filepath)
    new, updated = import_bindings_csv(filepath, switch_id)
    return jsonify({'ok': True, 'message': f'导入完成: 新增 {new} 条, 更新 {updated} 条'})


# --- 统计 API ---

@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())


# ==================== 启动 ====================

if __name__ == '__main__':
    from config import HOST, PORT, DEBUG
    init_db()
    print(f"\n{'='*50}")
    print(f"  IPAM - IP 地址管理系统")
    print(f"  访问地址: http://localhost:{PORT}")
    print(f"{'='*50}\n")
    app.run(host=HOST, port=PORT, debug=DEBUG)
