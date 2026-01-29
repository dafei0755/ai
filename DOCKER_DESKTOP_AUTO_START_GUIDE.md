# Docker Desktop 开机自启设置指南

**目标**: 配置 Docker Desktop 随 Windows 系统自动启动
**适用系统**: Windows 10/11
**所需时间**: 1-2 分钟

## 🎯 方法 1: Docker Desktop GUI 设置（推荐）

### 步骤详解

1. **启动 Docker Desktop**
   - 按 `Win` 键打开开始菜单
   - 搜索 "Docker Desktop"
   - 点击启动应用

2. **打开设置界面**
   - 等待 Docker Desktop 完全启动
   - 点击窗口右上角的 **⚙️ 齿轮图标**（Settings）

3. **配置自动启动**
   - 进入左侧菜单 **"General"** 标签
   - 找到并勾选 ✅ **"Start Docker Desktop when you log in"**
   - 点击右下角 **"Apply & Restart"** 按钮

4. **验证设置**
   - Docker Desktop 会自动重启
   - 重启完成后，设置即生效

### 图示参考

```
Docker Desktop Settings
├── General ← 选择这个标签
│   ├── ✅ Start Docker Desktop when you log in  ← 勾选此项
│   ├── □ Use the WSL 2 based engine
│   └── ...
├── Resources
├── Docker Engine
└── ...
```

### 测试验证

完成设置后，测试是否成功：

1. **重启计算机**
2. **检查 Docker 是否自动启动**
   ```powershell
   docker ps
   ```
   如果返回容器列表（即使为空），说明配置成功。

---

## 🔧 方法 2: Windows 任务计划程序（高级）

如果 GUI 设置不生效，可以使用 Windows 任务计划程序强制开机自启。

### 创建启动任务（管理员权限）

打开 PowerShell（管理员模式）并运行：

```powershell
# 创建开机启动任务
$Action = New-ScheduledTaskAction -Execute "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "DockerDesktopAutoStart" `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "自动启动 Docker Desktop"
```

### 验证任务

```powershell
# 查看任务是否创建成功
Get-ScheduledTask -TaskName "DockerDesktopAutoStart"
```

### 手动触发测试

```powershell
# 测试任务是否能正常运行
Start-ScheduledTask -TaskName "DockerDesktopAutoStart"
```

### 删除任务（如需要）

```powershell
Unregister-ScheduledTask -TaskName "DockerDesktopAutoStart" -Confirm:$false
```

---

## 🛠️ 方法 3: Windows 启动文件夹（简单但不推荐）

### 创建快捷方式

1. **打开启动文件夹**
   - 按 `Win + R` 打开运行对话框
   - 输入: `shell:startup`
   - 按 Enter

2. **创建 Docker Desktop 快捷方式**
   - 找到 Docker Desktop 安装路径（默认）:
     ```
     C:\Program Files\Docker\Docker\Docker Desktop.exe
     ```
   - 右键 → 发送到 → 桌面快捷方式
   - 将快捷方式移动到启动文件夹

### ⚠️ 局限性
- 可能需要手动点击 UAC 提示
- 不如方法 1 和方法 2 可靠

---

## 🚀 一键配置脚本

将以下内容保存为 `setup_docker_autostart.ps1`：

```powershell
# Docker Desktop 开机自启配置脚本
# 需要管理员权限运行

# 检查是否以管理员身份运行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ 请以管理员身份运行此脚本！" -ForegroundColor Red
    Write-Host "右键点击脚本 → 以管理员身份运行" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "🔧 正在配置 Docker Desktop 开机自启..." -ForegroundColor Cyan

# Docker Desktop 安装路径（根据实际情况调整）
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# 检查 Docker Desktop 是否已安装
if (-not (Test-Path $dockerPath)) {
    Write-Host "❌ 未找到 Docker Desktop，请检查安装路径" -ForegroundColor Red
    Write-Host "默认路径: $dockerPath" -ForegroundColor Yellow
    pause
    exit 1
}

try {
    # 删除已存在的任务（如果有）
    $existingTask = Get-ScheduledTask -TaskName "DockerDesktopAutoStart" -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "🗑️ 删除旧的启动任务..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName "DockerDesktopAutoStart" -Confirm:$false
    }

    # 创建新的启动任务
    $Action = New-ScheduledTaskAction -Execute $dockerPath
    $Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

    Register-ScheduledTask -TaskName "DockerDesktopAutoStart" `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description "开机自动启动 Docker Desktop" | Out-Null

    Write-Host "✅ Docker Desktop 开机自启配置成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 任务信息:" -ForegroundColor Cyan
    Get-ScheduledTask -TaskName "DockerDesktopAutoStart" | Format-List TaskName, State, Triggers

    Write-Host ""
    Write-Host "🎯 下次登录 Windows 时，Docker Desktop 将自动启动" -ForegroundColor Green
    Write-Host ""
    Write-Host "🧪 测试任务（可选）:" -ForegroundColor Yellow
    Write-Host "   Start-ScheduledTask -TaskName 'DockerDesktopAutoStart'" -ForegroundColor Gray

} catch {
    Write-Host "❌ 配置失败: $_" -ForegroundColor Red
    Write-Host "请尝试方法 1（GUI 设置）" -ForegroundColor Yellow
}

pause
```

### 运行脚本

```powershell
# 方法 A: 右键 → 以管理员身份运行 PowerShell
.\setup_docker_autostart.ps1

# 方法 B: 命令行
powershell -ExecutionPolicy Bypass -File .\setup_docker_autostart.ps1
```

---

## ✅ 验证清单

完成配置后，请检查以下项目：

- [ ] Docker Desktop GUI 设置中 "Start Docker Desktop when you log in" 已勾选
- [ ] 重启计算机后，Docker Desktop 自动启动
- [ ] 运行 `docker ps` 能正常返回结果
- [ ] 系统托盘显示 Docker 图标（鲸鱼图标）

---

## ❓ 常见问题

### Q1: 设置后 Docker Desktop 仍未自动启动

**可能原因**:
1. Windows 快速启动功能干扰
2. 杀毒软件阻止
3. Docker Desktop 版本过旧

**解决方法**:
```powershell
# 检查 Docker Desktop 进程
Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue

# 检查任务计划器中的任务
Get-ScheduledTask -TaskName "DockerDesktopAutoStart"
```

### Q2: UAC 弹窗阻止自动启动

**解决方法**: 使用方法 2（任务计划程序），配置 `-RunLevel Highest`

### Q3: 开机后 Docker Desktop 启动很慢

**优化方法**:
- 在任务计划程序中添加延迟启动（30 秒）
- 检查 Docker Desktop 资源配置

---

## 🔗 相关资源

- [Docker Desktop 官方文档](https://docs.docker.com/desktop/settings/windows/)
- [Windows 任务计划程序文档](https://docs.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page)
- [Milvus 启动失败诊断](MILVUS_STARTUP_FAILURE_DIAGNOSIS.md)

---

## 📞 进一步帮助

如果以上方法都不奏效，请检查：

1. **Windows 事件查看器**
   - 按 `Win + X` → 事件查看器
   - 查看 "应用程序" 和 "系统" 日志中的 Docker 相关错误

2. **Docker Desktop 日志**
   - 打开 Docker Desktop
   - 点击右上角 "Troubleshoot" 🐛
   - 查看日志文件

3. **系统启动项管理**
   ```powershell
   # 查看所有开机启动项
   Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location
   ```

---

**最后更新**: 2026-01-06
**适用版本**: Docker Desktop 4.0+, Windows 10/11
