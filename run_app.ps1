# Build frontend and run Flask single-server (Windows PowerShell)
# Usage: Open PowerShell in repo root and run: .\run_app.ps1

Write-Host "Building frontend (if present)..." -ForegroundColor Cyan
$frontendDir = Join-Path $PSScriptRoot 'frontend'
if (Test-Path (Join-Path $frontendDir 'package.json')) {
    Push-Location $frontendDir
    if (Test-Path 'node_modules') { Write-Host 'node_modules exists, skipping npm install' -ForegroundColor Yellow } else {
        Write-Host 'Running npm install...' -ForegroundColor Green
        npm install
    }
    Write-Host 'Running npm run build...' -ForegroundColor Green
    npm run build
    Pop-Location
} else {
    Write-Host 'No frontend/package.json found, skipping frontend build' -ForegroundColor Yellow
}

Write-Host 'Starting Flask app...' -ForegroundColor Cyan
# Run Flask app module (this will block)
python -m tradingbuddy.api.flask_app
