#!/bin/bash
# Deploy to Droplet 1 (Primary)
# IP: 134.199.198.81
# ZIPs: 1-20,743
# Proxies: 8001-8010

set -e

DROPLET_IP="134.199.198.81"
REMOTE_DIR="/opt/gasbuddy"

echo "======================================================================"
echo "🚀 DEPLOYING TO DROPLET 1 (Primary)"
echo "======================================================================"
echo "IP: $DROPLET_IP"
echo "ZIP Range: 1-20,743 (first half)"
echo "Proxies: isp.oxylabs.io:8001-8010"
echo ""

# Create backup of existing scraper
echo "1. Creating backup of current scraper..."
ssh root@$DROPLET_IP "cd $REMOTE_DIR && cp production_scraper.py production_scraper_backup_$(date +%Y%m%d_%H%M%S).py 2>/dev/null || true"

# Upload new files
echo ""
echo "2. Uploading new scraper files..."
scp production_scraper_droplet1.py root@$DROPLET_IP:$REMOTE_DIR/production_scraper.py
scp droplet1_zips.txt root@$DROPLET_IP:$REMOTE_DIR/
scp write_csv_incremental.py root@$DROPLET_IP:$REMOTE_DIR/
scp full_graphql_query.txt root@$DROPLET_IP:$REMOTE_DIR/

# Verify files
echo ""
echo "3. Verifying deployment..."
ssh root@$DROPLET_IP << 'EOF'
cd /opt/gasbuddy
echo "✅ Files present:"
ls -lh production_scraper.py droplet1_zips.txt write_csv_incremental.py full_graphql_query.txt | awk '{print "   " $9 " (" $5 ")"}'

echo ""
echo "✅ ZIP file check:"
wc -l droplet1_zips.txt

echo ""
echo "✅ Syntax check:"
python3 -c "import production_scraper" && echo "   No syntax errors"
EOF

echo ""
echo "======================================================================"
echo "✅ DROPLET 1 DEPLOYMENT COMPLETE"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Test with: ssh root@$DROPLET_IP 'cd /opt/gasbuddy && python3 production_scraper.py'"
echo "  2. Monitor: ssh root@$DROPLET_IP 'cd /opt/gasbuddy && tail -f logs/scraper_droplet1.log'"
echo ""

