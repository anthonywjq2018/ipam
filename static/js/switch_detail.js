// switch_detail.js - 交换机详情页逻辑

let currentPage = 1;
const PER_PAGE = 50;

document.addEventListener('DOMContentLoaded', () => {
    loadBindings();
    setupBindingForm();
    setupCheckAll('checkAll', 'bindings-table tbody');
});

function loadBindings(page = 1) {
    currentPage = page;
    apiGet(`/api/bindings?switch_id=${SWITCH_ID}&page=${page}&per_page=${PER_PAGE}`)
        .then(data => renderBindings(data.bindings, data.total))
        .catch(err => showToast('加载失败: ' + err.message, 'danger'));
}

function renderBindings(bindings, total) {
    const tbody = document.querySelector('#bindings-table tbody');
    if (!bindings.length) {
        tbody.innerHTML = '<tr><td colspan="15" class="text-center text-muted py-4">该交换机暂无 ARP 记录，点击"扫描 ARP"获取</td></tr>';
        return;
    }
    tbody.innerHTML = bindings.map(b => `
        <tr data-id="${b.id}">
            <td><input type="checkbox" value="${b.id}"></td>
            <td class="ip-addr">${escapeHtml(b.ip)}</td>
            <td class="mac-addr">${formatMac(b.mac)}</td>
            <td>${escapeHtml(b.vlan || '-')}</td>
            <td>${escapeHtml(b.interface || '-')}</td>
            <td>${escapeHtml(b.person_name || '-')}</td>
            <td>${escapeHtml(b.phone || '-')}</td>
            <td>${escapeHtml(b.office || '-')}</td>
            <td>${escapeHtml(b.department || '-')}</td>
            <td>${b.terminal_type ? `<i class="bi ${getTerminalIcon(b.terminal_type)} text-primary"></i> ${escapeHtml(b.terminal_type)}` : '-'}</td>
            <td>${escapeHtml(b.os_info || '-')}</td>
            <td>${escapeHtml(b.device_name || '-')}</td>
            <td>${getStatusBadge(b.status)}</td>
            <td class="text-muted small">${b.last_seen || '-'}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editBinding(${b.id})" title="编辑"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-outline-danger" onclick="deleteBinding(${b.id})" title="删除"><i class="bi bi-trash"></i></button>
                </div>
            </td>
        </tr>
    `).join('');
}

function scanSwitch() {
    const btn = event.target.closest('button');
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 扫描中...';
    
    apiPost(`/api/scan/${SWITCH_ID}`, {})
        .then(data => {
            if (data.ok) {
                showToast(data.message, 'success');
                loadBindings();
                // 刷新日志标签页
                setTimeout(() => location.reload(), 1000);
            } else showToast(data.message, 'danger');
        })
        .catch(err => showToast('扫描失败: ' + err.message, 'danger'))
        .finally(() => { btn.disabled = false; btn.innerHTML = original; });
}

function setupBindingForm() {
    const form = document.getElementById('bindingForm');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        const id = data.id;
        delete data.id;
        
        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 保存中...';
        
        apiPut(`/api/bindings/${id}`, data)
            .then(res => {
                if (res.ok) {
                    showToast(res.message, 'success');
                    bootstrap.Modal.getInstance(document.getElementById('editBindingModal')).hide();
                    loadBindings(currentPage);
                } else showToast(res.message, 'danger');
            })
            .catch(err => showToast('保存失败: ' + err.message, 'danger'))
            .finally(() => { btn.disabled = false; btn.innerHTML = '<i class="bi bi-check-lg"></i> 保存'; });
    });
}

