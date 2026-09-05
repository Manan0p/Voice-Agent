# PowerShell Production Deployment Script for Personal AI Call Agent
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Personal AI Voice & Call Agent - Production Deployment" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.production.example") {
        Write-Host "[!] .env file not found. Copying from .env.production.example..." -ForegroundColor Yellow
        Copy-Item ".env.production.example" ".env"
        Write-Host "[!] Please configure .env with your real API keys before running." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "[1/3] Building production multi-stage container images..." -ForegroundColor Green
docker compose -f docker-compose.prod.yml build

Write-Host "[2/3] Launching PostgreSQL, Asterisk, Agent API, Dashboard & Caddy..." -ForegroundColor Green
docker compose -f docker-compose.prod.yml up -d

Write-Host "[3/3] Checking container statuses..." -ForegroundColor Green
docker compose -f docker-compose.prod.yml ps

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host " Dashboard UI: http://localhost" -ForegroundColor White
Write-Host " API Docs:     http://localhost/docs" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
