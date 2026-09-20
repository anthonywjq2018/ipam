#!/bin/bash
# IPAM Linux 安装脚本
# 支持 Ubuntu/Debian/CentOS/RHEL/Rocky/AlmaLinux

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 默认配置
INSTALL_DIR="/opt/ipam"
SERVICE_NAME="ipam"
USER="ipam"
PYTHON_VERSION="3.11"

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    else
        log_error "无法检测操作系统"
        exit 1
    fi
    log_info "检测到操作系统: $PRETTY_NAME"
}

# 安装 Python
install_python() {
    log_info "安装 Python $PYTHON_VERSION..."
    
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y python3 python3-venv python3-pip python3-dev \
                libffi-dev gcc make
            ;;
        centos|rhel|rocky|almalinux)
            yum install -y python3 python3-venv python3-pip python3-devel \
                libffi-devel gcc make
            ;;
        *)
            log_warn "未知操作系统，尝试使用包管理器安装 Python..."
            ;;
    esac
}

# 创建用户
create_user() {
    if id "$USER" &>/dev/null; then
        log_info "用户 $USER 已存在"
    else
        useradd -r -s /bin/bash -d $INSTALL_DIR $USER
        log_success "创建用户 $USER"
    fi
}

# 复制文件
copy_files() {
    log_info "复制应用文件到 $INSTALL_DIR..."
    mkdir -p $INSTALL_DIR
    cp -r ../../* $INSTALL_DIR/
    chown -R $USER:$USER $INSTALL_DIR
}

# 创建虚拟环境并安装依赖
setup_venv() {
    log_info "创建虚拟环境并安装依赖..."
    sudo -u $USER bash -c "
        cd $INSTALL_DIR
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    "
}

# 创建数据目录
create_data_dirs() {
    log_info "创建数据目录..."
    mkdir -p $INSTALL_DIR/data/backups
    chown -R $USER:$USER $INSTALL_DIR/data
}

# 生成 systemd 服务文件
create_service() {
    log_info "创建 systemd 服务..."
    cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=IPAM - IP Address Management System
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=DB_TYPE=sqlite
Environment=HOST=0.0.0.0
Environment=PORT=5100
Environment=DEBUG=false
Environment=SECRET_KEY=$(openssl rand -hex 32)
Environment=SSH_TIMEOUT=10
ExecStart=$INSTALL_DIR/venv/bin/python app.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    log_success "systemd 服务已创建: $SERVICE_NAME"
}

# 启动服务
start_service() {
    log_info "启动服务..."
    systemctl enable $SERVICE_NAME
    systemctl start $SERVICE_NAME
    sleep 3
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_success "服务启动成功"
    else
        log_error "服务启动失败，查看日志: journalctl -u $SERVICE_NAME -f"
        exit 1
    fi
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    if command -v ufw &>/dev/null; then
        ufw allow 5100/tcp
        log_success "UFW 已放行 5100 端口"
    elif command -v firewall-cmd &>/dev/null; then
        firewall-cmd --permanent --add-port=5100/tcp
        firewall-cmd --reload
        log_success "firewalld 已放行 5100 端口"
    else
        log_warn "未检测到防火墙，请手动放行 5100 端口"
    fi
}

# 显示完成信息
show_completion() {
    echo ""
    echo "========================================"
    echo "  IPAM 安装完成！"
    echo "========================================"
    echo ""
    echo "访问地址: http://$(hostname -I | awk '{print $1}'):5100"
    echo "默认账号: admin"
    echo "默认密码: Admin@123"
    echo ""
    echo "常用命令:"
    echo "  启动服务: systemctl start $SERVICE_NAME"
    echo "  停止服务: systemctl stop $SERVICE_NAME"
    echo "  重启服务: systemctl restart $SERVICE_NAME"
    echo "  查看状态: systemctl status $SERVICE_NAME"
    echo "  查看日志: journalctl -u $SERVICE_NAME -f"
    echo ""
    echo "配置文件: $INSTALL_DIR/config.py"
    echo "数据目录: $INSTALL_DIR/data"
    echo ""
}

# 主流程
main() {
    echo "========================================"
    echo "  IPAM Linux 自动安装脚本"
    echo "========================================"
    echo ""
    
    # 检查 root 权限
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 权限运行: sudo $0"
        exit 1
    fi
    
    detect_os
    install_python
    create_user
    copy_files
    setup_venv
    create_data_dirs
    create_service
    setup_firewall
    start_service
    show_completion
}

main "$@"