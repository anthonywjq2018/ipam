"""
IPAM - IP 地址管理系统
Flask Web 服务
"""
import os
import json
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session
from db import init_db, get_db, add_switch, update_switch, delete_switch, get_switches, get_switch, add_user, verify_user
from db import get_bindings, get_binding, update_binding, delete_binding, import_bindings, log_scan
from db import get_scan_logs, get_stats, export_all_bindings_csv, import_bindings_csv
from ssh_handler import scan_switch

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour


# ==================== 认证中间件 ====================

def login_required(f):
    """登录装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'ok': False, 'message': '请先登录', 'code': 401}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


def init_default_user():
    """初始化默认用户（首次启动）"""
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    conn.close()
    if row['cnt'] == 0:
        salt = hashlib.sha256(os.urandom(16)).hexdigest()
        pwd_hash = hashlib.sha256((salt + 'admin').encode()).hexdigest()
        # 保存盐值和哈希到同一字段（salt+hash 组合）
        combined = salt + pwd_hash
        add_user('admin', combined)
        return True
    return False


# ==================== 认证路由 ====================

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """登录页面"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            return render_template('login.html', error='用户名和密码不能为空')
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        user = verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session.permanent = True
            return redirect(url_for('index'))
        return render_template('login.html', error='用户名或密码错误')
    return render_template('login.html', error='')


@app.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/api/login', methods=['POST'])
def api_login():
    """API 登录"""
    data = request.json or request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'ok': False, 'message': '用户名和密码不能为空', 'code': 400})
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    user = verify_user(username, password)
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session.permanent = True
        return jsonify({'ok': True, 'message': '登录成功', 'username': username})
    return jsonify({'ok': False, 'message': '用户名或密码错误', 'code': 401})


@app.route('/api/logout')
def api_logout():
    """API 登出"""
    session.clear()
    return jsonify({'ok': True, 'message': '已登出'})


@app.route('/api/me')
def api_me():
    """当前用户信息"""
    if 'user_id' not in session:
        return jsonify({'ok': False, 'message': '未登录', 'code': 401})
    return jsonify({'ok': True, 'username': session.get('username'), 'user_id': session.get('user_id')})




@app.route('/')
@login_required
def index():
    stats = get_stats()
    logs = get_scan_logs(limit=10)
    return render_template('index.html', stats=stats, logs=logs)


@app.route('/switches')
@login_required
def switches_page():
    switches = get_switches()
    return render_template('switches.html', switches=switches)


@app.route('/switches/<int:switch_id>')
@login_required
def switch_detail(switch_id):
    switch = get_switch(switch_id)
    if not switch:
        return redirect(url_for('switches_page'))
    bindings, total = get_bindings(switch_id=switch_id, per_page=9999)
    logs = get_scan_logs(switch_id=switch_id, limit=20)
    return render_template('switch_detail.html', switch=switch, bindings=bindings, logs=logs, total=total)


@app.route('/bindings')
@login_required
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
@login_required
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

@app.route('/api/scan/all', methods=['POST'])
@login_required
def api_scan_all_switches():
    """扫描所有交换机"""
    from db import batch_scan_all
    results, total_new, total_updated = batch_scan_all()
    return jsonify({
        'ok': True,
        'message': f'批量扫描完成: 新增 {total_new} 条, 更新 {total_updated} 条',
        'results': results,
        'total_new': total_new,
        'total_updated': total_updated
    })

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


# --- 用户管理 API ---

@app.route('/api/users', methods=['POST'])
@login_required
def api_add_user():
    """添加用户"""
    data = request.json or request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'ok': False, 'message': '用户名和密码不能为空'})
    if len(password) < 6:
        return jsonify({'ok': False, 'message': '密码至少 6 位'})
    ok, msg = create_user(username, password)
    return jsonify({'ok': ok, 'message': msg})


@app.route('/api/users', methods=['GET'])
@login_required
def api_get_users():
    """获取用户列表"""
    users = get_users()
    return jsonify({'ok': True, 'users': users})


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    """删除用户"""
    if user_id == session.get('user_id'):
        return jsonify({'ok': False, 'message': '不能删除自己的账号'})
    ok, msg = delete_user(user_id)
    return jsonify({'ok': ok, 'message': msg})


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def api_update_user(user_id):
    """更新用户密码"""
    data = request.json or request.form
    new_password = data.get('password', '')
    if not new_password or len(new_password) < 6:
        return jsonify({'ok': False, 'message': '新密码至少 6 位'})
    ok, msg = update_user_password(user_id, new_password)
    return jsonify({'ok': ok, 'message': msg})




# --- 备份维护 API ---

@app.route('/api/backup', methods=['POST'])
@login_required
def api_backup():
    """手动备份数据库"""
    from db import backup_db
    try:
        backup_path = backup_db()
        return jsonify({'ok': True, 'message': f'备份成功: {os.path.basename(backup_path)}'})
    except Exception as e:
        return jsonify({'ok': False, 'message': f'备份失败: {str(e)}'})


@app.route('/api/vacuum', methods=['POST'])
@login_required
def api_vacuum():
    """优化数据库"""
    from db import vacuum_db
    ok, msg = vacuum_db()
    return jsonify({'ok': ok, 'message': msg})


@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())


# ==================== 启动 ====================

if __name__ == '__main__':
    from config import HOST, PORT, DEBUG
    init_db()
    init_default_user()
    print(f"\n{'='*50}")
    print(f"  IPAM - IP 地址管理系统")
    print(f"  访问地址: http://localhost:{PORT}")
    print(f"  默认用户名: admin")
    print(f"  默认密码: admin")
    print(f"  首次登录后请立即修改密码")
    print(f"{'='*50}\n")
    app.run(host=HOST, port=PORT, debug=DEBUG)
