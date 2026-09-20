// IPAM 系统 - 通用前端工具
(function() {
    'use strict';
    
    // 全局配置
    const API_BASE = '/api';
    
    // Axios 拦截器 - 自动处理 401
    axios.interceptors.response.use(
        response => response,
        error => {
            if (error.response && error.response.status === 401) {
                window.location.href = '/login';
            }
            return Promise.reject(error);
        }
    );
    
    // Toast 通知
    window.showToast = function(message, type = 'info') {
        const toast = document.createElement('div');
        const bgClass = {
            success: 'bg-success',
            danger: 'bg-danger',
            warning: 'bg-warning',
            info: 'bg-info'
        }[type] || 'bg-info';
        
        toast.className = `toast align-items-center text-white ${bgClass} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>`;
        
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(container);
        }
        
        container.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, {delay: 3000});
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    };
    
    // 确认对话框
    window.confirmDialog = function(message, onConfirm) {
        if (confirm(message)) {
            onConfirm();
        }
    };
    
    // 加载状态管理
    window.loadingManager = {
        show: function(btn) {
            if (!btn) return;
            btn.dataset.originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>处理中...';
        },
        hide: function(btn) {
            if (!btn) return;
            btn.disabled = false;
            btn.innerHTML = btn.dataset.originalText || '保存';
        }
    };
    
    // 日期格式化
    window.formatDate = function(dateStr) {
        if (!dateStr) return '-';
        const d = new Date(dateStr);
        return d.toLocaleString('zh-CN', {
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    };
    
    // 防抖
    window.debounce = function(fn, delay) {
        let timer;
        return function(...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    };
    
    // 导出工具函数
    window.IPAM = {
        formatDate,
        debounce,
        showToast
    };
    
})();