@echo off
chcp 65001 >nul
title BIT-Nav 托盘启动器

echo ========================================
echo    BIT-Nav 系统托盘管理器
echo ========================================
echo.

:: 获取当前目录
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%BIT-Nav-Tray.ps1"

echo PowerShell 脚本路径: %PS_SCRIPT%
echo.

:: 检查脚本是否存在
if not exist "%PS_SCRIPT%" (
    echo [错误] 找不到托盘程序: %PS_SCRIPT%
    pause
    exit /b 1
)

echo [信息] 正在启动托盘程序...
echo.

:: 启动 PowerShell（隐藏窗口）
start /min powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

echo [信息] 托盘程序已启动
echo [提示] 查看任务栏右下角系统托盘
echo.
timeout /t 3 /nobreak >nul
