#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Personal AI Voice & Call Agent - Production Deployment"
echo "=========================================================="

if [ ! -f .env ]; then
    if [ -f .env.production.example ]; then
        echo "[!] .env file not found. Copying from .env.production.example..."
        cp .env.production.example .env
        echo "[!] Please edit .env with your real API keys and credentials before continuing."
        exit 1
    else
        echo "[ERROR] .env file is missing!"
        exit 1
    fi
fi

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed or not in PATH."
    exit 1
fi

echo "[1/4] Checking and building multi-stage container images..."
docker compose -f docker-compose.prod.yml build

echo "[2/4] Starting PostgreSQL with pgvector..."
docker compose -f docker-compose.prod.yml up -d postgres
echo "Waiting for PostgreSQL healthcheck..."
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres -t 20

echo "[3/4] Starting Asterisk PBX, Agent API, Next.js Dashboard & Caddy..."
docker compose -f docker-compose.prod.yml up -d

echo "[4/4] Verifying health and running status..."
docker compose -f docker-compose.prod.yml ps

echo "=========================================================="
echo "✅ Deployment Successful!"
echo " Web Dashboard: http://localhost"
echo " REST API Docs: http://localhost/docs"
echo " Asterisk ARI:  http://localhost:8088"
echo "=========================================================="
