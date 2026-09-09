// IPAM 通用工具函数
const API_BASE = '';

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
    container.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function apiGet(url) {
    return fetch(API_BASE + url, { credentials: 'same-origin' }).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    });
}

function apiPost(url, data) {
    return fetch(API_BASE + url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        credentials: 'same-origin'
    }).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    });
}

function apiPut(url, data) {
    return fetch(API_BASE + url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        credentials: 'same-origin'
    }).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    });
}

function apiDelete(url) {
    return fetch(API_BASE + url, { method: 'DELETE', credentials: 'same-origin' })
        .then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        });
}

function formatMac(mac) {
    if (!mac) return '';
    const clean = mac.replace(/[^0-9a-fA-F]/g, '').toUpperCase();
    return clean.replace(/(.{2})/g, '$1-').slice(0, -1);
}

function formatIp(ip) {
    return ip || '';
}

function getStatusBadge(status) {
    const map = {
        active: '<span class="badge bg-success status-active">活跃</span>',
        inactive: '<span class="badge bg-danger status-inactive">非活跃</span>',
        reserved: '<span class="badge bg-warning text-dark status-reserved">预留</span>'
    };
    return map[status] || `<span class="badge bg-secondary">${status}</span>`;
}

function getTerminalIcon(type) {
    const icons = {
        pc: 'bi-hdd', laptop: 'bi-laptop', phone: 'bi-phone',
        tablet: 'bi-tablet', printer: 'bi-printer', camera: 'bi-camera-video',
        iot: 'bi-cpu', server: 'bi-server', other: 'bi-question-circle'
    };
    return icons[type] || 'bi-question-circle';
}

function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

// 导出 CSV
function exportCSV() {
    window.location.href = '/api/export/csv';
}

// 导入 CSV
function importCSV() {
    const modal = new bootstrap.Modal(document.getElementById('importModal'));
    modal.show();
}

function submitImport() {
    const form = document.getElementById('importForm');
    const formData = new FormData(form);
    const modalEl = document.getElementById('importModal');
    const btn = modalEl.querySelector('.modal-footer .btn-primary');
    const modal = bootstrap.Modal.getInstance(modalEl);
    
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 导入中...';
    }
    
    fetch('/api/import/csv', { method: 'POST', body: formData, credentials: 'same-origin' })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                showToast(data.message, 'success');
                if (modal) modal.hide();
                setTimeout(() => location.reload(), 500);
            } else {
                showToast(data.message, 'danger');
            }
        })
        .catch(err => showToast('导入失败: ' + err.message, 'danger'))
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>确认导入';
            }
        });
}

// 批量删除
function deleteSelectedBindings() {
    const ids = Array.from(document.querySelectorAll('#bindings-table tbody input[type="checkbox"]:checked'))
        .map(cb => cb.value);
    if (!ids.length) { showToast('请先选择要删除的记录', 'warning'); return; }
    if (!confirm(`确定删除选中的 ${ids.length} 条记录？`)) return;
    
    apiPost('/api/bindings/batch-delete', { ids })
        .then(data => {
            if (data.ok) { showToast(data.message, 'success'); loadBindings(); }
            else showToast(data.message, 'danger');
        })
        .catch(err => showToast('删除失败: ' + err.message, 'danger'));
}

// 全选/反选
function setupCheckAll(checkAllId, tableBodyId) {
    const checkAll = document.getElementById(checkAllId);
    const tbody = document.getElementById(tableBodyId);
    if (checkAll && tbody) {
        checkAll.addEventListener('change', () => {
            tbody.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = checkAll.checked);
        });
    }
}