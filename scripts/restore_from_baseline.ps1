[CmdletBinding()]
param(
    [string]$BaselineRoot = 'D:\11-20\langgraph-design',
    [string]$TargetRoot = 'D:\11-20',
    [ValidateSet('runnable','strict')]
    [string]$Mode = 'runnable',
    [bool]$IncludeData = $true,
    [bool]$InstallDeps = $true,
    [bool]$InstallPostgresDriver = $true,
    [bool]$InstallBrowserDeps = $false
)

$ErrorActionPreference = 'Stop'

$backupRoot = Join-Path -Path $BaselineRoot -ChildPath 'backup'
$manifestPath = Join-Path -Path $TargetRoot -ChildPath 'restore_manifest_baseline.json'

$restoreMap = @(
    [PSCustomObject]@{ Source = 'auto_backup_周二022602_180001'; Target = 'langgraph-v4-0224-1800'; BackupTime = '2026-02-24 18:00:10'; Version = 'v7.502'; BackendPort = 8104; FrontendPort = 3104 },
    [PSCustomObject]@{ Source = 'auto_backup_周三022602_180001'; Target = 'langgraph-v5-0225-1800'; BackupTime = '2026-02-25 18:01:06'; Version = 'v7.502'; BackendPort = 8105; FrontendPort = 3105 },
    [PSCustomObject]@{ Source = 'auto_backup_周三022602_100002'; Target = 'langgraph-v6-0225-1000'; BackupTime = '2026-02-25 10:00:42'; Version = 'v7.502'; BackendPort = 8106; FrontendPort = 3106 },
    [PSCustomObject]@{ Source = 'auto_backup_20260226_100002'; Target = 'langgraph-v7-0226-1000'; BackupTime = '2026-02-26 10:00:30'; Version = 'v7.122'; BackendPort = 8107; FrontendPort = 3107 },
    [PSCustomObject]@{ Source = 'auto_backup_20260226_100002'; Target = 'langgraph-v8-0226-1000'; BackupTime = '2026-02-26 10:00:30'; Version = 'v7.122'; BackendPort = 8108; FrontendPort = 3108 },
    [PSCustomObject]@{ Source = 'auto_backup_周四022602_180001'; Target = 'langgraph-v9-0226-1800'; BackupTime = '2026-02-26 18:00:15'; Version = 'v7.122'; BackendPort = 8109; FrontendPort = 3109 }
)

$requiredDirs = @('python', 'frontend', 'config', 'docs', 'data')
$requiredFiles = @('config\\.env', 'config\\requirements.txt', 'config\\package.json')

$baselineExcludes = @(
    '.git', 'backup', 'node_modules', '.venv', 'venv', '.next',
    '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    'htmlcov', 'logs', 'dist', '.benchmarks'
)

function Invoke-Robocopy {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination,
        [string[]]$ExcludeDirs = @(),
        [string[]]$ExcludeFiles = @()
    )

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null

    $args = @($Source, $Destination, '/E', '/R:1', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP')

    if ($ExcludeDirs.Count -gt 0) {
        $args += '/XD'
        $args += $ExcludeDirs
    }
    if ($ExcludeFiles.Count -gt 0) {
        $args += '/XF'
        $args += $ExcludeFiles
    }

    & robocopy @args | Out-Null
    $rc = $LASTEXITCODE
    if ($rc -gt 7) {
        throw "robocopy failed ($rc): $Source -> $Destination"
    }
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

function Get-BaselinePython {
    param([Parameter(Mandatory = $true)][string]$ProjectRoot)

    $candidate = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $candidate) {
        return $candidate
    }

    return 'python'
}

function Get-BaselinePackageVersion {
    param(
        [Parameter(Mandatory = $true)][string]$PythonExe,
        [Parameter(Mandatory = $true)][string]$PackageName
    )

    $code = @"
import importlib.metadata as md
try:
    print(md.version("$PackageName"))
except Exception:
    print("")
"@
    $version = & $PythonExe -c $code
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to detect version for package: $PackageName"
    }

    return ($version | Out-String).Trim()
}

