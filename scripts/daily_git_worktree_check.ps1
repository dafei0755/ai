param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$ReportDir = 'reports/git-worktree-health',
    [switch]$FailOnDirty
)

$ErrorActionPreference = 'Stop'

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    & git -C $RepoRoot @Args
}

function Get-DirtyLevel {
    param([int]$ModifiedCount, [int]$UntrackedCount, [bool]$HasDelete, [bool]$HasConflict)
    $total = $ModifiedCount + $UntrackedCount
    if ($HasConflict -or $HasDelete) { return 'G4' }
    if ($total -eq 0) { return 'G0' }
    if ($total -le 5) { return 'G1' }
    if ($total -le 20) { return 'G2' }
    return 'G3'
}

function Get-Bucket {
    param([string]$Path)
    if ($Path -match '^"?\.gitignore"?$' -or $Path -match '^"?AGENTS\.md"?$' -or $Path -match '^"?docs[\/]development[\/].*PROTOCOL\.md"?$' -or $Path -match '^"?docs[\/]development[\/]DAILY_GIT_WORKTREE_MAINTENANCE\.md"?$' -or $Path -match '^"?scripts[\/](daily_git_worktree_check|register_daily_git_worktree_check)\.ps1"?$') { return 'B1 Git/Agent governance' }
    if ($Path -match '^"?README\.md"?$' -or $Path -match '^"?QUICKSTART\.md"?$' -or $Path -match '^"?docs[\\/]README\.md"?$') { return 'B2 startup docs' }
    if ($Path -match 'intelligent_project_analyzer[\\/].*demand_reconstruction' -or $Path -match 'intelligent_project_analyzer[\\/].*scheme_advisor') { return 'B3 demand reconstruction runtime' }
    if ($Path -match '^"?frontend-nextjs[\\/]') { return 'B4 frontend surface' }
    if ($Path -match 'admin_routes|knowledge_governance|review_queue') { return 'B5 governance admin' }
    if ($Path -match '^"?tests[\\/]' -or $Path -match '^"?scripts[\\/]smoke_') { return 'B6 tests and smoke tools' }
    if ($Path -match '^"?sf[\\/]' -or $Path -match '^"?docs[\\/]mechanism-reviews[\\/]') { return 'B7 product docs and corpus' }
    if ($Path -match '(^|[\\/])\.codegraph[\\/]' -or $Path -match '(^|[\\/])\.pytest_cache[\\/]' -or $Path -match '(^|[\\/])\.next[\\/]') { return 'B8 local/generated' }
    return 'B9 needs review'
}

$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$reportRoot = Join-Path $RepoRoot $ReportDir
New-Item -ItemType Directory -Force -Path $reportRoot | Out-Null

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$reportPath = Join-Path $reportRoot "$timestamp.md"

$branch = (Invoke-Git branch --show-current | Select-Object -First 1)
$head = (Invoke-Git rev-parse --short HEAD | Select-Object -First 1)
$statusLines = @(Invoke-Git status --porcelain=v1 --untracked-files=all)
$ignoredLines = @(Invoke-Git status --short --ignored -- .codegraph intelligent_project_analyzer/.codegraph)

$items = foreach ($line in $statusLines) {
    if ([string]::IsNullOrWhiteSpace($line) -or $line.Length -lt 4) { continue }
    $status = $line.Substring(0, 2)
    $itemPath = $line.Substring(3)
    [pscustomobject]@{
        Status = $status
        Path = $itemPath
        Bucket = Get-Bucket -Path $itemPath
    }
}

$modifiedCount = @($items | Where-Object { $_.Status -ne '??' }).Count
$untrackedCount = @($items | Where-Object { $_.Status -eq '??' }).Count
$hasDelete = [bool]@($items | Where-Object { $_.Status -match 'D' }).Count
$hasConflict = [bool]@($items | Where-Object { $_.Status -match 'U|AA|DD' }).Count
$level = Get-DirtyLevel -ModifiedCount $modifiedCount -UntrackedCount $untrackedCount -HasDelete $hasDelete -HasConflict $hasConflict

$bucketGroups = @($items | Group-Object Bucket | Sort-Object Name)
$statusGroups = @($items | Group-Object Status | Sort-Object Name)

$recommendation = switch ($level) {
    'G0' { 'No cleanup needed. Keep working from the clean baseline.' }
    'G1' { 'Review the small change set and commit by explicit path if it belongs to one task.' }
    'G2' { 'Classify files into buckets before staging. Avoid full-tree diff, stash, or clean.' }
    'G3' { 'Create a backup checkpoint before new work. Work one bucket at a time or use a worktree.' }
    'G4' { 'Freeze feature work. Resolve deletes/conflicts/unknown files before any cleanup.' }
}

$content = New-Object System.Collections.Generic.List[string]
$content.Add('# Daily Git Worktree Health Report')
$content.Add('')
$content.Add("- Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')")
$content.Add("- Repo: ``$RepoRoot``")
$content.Add("- Branch: ``$branch``")
$content.Add("- HEAD: ``$head``")
$content.Add("- Dirty level: ``$level``")
$content.Add("- Modified/tracked entries: $modifiedCount")
$content.Add("- Untracked entries: $untrackedCount")
$content.Add('')
$content.Add('## Recommendation')
$content.Add('')
$content.Add($recommendation)
$content.Add('')
$content.Add('## Status Counts')
$content.Add('')
if ($statusGroups.Count -eq 0) { $content.Add('- Clean') } else { foreach ($group in $statusGroups) { $content.Add("- ``$($group.Name)``: $($group.Count)") } }
$content.Add('')
$content.Add('## Buckets')
$content.Add('')
if ($bucketGroups.Count -eq 0) { $content.Add('- Clean') } else { foreach ($group in $bucketGroups) { $content.Add("- $($group.Name): $($group.Count)") } }
$content.Add('')
$content.Add('## Files')
$content.Add('')
if ($items.Count -eq 0) { $content.Add('- Clean') } else { foreach ($item in ($items | Sort-Object Bucket, Path)) { $content.Add("- ``$($item.Status)`` [$($item.Bucket)] ``$($item.Path)``") } }
$content.Add('')
$content.Add('## Ignored Local Index Directories')
$content.Add('')
if ($ignoredLines.Count -eq 0) { $content.Add('- None reported') } else { foreach ($line in $ignoredLines) { $content.Add("- ``$line``") } }
$content.Add('')
$content.Add('## Safety Rules')
$content.Add('')
$content.Add('- This task is report-only.')
$content.Add('- It does not run git add, git commit, git clean, git restore, git reset, or git stash.')
$content.Add('- Cleanup must be explicit and bucket-scoped.')
$content.Add('- In this environment, apply_patch is not used for scheduled maintenance writes because repeated small writes have stalled.')

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($reportPath, $content, $utf8NoBom)

Write-Output "Report: $reportPath"
Write-Output "DirtyLevel: $level"
Write-Output "Modified: $modifiedCount"
Write-Output "Untracked: $untrackedCount"

if ($FailOnDirty -and $level -ne 'G0') { exit 2 }
