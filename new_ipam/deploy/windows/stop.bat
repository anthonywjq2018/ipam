@echo off
REM IPAM Windows 停止脚本
REM 查找并终止运行 app.py 的 Python 进程

setlocal

echo 正在查找 IPAM 相关进程...

REM 使用 tasklist 查找 Python 进程，然后过滤命令行包含 app.py
for /f "tokens=1,2 delims=," %%a in ('
    wmic process where "name='python.exe'" get processid,commandline /format:csv
') do (
    if not "%%a"=="ProcessId" (
        set "PID=%%a"
        set "CMD=%%b"
        if not "!PID!"=="" if not "!CMD!"=="" if "!CMD:~0,1!" neq "" (
            echo !CMD! | findstr /i "app.py" >nul
            if not errorlevel 1 (
                echo 终止进程 !PID! (!CMD!)
                taskkill /PID !PID! /F >nul
            )
        )
    )
)

REM 也可以直接使用 taskkill 过滤镜像名和窗口标题（如果有）
REM 但上面的方法更可靠

echo 完成。
endlocal