<#
.SYNOPSIS
    清理 chaoxing 项目 进度存档 目录里一周之前的进度报告。

.DESCRIPTION
    只删除文件名形如 进度报告_<时间戳>.md 的"存档"文件，且最后写入时间早于 -Days 天。
    **永远不会删除 进度报告.md（最新一份）**，也不会碰目录里的其它文件。
    不改动 progress.py 的任何行为。

.PARAMETER Days
    保留天数，默认 7（即删除 7 天前未再写入的存档）。

.PARAMETER Path
    存档目录，默认本脚本所在目录下的 进度存档。

.PARAMETER Yes
    跳过确认提示，直接删除（供计划任务调用）。

.EXAMPLE
    .\clean_reports.ps1                # 列出并确认后删除 7 天前的存档
    .\clean_reports.ps1 -Days 30       # 只删 30 天前的
    .\clean_reports.ps1 -Yes           # 不询问
#>
[CmdletBinding()]
param(
    [int]$Days = 7,
    [string]$Path = '',
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'

# param 默认值在调用方作用域求值，那时 $PSScriptRoot 还是空的，所以在这里补
if ([string]::IsNullOrWhiteSpace($Path)) { $Path = Join-Path $PSScriptRoot '进度存档' }

# 只匹配存档：进度报告_20261023_223104.md
# 不会匹配最新的 进度报告.md
$Pattern = '进度报告_*.md'
$KeepName = '进度报告.md'

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Host "[提示] 存档目录还不存在，说明还没生成过存档: $Path" -ForegroundColor Yellow
    Write-Host "       先双击 查看进度.cmd 跑一次就会自动创建。" -ForegroundColor Yellow
    exit 0
}

$cutoff = (Get-Date).AddDays(-$Days)
Write-Host "存档目录: $Path"
Write-Host "删除条件: 名字符合 $Pattern 且最后写入早于 $($cutoff.ToString('yyyy-MM-dd HH:mm'))（即 $Days 天前）"
Write-Host ""

$targets = @(
    Get-ChildItem -LiteralPath $Path -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -ne $KeepName -and $_.LastWriteTime -lt $cutoff } |
        Sort-Object LastWriteTime
)

if ($targets.Count -eq 0) {
    Write-Host "没有符合条件的存档，无需清理。" -ForegroundColor Green
    $all = @(Get-ChildItem -LiteralPath $Path -Filter $Pattern -File -ErrorAction SilentlyContinue)
    if ($all.Count -gt 0) {
        $sum = ($all | Measure-Object -Property Length -Sum).Sum
        $newest = ($all | Sort-Object LastWriteTime -Descending)[0]
        Write-Host ("当前保留 {0} 份存档，合计 {1:N1} KB（最新的是 {2:yyyy-MM-dd HH:mm}）。" -f `
            $all.Count, ($sum / 1KB), $newest.LastWriteTime)
    }
    exit 0
}

$totalBytes = ($targets | Measure-Object -Property Length -Sum).Sum
Write-Host ("将删除 {0} 个文件，合计 {1:N1} KB：" -f $targets.Count, ($totalBytes / 1KB)) -ForegroundColor Yellow
foreach ($f in $targets) {
    Write-Host ("  {0,7:N1} KB  {1:yyyy-MM-dd HH:mm}  {2}" -f `
        ($f.Length / 1KB), $f.LastWriteTime, $f.Name)
}
Write-Host ""

if (-not $Yes) {
    # 坑：stdin 被重定向（含 < nul）时 Read-Host 返回 $null，
    # 而 $null -notmatch '...' 会得到 $false（不是 $true），会误判成"确认"直接删。
    # 所以这里显式判空 + 显式接受 y/yes，并且非交互环境一律拒绝。
    if ([Console]::IsInputRedirected) {
        Write-Host "检测到非交互输入（stdin 被重定向），为安全起见已取消，未删除任何文件。" -ForegroundColor Yellow
        Write-Host "无人值守删除请显式加 -Yes：clean_reports.ps1 -Days 7 -Yes" -ForegroundColor Yellow
        exit 0
    }
    $answer = Read-Host "确认删除以上文件？输入 y 继续，其他任意输入取消 [y/N]"
    $ok = ($null -ne $answer) -and ($answer.Trim() -match '^(?i:y|yes)$')
    if (-not $ok) {
        Write-Host "已取消，未删除任何文件。" -ForegroundColor Green
        exit 0
    }
}

$deleted = 0
$freed = 0
$failed = @()
foreach ($f in $targets) {
    try {
        Remove-Item -LiteralPath $f.FullName -Force -ErrorAction Stop
        $deleted++
        $freed += $f.Length
    }
    catch {
        $failed += "$($f.Name): $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host ("已删除 {0} 个文件，释放 {1:N1} KB。" -f $deleted, ($freed / 1KB)) -ForegroundColor Green
if ($failed.Count -gt 0) {
    Write-Host "[警告] 以下文件删不掉（可能正被占用）：" -ForegroundColor Yellow
    $failed | ForEach-Object { Write-Host "  $_" }
}

$rest = @(Get-ChildItem -LiteralPath $Path -Filter $Pattern -File -ErrorAction SilentlyContinue)
$restSum = if ($rest.Count -gt 0) { ($rest | Measure-Object -Property Length -Sum).Sum } else { 0 }
$latest = Get-ChildItem -LiteralPath $Path -Filter $KeepName -File -ErrorAction SilentlyContinue
$latestSize = if ($latest) { $latest.Length } else { 0 }
Write-Host ("剩余：存档 {0} 份 / {1:N1} KB（{2} 未动）。" -f `
    $rest.Count, ($restSum / 1KB), $KeepName)
