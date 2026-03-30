' BIT-Nav 系统托盘启动器
' 启动 PowerShell 托盘程序（隐藏窗口）

Option Explicit

Dim objShell, objFSO, scriptPath, cmd

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录（launcher 文件夹）
scriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName) & "\BIT-Nav-Tray.ps1"

' 检查 PowerShell 脚本是否存在
If Not objFSO.FileExists(scriptPath) Then
    MsgBox "Cannot find: " & scriptPath, vbCritical, "Error"
    WScript.Quit 1
End If

' 构建命令（隐藏 PowerShell 窗口）
cmd = "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & scriptPath & """"

' 启动托盘程序
objShell.Run cmd, 0, False

' 清理
Set objShell = Nothing
Set objFSO = Nothing

WScript.Quit 0
