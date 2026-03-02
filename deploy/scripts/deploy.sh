#!/bin/bash
# Deployment Script for Legal Case Search System
# Run this after cloning the repo on EC2
# Usage: chmod +x deploy.sh && ./deploy.sh

set -e  # Exit on error

PROJECT_DIR="/home/ubuntu/Legal-Judgement-Retrieval"
cd $PROJECT_DIR

echo "=================================================="
echo "Deploying Legal Case Search System"
echo "=================================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please create it first: cp deploy/.env.example .env && nano .env"
    exit 1
fi

echo ""
echo "=== Setting up Python environment ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r deploy/requirements-server.txt

echo ""
echo "=== Setting up frontend ==="
cd frontend
npm install
npm run build
cd ..

echo ""
echo "=== Installing systemd services ==="
sudo cp deploy/services/legal-api.service /etc/systemd/system/
sudo cp deploy/services/legal-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable legal-api legal-frontend

echo ""
echo "=== Starting services ==="
sudo systemctl start legal-api
sleep 2
sudo systemctl start legal-frontend

echo ""
echo "=== Checking service status ==="
sudo systemctl status legal-api --no-pager || true
echo ""
sudo systemctl status legal-frontend --no-pager || true

echo ""
echo "=================================================="
echo "✓ Deployment complete!"
echo "=================================================="

# Get public IP
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_EC2_IP")

echo ""
echo "Your services are running at:"
echo "  API:      http://${PUBLIC_IP}:8000"
echo "  Frontend: http://${PUBLIC_IP}:3000"
echo ""
echo "Useful commands:"
echo "  View API logs:      sudo journalctl -u legal-api -f"
echo "  View frontend logs: sudo journalctl -u legal-frontend -f"
echo "  Restart services:   sudo systemctl restart legal-api legal-frontend"
echo ""
echo "Don't forget to update frontend/.env.production.local with your EC2 IP:"
echo "  echo 'NEXT_PUBLIC_API_URL=http://${PUBLIC_IP}:8000' > frontend/.env.production.local"
echo "  npm run build && sudo systemctl restart legal-frontend"
