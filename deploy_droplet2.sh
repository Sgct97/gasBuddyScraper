#!/bin/bash
# Deploy to Droplet 2 (Secondary)
# IP: 129.212.186.232
# ZIPs: 20,744-41,487
# Proxies: 8011-8020

set -e

DROPLET_IP="129.212.186.232"
REMOTE_DIR="/opt/gasbuddy"

echo "======================================================================"
echo "🚀 DEPLOYING TO DROPLET 2 (Secondary)"
echo "======================================================================"
echo "IP: $DROPLET_IP"
echo "ZIP Range: 20,744-41,487 (second half)"
echo "Proxies: isp.oxylabs.io:8011-8020"
echo ""

# Create directory structure
echo "1. Setting up directory structure..."
ssh root@$DROPLET_IP << 'EOF'
mkdir -p /opt/gasbuddy/logs
mkdir -p /opt/gasbuddy/data
chmod 755 /opt/gasbuddy
EOF

# Upload dependencies
echo ""
echo "2. Uploading dependencies..."
scp requirements.txt root@$DROPLET_IP:$REMOTE_DIR/

# Install Python packages
echo ""
echo "3. Installing Python packages..."
ssh root@$DROPLET_IP << 'EOF'
cd /opt/gasbuddy
apt-get update -qq
apt-get install -y python3-pip python3-venv 2>&1 | grep -v "^Reading\|^Building"
pip3 install --quiet -r requirements.txt
EOF

# Upload scraper files
echo ""
echo "4. Uploading scraper files..."
scp production_scraper_droplet2.py root@$DROPLET_IP:$REMOTE_DIR/production_scraper.py
scp droplet2_zips.txt root@$DROPLET_IP:$REMOTE_DIR/
scp write_csv_incremental.py root@$DROPLET_IP:$REMOTE_DIR/
scp full_graphql_query.txt root@$DROPLET_IP:$REMOTE_DIR/

# Verify files
echo ""
echo "5. Verifying deployment..."
ssh root@$DROPLET_IP << 'EOF'
cd /opt/gasbuddy
echo "✅ Files present:"
ls -lh production_scraper.py droplet2_zips.txt write_csv_incremental.py full_graphql_query.txt | awk '{print "   " $9 " (" $5 ")"}'

echo ""
echo "✅ ZIP file check:"
wc -l droplet2_zips.txt

echo ""
echo "✅ Syntax check:"
python3 -c "import production_scraper" && echo "   No syntax errors"
EOF

echo ""
echo "======================================================================"
echo "✅ DROPLET 2 DEPLOYMENT COMPLETE"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Test with: ssh root@$DROPLET_IP 'cd /opt/gasbuddy && python3 production_scraper.py'"
echo "  2. Monitor: ssh root@$DROPLET_IP 'cd /opt/gasbuddy && tail -f logs/scraper_droplet2.log'"
echo ""

