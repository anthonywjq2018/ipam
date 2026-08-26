#!/bin/bash
# IPAM 启动脚本 (Linux/macOS)
# 使用方法: chmod +x run.sh && ./run.sh

set -e

echo "============================================"
echo "  IPAM - IP 地址管理系统"
echo "  启动中..."
echo "============================================"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 python3，请先安装 Python 3.8+"
    exit 1
fi

echo "[信息] 检测到: $(python3 --version)"

# 进入脚本目录
cd "$(dirname "$0")"

# 创建/激活虚拟环境
if [ ! -d "venv" ]; then
    echo "[信息] 创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

# 安装依赖
echo "[信息] 安装/更新依赖包..."
pip install --upgrade pip -q
pip install -r requirements.txt

# 初始化数据库
echo "[信息] 初始化数据库..."
python3 -c "from db import init_db; init_db(); print('数据库初始化完成')"

echo ""
echo "============================================"
echo "  启动 Web 服务..."
echo "  访问地址: http://localhost:5100"
echo "  按 Ctrl+C 停止服务"
echo "============================================"
echo ""

python3 app.py