# 车辆智能调度 Agent 项目 - 一键启动脚本（Windows PowerShell）
# 用法: .\start-dev.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "==> 启动后端（FastAPI :8000）..." -ForegroundColor Cyan
$backendProc = Start-Process -FilePath "py" -ArgumentList "-3.12", "-m", "app.run" -WorkingDirectory $backend -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 2

Write-Host "==> 启动前端（Vue3 :8080）..." -ForegroundColor Cyan
$frontendProc = Start-Process -FilePath "npm" -ArgumentList "run", "serve" -WorkingDirectory $frontend -PassThru -WindowStyle Minimized

Write-Host ""
Write-Host "==> 启动完成" -ForegroundColor Green
Write-Host "    前端: http://localhost:8080"
Write-Host "    后端: http://localhost:8000/docs"
Write-Host "    按 Ctrl+C 退出，或关闭本窗口"
Write-Host ""

try {
    while ($true) {
        if ($backendProc.HasExited -or $frontendProc.HasExited) {
            Write-Warning "检测到子进程退出，关闭另一进程..."
            break
        }
        Start-Sleep -Seconds 1
    }
} finally {
    if (-not $backendProc.HasExited) { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue }
    if (-not $frontendProc.HasExited) { Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue }
}