function editBinding(id) {
    // 如果是批量编辑（从列表页点击编辑选中），取第一个选中的
    if (id === null) {
        const checked = document.querySelectorAll('#bindings-table tbody input[type="checkbox"]:checked');
        if (!checked.length) { showToast('请先选择要编辑的记录', 'warning'); return; }
        id = checked[0].value;
    }
    
    apiGet(`/api/bindings/${id}`).then(b => {
        document.getElementById('bindId').value = b.id;
        document.getElementById('bindIp').value = b.ip;
        document.getElementById('bindMac').value = b.mac;
        document.getElementById('bindVlan').value = b.vlan || '';
        document.getElementById('bindPort').value = b.port || '';
        document.getElementById('bindInterface').value = b.interface || '';
        document.getElementById('bindStatus').value = b.status;
        document.getElementById('bindName').value = b.person_name || '';
        document.getElementById('bindPhone').value = b.phone || '';
        document.getElementById('bindOffice').value = b.office || '';
        document.getElementById('bindDept').value = b.department || '';
        document.getElementById('bindTerm').value = b.terminal_type || '';
        document.getElementById('bindOs').value = b.os_info || '';
        document.getElementById('bindDevice').value = b.device_name || '';
        document.getElementById('bindNotes').value = b.notes || '';
        
        new bootstrap.Modal(document.getElementById('editBindingModal')).show();
    }).catch(err => showToast('加载失败: ' + err.message, 'danger'));
}

function deleteBinding(id) {
    if (!confirm('确定删除这条记录？')) return;
    apiDelete(`/api/bindings/${id}`)
        .then(data => { if (data.ok) { showToast(data.message, 'success'); loadBindings(currentPage); } else showToast(data.message, 'danger'); })
        .catch(err => showToast('删除失败: ' + err.message, 'danger'));
}

function deleteSelectedBindings() {
    const ids = Array.from(document.querySelectorAll('#bindings-table tbody input[type="checkbox"]:checked'))
        .map(cb => cb.value);
    if (!ids.length) { showToast('请先选择要删除的记录', 'warning'); return; }
    if (!confirm(`确定删除选中的 ${ids.length} 条记录？`)) return;
    
    apiPost('/api/bindings/batch-delete', { ids })
        .then(data => { if (data.ok) { showToast(data.message, 'success'); loadBindings(currentPage); } else showToast(data.message, 'danger'); })
        .catch(err => showToast('删除失败: ' + err.message, 'danger'));
}

// 复用 app.js 的工具函数
function apiGet(url) { return fetch(url, {credentials:'same-origin'}).then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();}); }
function apiPost(url,data){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),credentials:'same-origin'}).then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();});}
function apiPut(url,data){return fetch(url,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),credentials:'same-origin'}).then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();});}
function apiDelete(url){return fetch(url,{method:'DELETE',credentials:'same-origin'}).then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();});}
function formatMac(mac){if(!mac)return'';const c=mac.replace(/[^0-9a-fA-F]/g,'').toUpperCase();return c.replace(/(.{2})/g,'$1-').slice(0,-1);}
function getStatusBadge(s){const m={active:'<span class="badge bg-success">活跃</span>',inactive:'<span class="badge bg-danger">非活跃</span>',reserved:'<span class="badge bg-warning text-dark">预留</span>'};return m[s]||`<span class="badge bg-secondary">${s}</span>`;}
function getTerminalIcon(t){const i={pc:'bi-hdd',laptop:'bi-laptop',phone:'bi-phone',tablet:'bi-tablet',printer:'bi-printer',camera:'bi-camera-video',iot:'bi-cpu',server:'bi-server',other:'bi-question-circle'};return i[t]||'bi-question-circle';}
function showToast(msg,type='info'){const t=document.createElement('div');t.className=`toast align-items-center text-white bg-${type} border-0`;t.setAttribute('role','alert');t.innerHTML=`<div class="d-flex"><div class="toast-body">${msg}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;let c=document.querySelector('.toast-container');if(!c){c=document.createElement('div');c.className='toast-container position-fixed bottom-0 end-0 p-3';document.body.appendChild(c);}c.appendChild(t);new bootstrap.Toast(t,{delay:3000}).show();t.addEventListener('hidden.bs.toast',()=>t.remove());}
function escapeHtml(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML;}
function setupCheckAll(a,b){const c=document.getElementById(a),d=document.querySelector(b);if(c&&d){c.addEventListener('change',()=>d.querySelectorAll('input[type="checkbox"]').forEach(e=>e.checked=c.checked));}}