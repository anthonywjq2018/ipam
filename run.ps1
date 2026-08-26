# IPAM 启动脚本 (PowerShell)
# 右键 "使用 PowerShell 运行" 或在终端执行: .\run.ps1

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  IPAM - IP 地址管理系统" -ForegroundColor Green
Write-Host "  启动中..." -ForegroundColor Yellow
Write-Host "============================================`n" -ForegroundColor Cyan

# 检查 Python
try {
    $pyVersion = python --version 2>&1
    Write-Host "[信息] 检测到: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] 未检测到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

# 进入脚本目录
Set-Location $PSScriptRoot

# 创建/激活虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "[信息] 创建虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[警告] 创建虚拟环境失败，将使用系统 Python" -ForegroundColor Yellow
    }
}

if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[信息] 激活虚拟环境..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
}

# 安装依赖
Write-Host "[信息] 安装/更新依赖包..." -ForegroundColor Yellow
pip install --upgrade pip -q
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 依赖安装失败" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 初始化数据库
Write-Host "[信息] 初始化数据库..." -ForegroundColor Yellow
python -c "from db import init_db; init_db(); print('数据库初始化完成')"

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  启动 Web 服务..." -ForegroundColor Green
Write-Host "  访问地址: http://localhost:5100" -ForegroundColor Cyan
Write-Host "  按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host "============================================`n" -ForegroundColor Cyan

python app.py

Read-Host "`n按回车键退出"