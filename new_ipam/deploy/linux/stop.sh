#!/bin/bash
# IPAM Linux 停止脚本

set -e

SERVICE_NAME="ipam"
INSTALL_DIR="/opt/ipam"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
log_warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }

# 检查是否以 systemd 服务运行
if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
    log_info "停止 systemd 服务..."
    systemctl stop $SERVICE_NAME
    log_success "服务已停止"
    exit 0
fi

# 如果没有 systemd 服务，尝试从 PID 文件停止
if [ -f /tmp/ipam.pid ]; then
    PID=$(cat /tmp/ipam.pid)
    if kill -0 $PID 2>/dev/null; then
        log_info "停止后台进程 (PID: $PID)..."
        kill $PID
        sleep 1
        if kill -0 $PID 2>/dev/null; then
            log_warn "进程未响应 SIGTERM，发送 SIGKILL..."
            kill -9 $PID
        fi
        rm -f /tmp/ipam.pid
        log_success "后台进程已停止"
        exit 0
    else
        log_warn "PID 文件存在但进程不存在，清理..."
        rm -f /tmp/ipam.pid
    fi
fi

# 最后尝试通过进程名查找
pkill -f "python app.py" 2>/dev/null || true
log_info "尝试通过进程名停止相关进程..."
sleep 1

log_success "停止操作完成"