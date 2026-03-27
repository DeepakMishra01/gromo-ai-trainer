#!/bin/bash
# ============================================================
# GroMo AI Trainer — AWS EC2 Setup Script
# Run this on a fresh Ubuntu 22.04 EC2 instance
# Usage: bash setup.sh
# ============================================================

set -e

echo "=========================================="
echo "  GroMo AI Trainer — Server Setup"
echo "=========================================="

# 1. System updates
echo "[1/8] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install Python 3.11, Node.js 20, nginx, git
echo "[2/8] Installing Python, Node.js, Nginx..."
sudo apt install -y python3 python3-pip python3-venv nginx git curl unzip

# Install Node.js 20 via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install LibreOffice (needed for PPTX to PDF conversion)
echo "[3/8] Installing LibreOffice (for video generation)..."
sudo apt install -y libreoffice-core libreoffice-impress

# 3. Clone the repository
echo "[4/8] Cloning repository..."
cd /home/ubuntu
if [ -d "gromo-ai-trainer" ]; then
    cd gromo-ai-trainer && git pull origin main
else
    git clone https://github.com/DeepakMishra01/gromo-ai-trainer.git
    cd gromo-ai-trainer
fi

# 4. Backend setup
echo "[5/8] Setting up Python backend..."
cd /home/ubuntu/gromo-ai-trainer/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
deactivate

# 5. Frontend build
echo "[6/8] Building React frontend..."
cd /home/ubuntu/gromo-ai-trainer/frontend
npm install
npm run build

# 6. Setup Nginx
echo "[7/8] Configuring Nginx..."
sudo cp /home/ubuntu/gromo-ai-trainer/deploy/nginx.conf /etc/nginx/sites-available/gromo
sudo ln -sf /etc/nginx/sites-available/gromo /etc/nginx/sites-enabled/gromo
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# 7. Setup systemd service for backend
echo "[8/8] Setting up backend service..."
sudo cp /home/ubuntu/gromo-ai-trainer/deploy/gromo-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gromo-backend
sudo systemctl start gromo-backend

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "  Backend:  Running on port 8000 (gunicorn)"
echo "  Frontend: Served by Nginx"
echo "  URL:      http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'YOUR_EC2_IP')"
echo ""
echo "  IMPORTANT: Create your .env file:"
echo "  nano /home/ubuntu/gromo-ai-trainer/backend/.env"
echo "  Then restart: sudo systemctl restart gromo-backend"
echo ""
echo "  View logs: sudo journalctl -u gromo-backend -f"
echo "=========================================="
