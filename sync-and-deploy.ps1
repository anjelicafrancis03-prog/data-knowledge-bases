# 知识库合集更新推送脚本
# 用法: powershell -ExecutionPolicy Bypass -File sync-and-deploy.ps1
# 功能: 重新生成数据 → 复制到仓库 → 推送到 GitHub → (可选)部署到 Cloudflare Pages

param(
    [switch]$NoDeploy,
    [switch]$NoGen
)

$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
$RepoRoot = "F:\codex\data-knowledge-bases"
$Start = Get-Date

Write-Host "=== 知识库合集更新推送 ===" -ForegroundColor Cyan

# Step 1: 重新生成 zst-kb 数据
if (-not $NoGen) {
    Write-Host "`n[1/5] 重新生成 zst-kb 数据..." -ForegroundColor Yellow
    & python "F:\codex\tools\gen-zst-kb-dashboard.py"
    if ($LASTEXITCODE -ne 0) { Write-Host "  ⚠️ 生成失败，继续执行" -ForegroundColor Red }
    else { Write-Host "  ✅ 生成完成" -ForegroundColor Green }
} else {
    Write-Host "`n[1/5] 跳过数据生成" -ForegroundColor Gray
}

# Step 2: 复制所有数据库到仓库
Write-Host "`n[2/5] 复制数据库到仓库..." -ForegroundColor Yellow
$dirs = @(
    "zst-kb",
    "xianmingyishuo-graph-browser",
    "xianmingyishuo-graph-browser-sigma",
    "xianmingyishuo-lightrag-browser",
    "memory-carry-context-browser",
    "memory-carry-dynamic-browser",
    "memory-carry-evidence-browser",
    "medical-aesthetic-rag-browser",
    "medical-aesthetic-btxa-review-batch",
    "sit-kanwas-fusion-dashboard",
    "follow-builders-browser",
    "external-agent-seat-graph",
    "codegraph-browser",
    "rag-architecture-comparison-20260608",
    "dbx-tool"
)
$copied = 0
foreach ($d in $dirs) {
    $src = "C:\html\$d"
    $dst = "$RepoRoot\$d"
    if (Test-Path "$src\index.html") {
        $files = (Get-ChildItem $src -Recurse -File).Count
        Write-Host "  📋 $d ($files 文件)"
        if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
        New-Item -Path $dst -ItemType Directory -Force | Out-Null
        Get-ChildItem $src | Copy-Item -Destination $dst -Recurse -Force
        $copied++
    } else {
        Write-Host "  📋 $d (已存在于仓库，跳过复制)" -ForegroundColor Gray
    }
}
Write-Host "  ✅ 共复制 $copied 个数据库" -ForegroundColor Green

# Step 3: 更新主页时间戳
Write-Host "`n[3/5] 更新主页时间戳..." -ForegroundColor Yellow
$date = Get-Date -Format "yyyy-MM-dd"
$indexFile = "$RepoRoot\index.html"
if (Test-Path $indexFile) {
    $content = Get-Content $indexFile -Raw
    $content = $content -replace '更新: \d{4}-\d{2}-\d{2}', "更新: $date"
    Set-Content $indexFile $content -Encoding UTF8
    Write-Host "  ✅ 时间戳已更新" -ForegroundColor Green
}

# Step 4: 推送到 GitHub
Write-Host "`n[4/5] 推送到 GitHub..." -ForegroundColor Yellow
$ErrorActionPreference = "SilentlyContinue"
Push-Location $RepoRoot
git add -A
$status = git status --porcelain
if ($status) {
    $count = ($status | Measure-Object -Line).Lines
    git commit -m "sync: $date 知识库更新 ($count files)"
    git push
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ GitHub 推送成功" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ GitHub 推送失败，请检查网络" -ForegroundColor Red
    }
} else {
    Write-Host "  ℹ️ 没有变更，跳过推送" -ForegroundColor Gray
}
Pop-Location

# Step 5: 部署到 Cloudflare Pages
if (-not $NoDeploy) {
    Write-Host "`n[5/5] 部署到 Cloudflare Pages..." -ForegroundColor Yellow
    npx wrangler pages deploy $RepoRoot --project-name data-knowledge-bases --branch main 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Cloudflare Pages 部署成功" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ Cloudflare Pages 部署失败" -ForegroundColor Red
    }
} else {
    Write-Host "`n[5/5] 跳过 Cloudflare 部署 (--NoDeploy)" -ForegroundColor Gray
}

$Elapsed = (Get-Date) - $Start
Write-Host "`n=== 完成 (耗时 $($Elapsed.TotalSeconds.ToString('0.0')) 秒) ===" -ForegroundColor Cyan
Write-Host "访问: https://data-knowledge-bases.pages.dev" -ForegroundColor Cyan