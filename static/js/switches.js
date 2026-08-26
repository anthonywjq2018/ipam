// switches.js - 交换机管理页面逻辑

let currentEditId = null;

document.addEventListener('DOMContentLoaded', () => {
    loadSwitches();
    setupForm();
});

function loadSwitches() {
    apiGet('/api/switches')
        .then(data => renderSwitches(data))
        .catch(err => showToast('加载失败: ' + err.message, 'danger'));
}

function renderSwitches(switches) {
    const tbody = document.querySelector('#switches-table tbody');
    if (!switches.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">暂无交换机，点击"添加交换机"开始</td></tr>';
        return;
    }
    tbody.innerHTML = switches.map(s => `
        <tr>
            <td><strong>${escapeHtml(s.name)}</strong></td>
            <td class="ip-addr">${escapeHtml(s.ip)}</td>
            <td><span class="badge bg-info text-dark">${escapeHtml(s.vendor)}</span></td>
            <td>${escapeHtml(s.location || '-')}</td>
            <td>${s.port}</td>
            <td class="text-muted small">${s.last_scan || '从未'}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <a href="/switches/${s.id}" class="btn btn-outline-primary" title="详情"><i class="bi bi-eye"></i></a>
                    <button class="btn btn-outline-secondary" onclick="editSwitch(${s.id})" title="编辑"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-outline-info" onclick="testSwitch(${s.id})" title="测试连接"><i class="bi bi-wifi"></i></button>
                    <button class="btn btn-outline-danger" onclick="deleteSwitch(${s.id}, '${escapeHtml(s.name)}')" title="删除"><i class="bi bi-trash"></i></button>
                </div>
            </td>
        </tr>
    `).join('');
}

function setupForm() {
    const form = document.getElementById('switchForm');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        data.port = parseInt(data.port) || 22;
        
        const btn = document.getElementById('submitBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 保存中...';
        
        const url = currentEditId ? `/api/switches/${currentEditId}` : '/api/switches';
        const method = currentEditId ? 'PUT' : 'POST';
        
        fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data), credentials: 'same-origin' })
            .then(r => r.json())
            .then(res => {
                if (res.ok) {
                    showToast(res.message, 'success');
                    bootstrap.Modal.getInstance(document.getElementById('addSwitchModal')).hide();
                    loadSwitches();
                    resetForm();
                } else showToast(res.message, 'danger');
            })
            .catch(err => showToast('操作失败: ' + err.message, 'danger'))
            .finally(() => { btn.disabled = false; btn.innerHTML = '<i class="bi bi-check-lg"></i> 保存'; });
    });
    
    // 模态框关闭时重置
    document.getElementById('addSwitchModal').addEventListener('hidden.bs.modal', resetForm);
}

function resetForm() {
    document.getElementById('switchForm').reset();
    document.getElementById('switchId').value = '';
    document.getElementById('modalTitle').innerHTML = '<i class="bi bi-plus-lg"></i> 添加交换机';
    document.getElementById('submitBtn').innerHTML = '<i class="bi bi-check-lg"></i> 保存';
    currentEditId = null;
    document.getElementById('swPass').removeAttribute('readonly');
}

function editSwitch(id) {
    apiGet(`/api/switches/${id}`).then(s => {
        currentEditId = s.id;
        document.getElementById('switchId').value = s.id;
        document.getElementById('swName').value = s.name;
        document.getElementById('swIp').value = s.ip;
        document.getElementById('swUser').value = s.username;
        document.getElementById('swPass').value = s.password;
        document.getElementById('swPort').value = s.port;
        document.getElementById('swVendor').value = s.vendor;
        document.getElementById('swLoc').value = s.location || '';
        document.getElementById('swNotes').value = s.notes || '';
        document.getElementById('modalTitle').innerHTML = '<i class="bi bi-pencil-square"></i> 编辑交换机';
        document.getElementById('submitBtn').innerHTML = '<i class="bi bi-check-lg"></i> 更新';
        document.getElementById('swPass').removeAttribute('readonly');
        new bootstrap.Modal(document.getElementById('addSwitchModal')).show();
    }).catch(err => showToast('加载失败: ' + err.message, 'danger'));
}

function deleteSwitch(id, name) {
    if (!confirm(`确定删除交换机 "${name}"？\n此操作不可恢复，关联的 ARP 记录将保留但失去交换机关联。`)) return;
    apiDelete(`/api/switches/${id}`)
        .then(data => { if (data.ok) { showToast(data.message, 'success'); loadSwitches(); } else showToast(data.message, 'danger'); })
        .catch(err => showToast('删除失败: ' + err.message, 'danger'));
}

function testSwitch(id) {
    const btn = event.target.closest('button');
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    
    apiPost(`/api/switches/${id}/test`, {})
        .then(data => showToast(data.message, data.ok ? 'success' : 'danger'))
        .catch(err => showToast('测试失败: ' + err.message, 'danger'))
        .finally(() => { btn.disabled = false; btn.innerHTML = original; });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}