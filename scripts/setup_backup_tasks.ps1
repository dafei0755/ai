# Windows Task Scheduler Configuration Script
# Purpose: Setup automatic backup tasks twice daily (10:00 AM and 6:00 PM)

# Check for administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Warning "This script requires administrator privileges!"
    Write-Host "Please right-click PowerShell and select 'Run as Administrator', then run this script again."
    pause
    exit
}

$ProjectRoot = "d:\11-20\langgraph-design"
$BackupScript = "$ProjectRoot\scripts\backup_project.bat"

# Check if backup script exists
if (-not (Test-Path $BackupScript)) {
    Write-Error "Backup script not found: $BackupScript"
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configure Project Auto-Backup Tasks" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Remove existing tasks if any
$TaskName1 = "ProjectBackup-Morning"
$TaskName2 = "ProjectBackup-Evening"

Write-Host "Checking and removing old tasks..." -ForegroundColor Yellow
Get-ScheduledTask -TaskName $TaskName1 -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue
Get-ScheduledTask -TaskName $TaskName2 -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue

# Create Task 1: Daily backup at 10:00 AM
Write-Host ""
Write-Host "[1/2] Creating morning backup task (Daily 10:00 AM)..." -ForegroundColor Green

$Action1 = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BackupScript`""
$Trigger1 = New-ScheduledTaskTrigger -Daily -At "10:00AM"
$Settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal1 = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName1 `
    -Action $Action1 `
    -Trigger $Trigger1 `
    -Settings $Settings1 `
    -Principal $Principal1 `
    -Description "Auto backup langgraph-design project files (Morning)" `
    -Force | Out-Null

Write-Host "Morning backup task created successfully" -ForegroundColor Green

# Create Task 2: Daily backup at 6:00 PM
Write-Host ""
Write-Host "[2/2] Creating evening backup task (Daily 6:00 PM)..." -ForegroundColor Green

$Action2 = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BackupScript`""
$Trigger2 = New-ScheduledTaskTrigger -Daily -At "6:00PM"
$Settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal2 = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName2 `
    -Action $Action2 `
    -Trigger $Trigger2 `
    -Settings $Settings2 `
    -Principal $Principal2 `
    -Description "Auto backup langgraph-design project files (Evening)" `
    -Force | Out-Null

Write-Host "Evening backup task created successfully" -ForegroundColor Green

# Verify tasks
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tasks configured successfully!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$Task1 = Get-ScheduledTask -TaskName $TaskName1
$Task2 = Get-ScheduledTask -TaskName $TaskName2

Write-Host "Created backup tasks:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Task 1: $TaskName1" -ForegroundColor White
Write-Host "  Status: $($Task1.State)" -ForegroundColor Gray
Write-Host "  Trigger: Daily 10:00 AM" -ForegroundColor Gray
Write-Host "  Next Run: $((Get-ScheduledTaskInfo -TaskName $TaskName1).NextRunTime)" -ForegroundColor Gray
Write-Host ""
Write-Host "Task 2: $TaskName2" -ForegroundColor White
Write-Host "  Status: $($Task2.State)" -ForegroundColor Gray
Write-Host "  Trigger: Daily 6:00 PM" -ForegroundColor Gray
Write-Host "  Next Run: $((Get-ScheduledTaskInfo -TaskName $TaskName2).NextRunTime)" -ForegroundColor Gray
Write-Host ""

# Test backup
Write-Host "Run a test backup now? (Y/N): " -ForegroundColor Yellow -NoNewline
$Response = Read-Host

if ($Response -eq "Y" -or $Response -eq "y") {
    Write-Host ""
    Write-Host "Running test backup..." -ForegroundColor Green
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$BackupScript`"" -Wait -NoNewWindow
    Write-Host ""
    Write-Host "Test backup completed! Check the backup\ directory" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backup Task Management Commands:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "View task status:" -ForegroundColor Yellow
Write-Host "  Get-ScheduledTask -TaskName 'ProjectBackup-*'" -ForegroundColor Gray
Write-Host ""
Write-Host "Run task manually:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName 'ProjectBackup-Morning'" -ForegroundColor Gray
Write-Host "  Start-ScheduledTask -TaskName 'ProjectBackup-Evening'" -ForegroundColor Gray
Write-Host ""
Write-Host "Disable task:" -ForegroundColor Yellow
Write-Host "  Disable-ScheduledTask -TaskName 'ProjectBackup-Morning'" -ForegroundColor Gray
Write-Host ""
Write-Host "Delete task:" -ForegroundColor Yellow
Write-Host "  Unregister-ScheduledTask -TaskName 'ProjectBackup-Morning' -Confirm:`$false" -ForegroundColor Gray
Write-Host ""

pause
