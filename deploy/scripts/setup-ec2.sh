#!/bin/bash
# EC2 Initial Setup Script
# Run this on a fresh Ubuntu 22.04 EC2 instance
# Usage: chmod +x setup-ec2.sh && ./setup-ec2.sh

set -e  # Exit on error

echo "=================================================="
echo "EC2 Setup for Legal Case Search System"
echo "=================================================="

echo ""
echo "=== Updating system packages ==="
sudo apt update && sudo apt upgrade -y

echo ""
echo "=== Installing Python 3 and venv ==="
sudo apt install python3 python3-venv python3-pip -y

echo ""
echo "=== Installing Node.js 18 LTS ==="
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

echo ""
echo "=== Installing git ==="
sudo apt install git -y

echo ""
echo "=== Verifying installations ==="
echo "Python: $(python3 --version)"
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"
echo "git: $(git --version)"

echo ""
echo "=================================================="
echo "✓ EC2 setup complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Clone your repository:"
echo "     git clone https://github.com/YOUR_USER/Legal-Judgement-Retrieval.git"
echo ""
echo "  2. Create .env file:"
echo "     cd Legal-Judgement-Retrieval"
echo "     cp deploy/.env.example .env"
echo "     nano .env  # Add your API keys"
echo ""
echo "  3. Run deployment:"
echo "     chmod +x deploy/scripts/*.sh"
echo "     ./deploy/scripts/deploy.sh"
