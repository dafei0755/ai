# 创建紧急恢复桌面快捷方式
# 以管理员权限运行 PowerShell 并执行此脚本

$ProjectRoot = "D:\11-20\langgraph-design"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "🚨紧急恢复-历史版本.lnk"

# 创建 WScript.Shell COM 对象
$WScriptShell = New-Object -ComObject WScript.Shell

# 创建快捷方式
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $ProjectRoot "emergency_restore.bat"
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "程序出错？立即恢复到历史版本！"
$Shortcut.IconLocation = "shell32.dll,21" # 急救箱图标
$Shortcut.Save()

Write-Host "✓ 桌面快捷方式创建成功！" -ForegroundColor Green
Write-Host "  位置: $ShortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "使用方法:" -ForegroundColor Yellow
Write-Host "  双击桌面上的 '🚨紧急恢复-历史版本' 图标" -ForegroundColor White
Write-Host "  即可快速恢复到任意历史版本！" -ForegroundColor White
Write-Host ""

pause
