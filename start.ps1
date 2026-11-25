$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting Parallel World Backend (FastAPI on http://127.0.0.1:8000)..." -ForegroundColor Cyan
$backend = Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory "$root\backend" -PassThru

Write-Host "Starting Parallel World Frontend (Vite on http://localhost:5173)..." -ForegroundColor Cyan
$frontend = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory "$root\frontend" -PassThru

Write-Host "Parallel World is launching! Open http://localhost:5173" -ForegroundColor Green
Write-Host "Press Ctrl+C or close child windows to stop." -ForegroundColor Yellow

try {
    Wait-Process -Id $backend.Id, $frontend.Id
} finally {
    if (!$backend.HasExited) { Stop-Process -Id $backend.Id -Force }
    if (!$frontend.HasExited) { Stop-Process -Id $frontend.Id -Force }
}
