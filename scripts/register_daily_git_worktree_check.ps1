param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$TaskName = 'LangGraphDesignDailyGitWorktreeCheck',
    [string]$DailyAt = '09:20'
)

$ErrorActionPreference = 'Stop'

$repo = Resolve-Path -LiteralPath $RepoRoot
$scriptPath = Join-Path $repo.Path 'scripts/daily_git_worktree_check.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$time = [datetime]::ParseExact($DailyAt, 'HH:mm', [System.Globalization.CultureInfo]::InvariantCulture)
$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -RepoRoot `"$($repo.Path)`"" `
    -WorkingDirectory $repo.Path
$trigger = New-ScheduledTaskTrigger -Daily -At $time
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description 'Daily report-only Git worktree health check for langgraph-design.' `
    -Force | Out-Null

Write-Output "Registered task: $TaskName"
Write-Output "DailyAt: $DailyAt"
Write-Output "Script: $scriptPath"