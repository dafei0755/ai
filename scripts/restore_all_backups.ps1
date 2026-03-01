[CmdletBinding()]
param(
    [string]$SourceRoot = 'D:\11-20\langgraph-design',
    [string]$TargetRoot = 'D:\11-20',
    [bool]$IncludeData = $true,
    [bool]$InstallDeps = $true
)

$ErrorActionPreference = 'Stop'

$backupRoot = Join-Path -Path $SourceRoot -ChildPath 'backup'
$manifestPath = Join-Path -Path $TargetRoot -ChildPath 'restore_manifest.json'

$restoreMap = @(
    [PSCustomObject]@{ Source = 'auto_backup_周二022602_180001'; Target = 'langgraph-v4-0224-1800'; BackupTime = '2026-02-24 18:00:10'; Version = 'v7.502' },
    [PSCustomObject]@{ Source = 'auto_backup_周三022602_180001'; Target = 'langgraph-v5-0225-1800'; BackupTime = '2026-02-25 18:01:06'; Version = 'v7.502' },
    [PSCustomObject]@{ Source = 'auto_backup_周三022602_100002'; Target = 'langgraph-v6-0225-1000'; BackupTime = '2026-02-25 10:00:42'; Version = 'v7.502' },
    [PSCustomObject]@{ Source = 'auto_backup_20260226_100002'; Target = 'langgraph-v7-0226-1000'; BackupTime = '2026-02-26 10:00:30'; Version = 'v7.122' }
)

$requiredDirs = @('python', 'frontend', 'config', 'docs', 'data')
$requiredFiles = @('config\\.env', 'config\\requirements.txt', 'config\\package.json')

function Copy-DirContent {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,
        [Parameter(Mandatory = $true)][string]$TargetDir
    )

    if (!(Test-Path -LiteralPath $SourceDir)) {
        throw "Source directory does not exist: $SourceDir"
    }

    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

    Get-ChildItem -LiteralPath $SourceDir -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $TargetDir -Recurse -Force
    }
}

function Test-BackupCompleteness {
    param([Parameter(Mandatory = $true)][string]$BackupDir)

    $missing = @()

    foreach ($dir in $requiredDirs) {
        $path = Join-Path -Path $BackupDir -ChildPath $dir
        if (!(Test-Path -LiteralPath $path)) {
            $missing += $dir
        }
    }

    foreach ($fileRel in $requiredFiles) {
        $path = Join-Path -Path $BackupDir -ChildPath $fileRel
        if (!(Test-Path -LiteralPath $path)) {
            $missing += $fileRel
        }
    }

    return $missing
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][ScriptBlock]$Script,
        [Parameter(Mandatory = $true)][string]$Description
    )

    & $Script
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

if (!(Test-Path -LiteralPath $backupRoot)) {
    throw "Backup root not found: $backupRoot"
}

$manifest = [ordered]@{
    generated_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    source_root = $SourceRoot
    backup_root = $backupRoot
    target_root = $TargetRoot
    include_data = $IncludeData
    install_deps = $InstallDeps
    entries = @()
}

