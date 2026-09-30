# Media Downloader - PowerShell Launcher
$rootDir = $PSScriptRoot
Set-Location $rootDir

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "       Media Downloader - Starting Services        " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Ensure .env exists
if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Write-Host "[INFO] Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# 2. Check Backend Virtual Environment
$venvPython = Join-Path $rootDir "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[INFO] Creating backend virtual environment..." -ForegroundColor Yellow
    python -m venv (Join-Path $rootDir "backend\.venv")
    Write-Host "[INFO] Installing backend dependencies..." -ForegroundColor Yellow
    & $venvPython -m pip install -r (Join-Path $rootDir "backend\requirements.txt")
}

# 3. Check Frontend node_modules
$nodeModules = Join-Path $rootDir "frontend\node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "[INFO] Installing frontend node_modules..." -ForegroundColor Yellow
    Set-Location (Join-Path $rootDir "frontend")
    npm install
    Set-Location $rootDir
}

Write-Host "`n[1/2] Launching Backend on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$rootDir\backend'; & '$venvPython' -m uvicorn app.main:app --reload --port 8000"

Write-Host "[2/2] Launching Frontend on http://localhost:3000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$rootDir\frontend'; npm run dev"

Write-Host "`n===================================================" -ForegroundColor Cyan
Write-Host "Both services launched in separate windows!" -ForegroundColor Cyan
Write-Host "- Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host "- Swagger Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "- Frontend UI:  http://localhost:3000" -ForegroundColor White
Write-Host "===================================================" -ForegroundColor Cyan
