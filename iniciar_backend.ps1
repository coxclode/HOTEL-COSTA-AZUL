# ── Hotel Costa Azul: Iniciar backend local ──
# Ejecutar desde la raiz del proyecto: .\iniciar_backend.ps1

$backendPath = Join-Path $PSScriptRoot "backend"

if (-not (Test-Path "$backendPath\.env")) {
    Write-Host "ERROR: No existe backend/.env" -ForegroundColor Red
    Write-Host "Crea el archivo backend/.env con tu DATABASE_URL de Neon." -ForegroundColor Yellow
    Write-Host "Ejemplo: DATABASE_URL=postgresql://user:pass@host/db?sslmode=require" -ForegroundColor Yellow
    exit 1
}

Write-Host "Iniciando Hotel Costa Azul Backend..." -ForegroundColor Cyan
Write-Host "API disponible en: http://localhost:5000" -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detener." -ForegroundColor Gray

Set-Location $backendPath
python app.py
