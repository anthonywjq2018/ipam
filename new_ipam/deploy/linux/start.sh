#!/bin/bash
# IPAM Linux 启动脚本

set -e

SERVICE_NAME="ipam"
INSTALL_DIR="/opt/ipam"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
log_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

# 检查是否以 systemd 服务运行
if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
    log_info "服务已在运行中"
    exit 0
fi

# 尝试启动 systemd 服务
if systemctl list-unit-files | grep -q "^$SERVICE_NAME.service"; then
    log_info "启动 systemd 服务..."
    systemctl start $SERVICE_NAME
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_success "服务启动成功"
        exit 0
    else
        log_error "systemd 服务启动失败"
        exit 1
    fi
fi

# 如果没有 systemd 服务，直接运行
log_info "未找到 systemd 服务，直接运行..."
cd $INSTALL_DIR

if [ ! -d "venv" ]; then
    log_error "虚拟环境不存在，请先运行安装脚本"
    exit 1
fi

source venv/bin/activate
export DB_TYPE=sqlite
export HOST=0.0.0.0
export PORT=5100
export DEBUG=false
export SECRET_KEY=$(openssl rand -hex 32)

log_info "在后台启动 IPAM..."
nohup python app.py > /var/log/ipam.log 2>&1 &
PID=$!
echo $PID > /tmp/ipam.pid
sleep 2

if kill -0 $PID 2>/dev/null; then
    log_success "IPAM 已启动 (PID: $PID)"
    log_info "日志文件: /var/log/ipam.log"
else
    log_error "启动失败，查看日志: cat /var/log/ipam.log"
    exit 1
fi