function Install-CompatibilityPackages {
    param(
        [Parameter(Mandatory = $true)][string]$BaselinePython,
        [Parameter(Mandatory = $true)][string]$VenvPython,
        [bool]$InstallPostgresDriver = $true,
        [bool]$InstallBrowserDeps = $false
    )

    $runtimePackages = @('fpdf2', 'playwright', 'PyJWT', 'python-multipart')
    if ($InstallPostgresDriver) {
        $runtimePackages += 'psycopg2-binary'
    }

    Invoke-CheckedCommand -Description 'pip install runtime support packages' -Script {
        & $VenvPython -m pip install --no-cache-dir @runtimePackages
    }

    $langgraphPackages = @(
        'langgraph',
        'langgraph-checkpoint',
        'langgraph-checkpoint-sqlite',
        'langgraph-prebuilt',
        'langgraph-sdk'
    )

    $pins = @()
    foreach ($pkg in $langgraphPackages) {
        $version = Get-BaselinePackageVersion -PythonExe $BaselinePython -PackageName $pkg
        if ([string]::IsNullOrWhiteSpace($version)) {
            throw "Baseline package not installed: $pkg"
        }
        $pins += "$pkg==$version"
    }

    Invoke-CheckedCommand -Description 'pip install pinned langgraph packages' -Script {
        & $VenvPython -m pip install --no-cache-dir @pins
    }

    if ($InstallBrowserDeps) {
        Invoke-CheckedCommand -Description 'playwright install chromium' -Script {
            & $VenvPython -m playwright install chromium
        }
    }
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$EnvFile,
        [Parameter(Mandatory = $true)][string]$Key
    )

    if (!(Test-Path -LiteralPath $EnvFile)) {
        return $null
    }

    $match = Select-String -Path $EnvFile -Pattern "^\s*$Key=(.+)$" -SimpleMatch:$false | Select-Object -First 1
    if ($null -eq $match) {
        return $null
    }

    return $match.Matches[0].Groups[1].Value.Trim()
}

function Write-DatabaseWarning {
    param([Parameter(Mandatory = $true)][string]$ProjectRoot)

    $envPath = Join-Path $ProjectRoot '.env'
    $databaseUrl = Get-EnvValue -EnvFile $envPath -Key 'DATABASE_URL'
    $externalDbUrl = Get-EnvValue -EnvFile $envPath -Key 'EXTERNAL_DB_URL'

    $warning = @(
        'PostgreSQL configuration check'
        "Project: $ProjectRoot"
        "DATABASE_URL=$databaseUrl"
        "EXTERNAL_DB_URL=$externalDbUrl"
        ''
        'Warning: restored projects are isolated in filesystem only.'
        'If multiple restored projects use the same PostgreSQL database names, their runtime data will mix.'
        'Recommended: assign unique database names per restored project before side-by-side testing.'
    ) -join "`r`n"

    Set-Content -Path (Join-Path $ProjectRoot '_restore_meta\db_config_warning.txt') -Value $warning -Encoding UTF8
}

function Set-ProjectDatabaseUrls {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$ProjectName
    )

    $envPath = Join-Path $ProjectRoot '.env'
    if (!(Test-Path -LiteralPath $envPath)) {
        return
    }

    $suffix = $null
    if ($ProjectName -match '^langgraph-v(\d+)-') {
        $suffix = "v$($Matches[1])"
    }
    if ([string]::IsNullOrWhiteSpace($suffix)) {
        return
    }

    $content = Get-Content -Raw -Encoding UTF8 $envPath
    $content = [regex]::Replace($content, '^DATABASE_URL=.*$', "DATABASE_URL=postgresql://postgres:password@localhost:5432/project_analyzer_$suffix", 'Multiline')
    $content = [regex]::Replace($content, '^EXTERNAL_DB_URL=.*$', "EXTERNAL_DB_URL=postgresql://postgres:password@localhost:5432/external_projects_$suffix", 'Multiline')
    Set-Content -Path $envPath -Value $content -Encoding UTF8

    $mapping = @(
        'Restored project database mapping'
        "ProjectRoot=$ProjectRoot"
        "DATABASE_URL=postgresql://postgres:password@localhost:5432/project_analyzer_$suffix"
        "EXTERNAL_DB_URL=postgresql://postgres:password@localhost:5432/external_projects_$suffix"
    ) -join "`r`n"

    Set-Content -Path (Join-Path $ProjectRoot '_restore_meta\db_mapping.txt') -Value $mapping -Encoding UTF8
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