foreach ($item in $restoreMap) {
    $startTime = Get-Date
    $sourceBackup = Join-Path -Path $backupRoot -ChildPath $item.Source
    $targetProject = Join-Path -Path $TargetRoot -ChildPath $item.Target

    $entry = [ordered]@{
        source_backup = $item.Source
        target_project = $targetProject
        version = $item.Version
        backup_time = $item.BackupTime
        started_at = $startTime.ToString('yyyy-MM-ddTHH:mm:ssK')
        status = 'pending'
        include_data = $IncludeData
        install_deps = $InstallDeps
        file_count = 0
        patch_bytes = 0
        error = $null
    }

    try {
        if (Test-Path -LiteralPath $targetProject) {
            $entry.status = 'skipped_exists'
            $entry.error = 'Target directory already exists'
            $entry.completed_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
            $manifest.entries += [PSCustomObject]$entry
            Write-Host "[SKIP] $targetProject already exists"
            continue
        }

        if (!(Test-Path -LiteralPath $sourceBackup)) {
            $entry.status = 'failed_validation'
            $entry.error = "Source backup not found: $sourceBackup"
            $entry.completed_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
            $manifest.entries += [PSCustomObject]$entry
            Write-Host "[FAIL] Source not found: $sourceBackup"
            continue
        }

        $missingItems = Test-BackupCompleteness -BackupDir $sourceBackup
        if ($missingItems.Count -gt 0) {
            $entry.status = 'failed_validation'
            $entry.error = "Missing required items: $($missingItems -join ', ')"
            $entry.completed_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
            $manifest.entries += [PSCustomObject]$entry
            Write-Host "[FAIL] Missing required items in $($item.Source): $($missingItems -join ', ')"
            continue
        }

        New-Item -ItemType Directory -Path $targetProject -Force | Out-Null
        New-Item -ItemType Directory -Path (Join-Path -Path $targetProject -ChildPath 'intelligent_project_analyzer') -Force | Out-Null
        New-Item -ItemType Directory -Path (Join-Path -Path $targetProject -ChildPath 'frontend-nextjs') -Force | Out-Null

        Copy-DirContent -SourceDir (Join-Path -Path $sourceBackup -ChildPath 'python') -TargetDir (Join-Path -Path $targetProject -ChildPath 'intelligent_project_analyzer')
        Copy-DirContent -SourceDir (Join-Path -Path $sourceBackup -ChildPath 'frontend') -TargetDir (Join-Path -Path $targetProject -ChildPath 'frontend-nextjs')
        Copy-DirContent -SourceDir (Join-Path -Path $sourceBackup -ChildPath 'docs') -TargetDir $targetProject

        if ($IncludeData) {
            Copy-DirContent -SourceDir (Join-Path -Path $sourceBackup -ChildPath 'data') -TargetDir (Join-Path -Path $targetProject -ChildPath 'data')
        }

        $configRoot = Join-Path -Path $sourceBackup -ChildPath 'config'
        Copy-Item -LiteralPath (Join-Path -Path $configRoot -ChildPath '.env') -Destination (Join-Path -Path $targetProject -ChildPath '.env') -Force
        Copy-Item -LiteralPath (Join-Path -Path $configRoot -ChildPath 'requirements.txt') -Destination (Join-Path -Path $targetProject -ChildPath 'requirements.txt') -Force
        Copy-Item -LiteralPath (Join-Path -Path $configRoot -ChildPath 'package.json') -Destination (Join-Path -Path $targetProject -ChildPath 'frontend-nextjs\\package.json') -Force

        if (Test-Path -LiteralPath (Join-Path -Path $configRoot -ChildPath '.env.local')) {
            Copy-Item -LiteralPath (Join-Path -Path $configRoot -ChildPath '.env.local') -Destination (Join-Path -Path $targetProject -ChildPath 'frontend-nextjs\\.env.local') -Force
        }

        if (Test-Path -LiteralPath (Join-Path -Path $configRoot -ChildPath 'analyzer')) {
            Copy-DirContent -SourceDir (Join-Path -Path $configRoot -ChildPath 'analyzer') -TargetDir (Join-Path -Path $targetProject -ChildPath 'intelligent_project_analyzer\\config')
        }

        $metaDir = Join-Path -Path $targetProject -ChildPath '_restore_meta'
        New-Item -ItemType Directory -Path $metaDir -Force | Out-Null

        foreach ($metaFile in @('BACKUP_INFO.txt', 'git_log.txt', 'git_status.txt', 'git_diff.patch')) {
            $metaSource = Join-Path -Path $sourceBackup -ChildPath $metaFile
            if (Test-Path -LiteralPath $metaSource) {
                Copy-Item -LiteralPath $metaSource -Destination (Join-Path -Path $metaDir -ChildPath $metaFile) -Force
            }
        }

        if ($InstallDeps) {
            $env:PIP_NO_CACHE_DIR = '1'

            Push-Location $targetProject
            try {
                Invoke-CheckedCommand -Description 'python -m venv .venv' -Script { python -m venv .venv }

                $venvPython = Join-Path -Path $targetProject -ChildPath '.venv\\Scripts\\python.exe'
                Invoke-CheckedCommand -Description 'pip install --upgrade pip' -Script { & $venvPython -m pip install --no-cache-dir --upgrade pip }
                Invoke-CheckedCommand -Description 'pip install -r requirements.txt' -Script { & $venvPython -m pip install --no-cache-dir -r (Join-Path -Path $targetProject -ChildPath 'requirements.txt') }
            }
            finally {
                Pop-Location
            }

            Push-Location (Join-Path -Path $targetProject -ChildPath 'frontend-nextjs')
            try {
                Invoke-CheckedCommand -Description 'npm install' -Script { npm install }
            }
            finally {
                Pop-Location
            }
        }

        $patchPath = Join-Path -Path $sourceBackup -ChildPath 'git_diff.patch'
        if (Test-Path -LiteralPath $patchPath) {
            $entry.patch_bytes = (Get-Item -LiteralPath $patchPath).Length
        }

        $entry.file_count = (Get-ChildItem -LiteralPath $targetProject -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
        $entry.status = 'success'
        $entry.completed_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')

        Write-Host "[OK] Restored $($item.Source) -> $targetProject"
    }
    catch {
        $entry.status = 'failed'
        $entry.error = $_.Exception.Message
        $entry.completed_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
        Write-Host "[FAIL] $($item.Source): $($_.Exception.Message)"
    }

    $manifest.entries += [PSCustomObject]$entry
}

$manifestJson = $manifest | ConvertTo-Json -Depth 8
Set-Content -Path $manifestPath -Value $manifestJson -Encoding UTF8

$successCount = @($manifest.entries | Where-Object { $_.status -eq 'success' }).Count
$skipCount = @($manifest.entries | Where-Object { $_.status -eq 'skipped_exists' }).Count
$failCount = @($manifest.entries | Where-Object { $_.status -like 'failed*' }).Count

Write-Host ''
Write-Host '========================================'
Write-Host 'Restore complete'
Write-Host "Manifest: $manifestPath"
Write-Host "Success:  $successCount"
Write-Host "Skipped:  $skipCount"
Write-Host "Failed:   $failCount"
Write-Host '========================================'
