@echo off
REM IPAM Windows 启动脚本
REM 检查并创建虚拟环境，安装依赖，启动应用

setlocal

REM 设置工作目录为批处理文件所在目录的上两级（即 IPAM 根目录）
cd /d "%~dp0..\.."

REM 检查 Python 是否可用
where python >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+ 并确保其在 PATH 中
    pause
    exit /b 1
)

REM 虚拟环境目录
set "VENV_DIR=%cd%\venv"

REM 如果虚拟环境不存在，则创建
if not exist "%VENV_DIR%" (
    echo 创建虚拟环境...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo 错误: 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
call "%VENV_DIR%\Scripts\activate.bat"

REM 升级 pip
pip install --upgrade pip >nul

REM 安装依赖
if exist requirements.txt (
    echo 安装依赖...
    pip install -r requirements.txt >nul
    if errorlevel 1 (
        echo 错误: 安装依赖失败
        pause
        exit /b 1
    )
) else (
    echo 警告: 未找到 requirements.txt
)

REM 设置环境变量（可根据需要修改）
set "DB_TYPE=sqlite"
set "HOST=0.0.0.0"
set "PORT=5100"
set "DEBUG=false"
REM 生成一个随机密钥（仅在首次运行时设置，实际应用中应保持一致）
if not exist "%cd%\data\secret.key" (
    for /f "usebackq delims=" %%k in (`powershell -command "[byte[]]::new(32) | ForEach-Object { '{0:x2}' -f $_ } -join ''"`) do (
        echo %%k > "%cd%\data\secret.key"
    )
)
set /p SECRET_KEY=<"%cd%\data\secret.key"

REM 确保数据目录存在
if not exist "%cd%\data" mkdir "%cd%\data"
if not exist "%cd%\data\backups" mkdir "%cd%\data\backups"

REM 启动应用
echo 启动 IPAM 系统...
echo 访问地址: http://localhost:%PORT%
echo.
python app.py

REM 保持窗口打开以便查看日志（如果需要自动关闭可删除 pause）
pause
endlocal