function Write-BackendWrapper {
    param([Parameter(Mandatory = $true)][string]$ProjectRoot)

    $wrapper = @"
@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d %~dp0
call .venv\Scripts\python.exe scripts\run_server_production.py
"@
    Set-Content -Path (Join-Path $ProjectRoot 'start_backend_restored.bat') -Value $wrapper -Encoding ASCII
}

function Write-CompareStartScripts {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][int]$BackendPort,
        [Parameter(Mandatory = $true)][int]$FrontendPort
    )

    $backendPy = @"
import asyncio
import sys
from pathlib import Path
import uvicorn

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

if sys.platform == "win32" and sys.version_info >= (3, 13):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

uvicorn.run(
    "intelligent_project_analyzer.api.server:app",
    host="127.0.0.1",
    port=$BackendPort,
    reload=False,
    log_level="info",
    workers=1,
)
"@
    Set-Content -Path (Join-Path $ProjectRoot 'scripts\run_server_compare.py') -Value $backendPy -Encoding ASCII

    $backendScript = @"
@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d %~dp0
call .venv\Scripts\python.exe scripts\run_server_compare.py
"@
    Set-Content -Path (Join-Path $ProjectRoot 'start_backend_compare.bat') -Value $backendScript -Encoding ASCII

    $frontendDir = Join-Path $ProjectRoot 'frontend-nextjs'
    $frontendScript = @"
@echo off
chcp 65001 >nul
cd /d %~dp0frontend-nextjs
set NEXT_PUBLIC_API_URL=http://127.0.0.1:$BackendPort
call .\node_modules\.bin\next.cmd dev -p $FrontendPort
"@
    Set-Content -Path (Join-Path $ProjectRoot 'start_frontend_compare.bat') -Value $frontendScript -Encoding ASCII

    $envLocalPath = Join-Path $frontendDir '.env.local'
    if (Test-Path -LiteralPath $envLocalPath) {
        $envLocal = Get-Content -Raw -Encoding UTF8 $envLocalPath
        if ($envLocal -match '^NEXT_PUBLIC_API_URL=') {
            $envLocal = [regex]::Replace($envLocal, '^NEXT_PUBLIC_API_URL=.*$', "NEXT_PUBLIC_API_URL=http://127.0.0.1:$BackendPort", 'Multiline')
        } else {
            $envLocal = "NEXT_PUBLIC_API_URL=http://127.0.0.1:$BackendPort`r`n$envLocal"
        }
        Set-Content -Path $envLocalPath -Value $envLocal -Encoding UTF8
    }

    $mapping = @(
        'Comparison port mapping'
        "BackendPort=$BackendPort"
        "FrontendPort=$FrontendPort"
        "FrontendUrl=http://127.0.0.1:$FrontendPort"
        "BackendUrl=http://127.0.0.1:$BackendPort"
        'StartBackend=start_backend_compare.bat'
        'StartFrontend=start_frontend_compare.bat'
    ) -join "`r`n"
    Set-Content -Path (Join-Path $ProjectRoot '_restore_meta\port_mapping.txt') -Value $mapping -Encoding UTF8
}

if (!(Test-Path -LiteralPath $BaselineRoot)) {
    throw "Baseline root not found: $BaselineRoot"
}
if (!(Test-Path -LiteralPath $backupRoot)) {
    throw "Backup root not found: $backupRoot"
}

