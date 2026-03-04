[CmdletBinding()]
param(
    [string]$RepoRoot = '',
    [string]$TargetProject = 'D:\11-20\langgraph-v8.0.0-runtime',
    [string]$Commit = '8c2099707ce9d46a2192d4cd89fb81e1c336ce76',
    [string]$Tag = 'v8.0.0',
    [string]$BackupName = 'auto_backup_20260302_120001',
    [int]$PreferredBackendPort = 8108,
    [int]$PreferredFrontendPort = 3108,
    [bool]$CopyData = $true,
    [bool]$InstallDeps = $true,
    [bool]$InstallPostgresDriver = $true,
    [bool]$InstallBrowserDeps = $false,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
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

function Get-PackageVersion {
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
        return ""
    }

    return ($version | Out-String).Trim()
}

function Install-CompatibilityPackages {
    param(
        [Parameter(Mandatory = $true)][string]$VenvPython,
        [string]$BaselinePython,
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

    if (![string]::IsNullOrWhiteSpace($BaselinePython) -and (Test-Path -LiteralPath $BaselinePython)) {
        $langgraphPackages = @(
            'langgraph',
            'langgraph-checkpoint',
            'langgraph-checkpoint-sqlite',
            'langgraph-prebuilt',
            'langgraph-sdk'
        )

        $pins = @()
        foreach ($pkg in $langgraphPackages) {
            $version = Get-PackageVersion -PythonExe $BaselinePython -PackageName $pkg
            if (-not [string]::IsNullOrWhiteSpace($version)) {
                $pins += "$pkg==$version"
            }
        }

        if ($pins.Count -gt 0) {
            Invoke-CheckedCommand -Description 'pip install pinned langgraph packages' -Script {
                & $VenvPython -m pip install --no-cache-dir @pins
            }
        }
    }

    if ($InstallBrowserDeps) {
        Invoke-CheckedCommand -Description 'playwright install chromium' -Script {
            & $VenvPython -m playwright install chromium
        }
    }
}

function Test-PortAvailable {
    param([Parameter(Mandatory = $true)][int]$Port)

    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        try {
            $listener.Stop()
        }
        catch {
        }
    }
}

function Get-PortPair {
    param(
        [Parameter(Mandatory = $true)][int]$BackendPort,
        [Parameter(Mandatory = $true)][int]$FrontendPort
    )

    $currentBackend = $BackendPort
    $currentFrontend = $FrontendPort

    while ($true) {
        if ((Test-PortAvailable -Port $currentBackend) -and (Test-PortAvailable -Port $currentFrontend)) {
            return @{
                Backend = $currentBackend
                Frontend = $currentFrontend
            }
        }

        $currentBackend += 10
        $currentFrontend += 10
    }
}

function Export-CommitTree {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Commit,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $archiveEntries = @()
    $topLevel = & git -C $RepoRoot ls-tree --name-only $Commit
    if ($LASTEXITCODE -ne 0) {
        throw "git ls-tree failed for commit $Commit"
    }

    foreach ($entry in $topLevel) {
        $trimmed = ($entry | Out-String).Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }
        if ($trimmed -eq 'node_modules') {
            continue
        }
        $archiveEntries += $trimmed
    }

    if ($archiveEntries.Count -eq 0) {
        throw "No archive entries resolved for commit $Commit"
    }

    $archivePath = Join-Path ([System.IO.Path]::GetTempPath()) ("v8_restore_{0}.tar" -f [System.Guid]::NewGuid().ToString('N'))
    try {
        Invoke-CheckedCommand -Description 'git archive export' -Script {
            & git -C $RepoRoot archive --format=tar --output=$archivePath $Commit @archiveEntries
        }
        Invoke-CheckedCommand -Description 'tar extract commit snapshot' -Script {
            & tar -xf $archivePath -C $Destination
        }
    }
    finally {
        if (Test-Path -LiteralPath $archivePath) {
            Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Remove-IfExists {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

function Set-OrAppendEnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $content = ''
    if (Test-Path -LiteralPath $Path) {
        $content = Get-Content -Raw -Encoding UTF8 $Path
    }

    if ($content -match "(?m)^$([regex]::Escape($Key))=") {
        $content = [regex]::Replace($content, "(?m)^$([regex]::Escape($Key))=.*$", "$Key=$Value")
    }
    else {
        if ($content.Length -gt 0 -and -not $content.EndsWith("`r`n")) {
            $content += "`r`n"
        }
        $content += "$Key=$Value`r`n"
    }

    Set-Content -Path $Path -Value $content -Encoding UTF8
}

function Write-BackendWrapper {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][int]$BackendPort
    )

    $scriptDir = Join-Path $ProjectRoot 'scripts'
    New-Item -ItemType Directory -Path $scriptDir -Force | Out-Null

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
    Set-Content -Path (Join-Path $scriptDir 'run_server_v8.py') -Value $backendPy -Encoding ASCII

    $backendBat = @"
@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set DEBUG=
cd /d %~dp0
call .venv\Scripts\python.exe scripts\run_server_v8.py
"@
    Set-Content -Path (Join-Path $ProjectRoot 'start_backend_v8.bat') -Value $backendBat -Encoding ASCII
}

