#!/bin/bash
# Enterprise Production Deployment Script
# Deploys GasBuddy scraper to production server

SERVER_IP="134.199.198.81"
SERVER_USER="root"
DEPLOY_DIR="/opt/gasbuddy"
REPO_URL="https://github.com/Sgct97/gasBuddyScraper.git"

echo "=========================================="
echo "GASBUDDY SCRAPER - PRODUCTION DEPLOYMENT"
echo "=========================================="
echo "Target: $SERVER_USER@$SERVER_IP"
echo "Deploy dir: $DEPLOY_DIR"
echo ""

# Test SSH connection
echo "Testing SSH connection..."
ssh -o ConnectTimeout=10 $SERVER_USER@$SERVER_IP "echo 'SSH connection successful'" || {
    echo "❌ SSH connection failed. Please check:"
    echo "   1. Server IP is correct"
    echo "   2. SSH key is configured"
    echo "   3. Server is running"
    exit 1
}

echo "✅ SSH connection verified"
echo ""

# Deploy application
echo "Deploying application..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
    set -e
    
    # Install system dependencies
    echo "📦 Installing system dependencies..."
    apt-get update -qq
    apt-get install -y python3 python3-pip git curl -qq
    
    # Create deployment directory
    echo "📁 Creating deployment directory..."
    mkdir -p /opt/gasbuddy
    cd /opt/gasbuddy
    
    # Clone or update repository
    if [ -d ".git" ]; then
        echo "🔄 Updating existing repository..."
        git fetch --all
        git reset --hard origin/main
    else
        echo "📥 Cloning repository..."
        git clone https://github.com/Sgct97/gasBuddyScraper.git .
    fi
    
    # Install Python dependencies
    echo "🐍 Installing Python dependencies..."
    pip3 install --quiet curl_cffi
    
    # Create logs directory
    mkdir -p /opt/gasbuddy/logs
    
    # Create data directory for CSVs
    mkdir -p /opt/gasbuddy/data
    
    echo "✅ Application deployed successfully"
ENDSSH

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "  1. Upload monitoring script: scp monitor.py $SERVER_USER@$SERVER_IP:$DEPLOY_DIR/"
echo "  2. Upload cron wrapper: scp cron_wrapper.sh $SERVER_USER@$SERVER_IP:$DEPLOY_DIR/"
echo "  3. Set up cron jobs"
echo ""