$baselinePython = Get-BaselinePython -ProjectRoot $BaselineRoot

$manifest = [ordered]@{
    generated_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    baseline_root = $BaselineRoot
    backup_root = $backupRoot
    target_root = $TargetRoot
    mode = $Mode
    include_data = $IncludeData
    install_deps = $InstallDeps
    install_postgres_driver = $InstallPostgresDriver
    install_browser_deps = $InstallBrowserDeps
    entries = @()
}

foreach ($item in $restoreMap) {
    $sourceBackup = Join-Path -Path $backupRoot -ChildPath $item.Source
    $targetProject = Join-Path -Path $TargetRoot -ChildPath $item.Target

    $entry = [ordered]@{
        source_backup = $item.Source
        target_project = $targetProject
        version = $item.Version
        backup_time = $item.BackupTime
        mode = $Mode
        started_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
        status = 'pending'
        file_count = 0
        patch_bytes = 0
        error = $null
    }

    try {
        if (!(Test-Path -LiteralPath $sourceBackup)) {
            throw "Source backup not found: $sourceBackup"
        }

        $missingItems = Test-BackupCompleteness -BackupDir $sourceBackup
        if ($missingItems.Count -gt 0) {
            throw "Missing required items in backup: $($missingItems -join ', ')"
        }

        New-Item -ItemType Directory -Path $targetProject -Force | Out-Null

        Invoke-Robocopy -Source $BaselineRoot -Destination $targetProject -ExcludeDirs $baselineExcludes
        Invoke-Robocopy -Source (Join-Path $sourceBackup 'python') -Destination (Join-Path $targetProject 'intelligent_project_analyzer')
        Invoke-Robocopy -Source (Join-Path $sourceBackup 'frontend') -Destination (Join-Path $targetProject 'frontend-nextjs')
        Invoke-Robocopy -Source (Join-Path $sourceBackup 'docs') -Destination $targetProject
        Invoke-Robocopy -Source (Join-Path $sourceBackup 'config\\analyzer') -Destination (Join-Path $targetProject 'intelligent_project_analyzer\\config')

        if ($IncludeData) {
            Invoke-Robocopy -Source (Join-Path $sourceBackup 'data') -Destination (Join-Path $targetProject 'data')
        }

        $configRoot = Join-Path -Path $sourceBackup -ChildPath 'config'

        if ($Mode -eq 'strict') {
            Copy-Item -LiteralPath (Join-Path $configRoot '.env') -Destination (Join-Path $targetProject '.env') -Force
            Copy-Item -LiteralPath (Join-Path $configRoot 'requirements.txt') -Destination (Join-Path $targetProject 'requirements.txt') -Force
            Copy-Item -LiteralPath (Join-Path $configRoot 'package.json') -Destination (Join-Path $targetProject 'frontend-nextjs\\package.json') -Force
            if (Test-Path -LiteralPath (Join-Path $configRoot '.env.local')) {
                Copy-Item -LiteralPath (Join-Path $configRoot '.env.local') -Destination (Join-Path $targetProject 'frontend-nextjs\\.env.local') -Force
            }
        } else {
            if (!(Test-Path -LiteralPath (Join-Path $targetProject '.env'))) {
                Copy-Item -LiteralPath (Join-Path $configRoot '.env') -Destination (Join-Path $targetProject '.env') -Force
            }
            if (!(Test-Path -LiteralPath (Join-Path $targetProject 'requirements.txt'))) {
                Copy-Item -LiteralPath (Join-Path $configRoot 'requirements.txt') -Destination (Join-Path $targetProject 'requirements.txt') -Force
            }
            if (!(Test-Path -LiteralPath (Join-Path $targetProject 'frontend-nextjs\\package.json'))) {
                Copy-Item -LiteralPath (Join-Path $configRoot 'package.json') -Destination (Join-Path $targetProject 'frontend-nextjs\\package.json') -Force
            }
            if (!(Test-Path -LiteralPath (Join-Path $targetProject 'frontend-nextjs\\.env.local')) -and (Test-Path -LiteralPath (Join-Path $configRoot '.env.local'))) {
                Copy-Item -LiteralPath (Join-Path $configRoot '.env.local') -Destination (Join-Path $targetProject 'frontend-nextjs\\.env.local') -Force
            }
        }

        $metaDir = Join-Path -Path $targetProject -ChildPath '_restore_meta'
        New-Item -ItemType Directory -Path $metaDir -Force | Out-Null

        foreach ($metaFile in @('BACKUP_INFO.txt', 'git_log.txt', 'git_status.txt', 'git_diff.patch')) {
            $metaSource = Join-Path -Path $sourceBackup -ChildPath $metaFile
            if (Test-Path -LiteralPath $metaSource) {
                Copy-Item -LiteralPath $metaSource -Destination (Join-Path -Path $metaDir -ChildPath $metaFile) -Force
            }
        }

        New-Item -ItemType Directory -Path (Join-Path $metaDir 'backup_config_snapshot') -Force | Out-Null
        foreach ($cfg in @('.env', '.env.example', '.env.local', 'requirements.txt', 'package.json')) {
            $cfgSource = Join-Path $configRoot $cfg
            if (Test-Path -LiteralPath $cfgSource) {
                Copy-Item -LiteralPath $cfgSource -Destination (Join-Path $metaDir 'backup_config_snapshot') -Force
            }
        }

        Set-ProjectDatabaseUrls -ProjectRoot $targetProject -ProjectName $item.Target
        Write-DatabaseWarning -ProjectRoot $targetProject

        Write-BackendWrapper -ProjectRoot $targetProject
        Write-CompareStartScripts -ProjectRoot $targetProject -BackendPort $item.BackendPort -FrontendPort $item.FrontendPort

        if ($InstallDeps) {
            $env:PIP_NO_CACHE_DIR = '1'
            $venvPython = Join-Path -Path $targetProject -ChildPath '.venv\\Scripts\\python.exe'

            if (!(Test-Path -LiteralPath $venvPython)) {
                Push-Location $targetProject
                try {
                    Invoke-CheckedCommand -Description 'python -m venv .venv' -Script { python -m venv .venv }
                }
                finally {
                    Pop-Location
                }
            }

            Invoke-CheckedCommand -Description 'pip install --upgrade pip' -Script { & $venvPython -m pip install --no-cache-dir --upgrade pip }
            Invoke-CheckedCommand -Description 'pip install -r requirements.txt' -Script { & $venvPython -m pip install --no-cache-dir -r (Join-Path $targetProject 'requirements.txt') }
            Install-CompatibilityPackages -BaselinePython $baselinePython -VenvPython $venvPython -InstallPostgresDriver:$InstallPostgresDriver -InstallBrowserDeps:$InstallBrowserDeps

            Push-Location (Join-Path $targetProject 'frontend-nextjs')
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

        Write-Host "[OK] Prepared $targetProject from baseline + backup"
    }
    catch {
        $entry.status = 'failed'
        $entry.error = $_.Exception.Message
        $entry.completed_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
        Write-Host "[FAIL] $($item.Target): $($_.Exception.Message)"
    }

    $manifest.entries += [PSCustomObject]$entry
}

$manifest | ConvertTo-Json -Depth 8 | Set-Content -Path $manifestPath -Encoding UTF8

$successCount = @($manifest.entries | Where-Object { $_.status -eq 'success' }).Count
$failCount = @($manifest.entries | Where-Object { $_.status -eq 'failed' }).Count

Write-Host ''
Write-Host '========================================'
Write-Host 'Baseline restore complete'
Write-Host "Manifest: $manifestPath"
Write-Host "Success:  $successCount"
Write-Host "Failed:   $failCount"
Write-Host '========================================'
