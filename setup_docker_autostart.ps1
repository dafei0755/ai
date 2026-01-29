# Docker Desktop 开机自启配置脚本
# 需要管理员权限运行
# 使用方法: 右键 → 以管理员身份运行 PowerShell → .\setup_docker_autostart.ps1

# 检查是否以管理员身份运行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ 请以管理员身份运行此脚本！" -ForegroundColor Red
    Write-Host "右键点击脚本 → 以管理员身份运行" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "🔧 正在配置 Docker Desktop 开机自启..." -ForegroundColor Cyan
Write-Host ""

# Docker Desktop 安装路径（根据实际情况调整）
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# 检查 Docker Desktop 是否已安装
if (-not (Test-Path $dockerPath)) {
    Write-Host "❌ 未找到 Docker Desktop，请检查安装路径" -ForegroundColor Red
    Write-Host "默认路径: $dockerPath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "如果 Docker Desktop 安装在其他位置，请编辑此脚本修改路径" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✅ 找到 Docker Desktop: $dockerPath" -ForegroundColor Green
Write-Host ""

try {
    # 删除已存在的任务（如果有）
    $existingTask = Get-ScheduledTask -TaskName "DockerDesktopAutoStart" -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "🗑️ 删除旧的启动任务..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName "DockerDesktopAutoStart" -Confirm:$false
        Write-Host "✅ 旧任务已删除" -ForegroundColor Green
        Write-Host ""
    }

    # 创建新的启动任务
    Write-Host "📝 创建新的开机启动任务..." -ForegroundColor Cyan

    $Action = New-ScheduledTaskAction -Execute $dockerPath
    $Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 0)

    Register-ScheduledTask -TaskName "DockerDesktopAutoStart" `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description "开机自动启动 Docker Desktop" | Out-Null

    Write-Host "✅ Docker Desktop 开机自启配置成功！" -ForegroundColor Green
    Write-Host ""

    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "📝 任务信息:" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    $task = Get-ScheduledTask -TaskName "DockerDesktopAutoStart"
    Write-Host "任务名称: $($task.TaskName)" -ForegroundColor White
    Write-Host "状态    : $($task.State)" -ForegroundColor White
    Write-Host "触发器  : 用户登录时" -ForegroundColor White
    Write-Host "执行程序: $dockerPath" -ForegroundColor White
    Write-Host ""

    Write-Host "🎯 效果: 下次登录 Windows 时，Docker Desktop 将自动启动" -ForegroundColor Green
    Write-Host ""

    Write-Host "🧪 测试任务（可选）:" -ForegroundColor Yellow
    Write-Host "   1. 运行以下命令测试任务是否能正常执行:" -ForegroundColor Gray
    Write-Host "      Start-ScheduledTask -TaskName 'DockerDesktopAutoStart'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   2. 或者直接重启计算机验证" -ForegroundColor Gray
    Write-Host ""

    Write-Host "✅ 配置完成！" -ForegroundColor Green

} catch {
    Write-Host "❌ 配置失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "建议使用 GUI 方法:" -ForegroundColor Yellow
    Write-Host "1. 启动 Docker Desktop" -ForegroundColor Gray
    Write-Host "2. 点击右上角齿轮图标（Settings）" -ForegroundColor Gray
    Write-Host "3. 进入 General 标签" -ForegroundColor Gray
    Write-Host "4. 勾选 'Start Docker Desktop when you log in'" -ForegroundColor Gray
    Write-Host "5. 点击 'Apply & Restart'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "详细指南: DOCKER_DESKTOP_AUTO_START_GUIDE.md" -ForegroundColor Cyan
}

Write-Host ""
pause
