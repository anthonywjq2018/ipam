@echo off
chcp 65001 >nul
title IPAM - IP 地址管理系统

echo ============================================
echo  IPAM - IP 地址管理系统
echo  启动中...
echo ============================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查 pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 pip
    pause
    exit /b 1
)

REM 进入脚本目录
cd /d "%~dp0"

REM 创建虚拟环境（可选，建议使用）
if not exist "venv" (
    echo [信息] 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [警告] 创建虚拟环境失败，将使用系统 Python
        goto :install_deps
    )
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

:install_deps
echo [信息] 安装依赖包...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络或手动运行: pip install -r requirements.txt
    pause
    exit /b 1
)

REM 初始化数据库
echo [信息] 初始化数据库...
python -c "from db import init_db; init_db(); print('数据库初始化完成')"

echo.
echo ============================================
echo  启动 Web 服务...
echo  访问地址: http://localhost:5100
echo  按 Ctrl+C 停止服务
echo ============================================
echo.

python app.py

pause