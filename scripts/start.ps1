param([switch]$SkipBuild, [switch]$Lan)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw '请先按 README 安装项目依赖。' }
if (-not $SkipBuild) {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw '前端构建失败，请查看上方错误。' }
}
if ($Lan) { Write-Host '手机与电脑连接同一 Wi-Fi，手机浏览器访问 http://电脑的局域网IPv4地址:8010；仅在可信局域网使用。' }
$listenAddress = if ($Lan) { '0.0.0.0' } else { '127.0.0.1' }
Write-Host '窗序启动地址：http://127.0.0.1:8010，按 Ctrl+C 停止。'
& $pythonPath -m uvicorn backend.main:app --host $listenAddress --port 8010