function Write-FrontendWrapper {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][int]$BackendPort,
        [Parameter(Mandatory = $true)][int]$FrontendPort
    )

    $apiUrl = "http://127.0.0.1:$BackendPort"
    $envLocalPath = Join-Path $ProjectRoot 'frontend-nextjs\.env.local'

    Set-OrAppendEnvValue -Path $envLocalPath -Key 'NEXT_PUBLIC_API_BASE_URL' -Value $apiUrl
    Set-OrAppendEnvValue -Path $envLocalPath -Key 'NEXT_PUBLIC_API_URL' -Value $apiUrl

    $frontendBat = @"
@echo off
chcp 65001 >nul
cd /d %~dp0frontend-nextjs
set NEXT_PUBLIC_API_BASE_URL=$apiUrl
set NEXT_PUBLIC_API_URL=$apiUrl
call npm run dev -- -p $FrontendPort
"@
    Set-Content -Path (Join-Path $ProjectRoot 'start_frontend_v8.bat') -Value $frontendBat -Encoding ASCII
}

function Copy-IfExists {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (Test-Path -LiteralPath $Source) {
        $destinationDir = Split-Path -Parent $Destination
        if (-not [string]::IsNullOrWhiteSpace($destinationDir)) {
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $Source -Destination $Destination -Force
    }
}

function Write-TextFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $destinationDir = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($destinationDir)) {
        New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
    }
    Set-Content -Path $Path -Value $Content -Encoding UTF8
}

$backupRoot = Join-Path $RepoRoot 'backup'
$backupDir = Join-Path $backupRoot $BackupName
$metaDir = Join-Path $TargetProject '_restore_meta'
$baselinePython = Get-BaselinePython -ProjectRoot $RepoRoot

if (!(Test-Path -LiteralPath $RepoRoot)) {
    throw "Repo root not found: $RepoRoot"
}
if (!(Test-Path -LiteralPath $backupDir)) {
    throw "Backup directory not found: $backupDir"
}

$resolvedCommit = (& git -C $RepoRoot rev-parse --verify "$Commit^{commit}" | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($resolvedCommit)) {
    throw "Failed to resolve commit: $Commit"
}

$tagCommit = (& git -C $RepoRoot rev-parse --verify "$Tag^{commit}" | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($tagCommit)) {
    throw "Failed to resolve tag: $Tag"
}
if ($tagCommit -ne $resolvedCommit) {
    throw "Tag $Tag resolves to $tagCommit, expected $resolvedCommit"
}

$commitInfo = (& git -C $RepoRoot show -s --format="%H%n%ci%n%s" $resolvedCommit | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Failed to read commit metadata for $resolvedCommit"
}

if (Test-Path -LiteralPath $TargetProject) {
    if ($Force) {
        Remove-Item -LiteralPath $TargetProject -Recurse -Force
    }
    else {
        throw "Target project already exists: $TargetProject"
    }
}

New-Item -ItemType Directory -Path $TargetProject -Force | Out-Null
New-Item -ItemType Directory -Path $metaDir -Force | Out-Null

Export-CommitTree -RepoRoot $RepoRoot -Commit $resolvedCommit -Destination $TargetProject

Remove-IfExists -Path (Join-Path $TargetProject 'node_modules')
Remove-IfExists -Path (Join-Path $TargetProject 'frontend-nextjs\node_modules')

$backupConfigDir = Join-Path $backupDir 'config'

Copy-IfExists -Source (Join-Path $backupConfigDir '.env') -Destination (Join-Path $TargetProject '.env')
Copy-IfExists -Source (Join-Path $backupConfigDir '.env.local') -Destination (Join-Path $TargetProject 'frontend-nextjs\.env.local')

if ($CopyData) {
    Copy-Item -LiteralPath (Join-Path $backupDir 'data') -Destination (Join-Path $TargetProject 'data') -Recurse -Force
}

foreach ($metaFile in @('BACKUP_INFO.txt', 'version_metadata.json', 'git_log.txt', 'git_status.txt', 'git_diff.patch', 'repo.bundle')) {
    Copy-IfExists -Source (Join-Path $backupDir $metaFile) -Destination (Join-Path $metaDir $metaFile)
}

$ports = Get-PortPair -BackendPort $PreferredBackendPort -FrontendPort $PreferredFrontendPort
$backendPort = [int]$ports.Backend
$frontendPort = [int]$ports.Frontend

Write-BackendWrapper -ProjectRoot $TargetProject -BackendPort $backendPort
Write-FrontendWrapper -ProjectRoot $TargetProject -BackendPort $backendPort -FrontendPort $frontendPort

$targetCommitText = @(
    "tag=$Tag"
    "commit=$resolvedCommit"
    "backup=$BackupName"
    "restored_at=$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK')"
    "repo_root=$RepoRoot"
    "target_project=$TargetProject"
) -join "`r`n"
Write-TextFile -Path (Join-Path $metaDir 'target_commit.txt') -Content $targetCommitText

$tagResolutionText = @(
    "requested_tag=$Tag"
    "resolved_commit=$tagCommit"
    "expected_commit=$resolvedCommit"
    "match=$($tagCommit -eq $resolvedCommit)"
    ""
    $commitInfo
) -join "`r`n"
Write-TextFile -Path (Join-Path $metaDir 'tag_resolution.txt') -Content $tagResolutionText

$portMappingText = @(
    "backend_port=$backendPort"
    "frontend_port=$frontendPort"
    "backend_url=http://127.0.0.1:$backendPort"
    "frontend_url=http://127.0.0.1:$frontendPort"
    "backend_launcher=start_backend_v8.bat"
    "frontend_launcher=start_frontend_v8.bat"
) -join "`r`n"
Write-TextFile -Path (Join-Path $metaDir 'port_mapping.txt') -Content $portMappingText

$runtimeNotes = @(
    "restore_mode=shared_service_state"
    "redis=shared"
    "milvus=shared"
    "database=shared"
    "data_copied=$CopyData"
    "dependencies_installed=$InstallDeps"
    "git_diff_patch_applied=false"
    ""
    "Runtime note: this restored project shares Redis, Milvus, and database state with the current machine."
) -join "`r`n"
Write-TextFile -Path (Join-Path $metaDir 'runtime_notes.txt') -Content $runtimeNotes

if ($InstallDeps) {
    $env:PIP_NO_CACHE_DIR = '1'
    $venvPython = Join-Path $TargetProject '.venv\Scripts\python.exe'

    if (!(Test-Path -LiteralPath $venvPython)) {
        Push-Location $TargetProject
        try {
            Invoke-CheckedCommand -Description 'python -m venv .venv' -Script { python -m venv .venv }
        }
        finally {
            Pop-Location
        }
    }

    Invoke-CheckedCommand -Description 'pip install --upgrade pip' -Script { & $venvPython -m pip install --no-cache-dir --upgrade pip }
    Invoke-CheckedCommand -Description 'pip install -r requirements.txt' -Script { & $venvPython -m pip install --no-cache-dir -r (Join-Path $TargetProject 'requirements.txt') }
    Install-CompatibilityPackages -VenvPython $venvPython -BaselinePython $baselinePython -InstallPostgresDriver:$InstallPostgresDriver -InstallBrowserDeps:$InstallBrowserDeps

    $frontendNodeModules = Join-Path $TargetProject 'frontend-nextjs\node_modules'
    Remove-IfExists -Path $frontendNodeModules

    Push-Location (Join-Path $TargetProject 'frontend-nextjs')
    try {
        try {
            Invoke-CheckedCommand -Description 'npm ci' -Script { npm ci }
        }
        catch {
            Write-Host '[WARN] npm ci failed, falling back to npm install'
            Invoke-CheckedCommand -Description 'npm install' -Script { npm install }
        }
    }
    finally {
        Pop-Location
    }
}

$manifest = [ordered]@{
    restored_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    repo_root = $RepoRoot
    target_project = $TargetProject
    tag = $Tag
    commit = $resolvedCommit
    backup = $BackupName
    copy_data = $CopyData
    install_deps = $InstallDeps
    install_postgres_driver = $InstallPostgresDriver
    install_browser_deps = $InstallBrowserDeps
    backend_port = $backendPort
    frontend_port = $frontendPort
    shared_services = @{
        redis = $true
        milvus = $true
        database = $true
    }
    metadata_dir = $metaDir
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $metaDir 'restore_manifest.json') -Encoding UTF8

Write-Host ''
Write-Host '========================================'
Write-Host 'v8.0.0 runtime restore prepared'
Write-Host "Target:   $TargetProject"
Write-Host "Backend:  http://127.0.0.1:$backendPort"
Write-Host "Frontend: http://127.0.0.1:$frontendPort"
Write-Host "Meta:     $metaDir"
Write-Host '========================================'
