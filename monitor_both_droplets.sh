#!/bin/bash
# Monitor both droplets simultaneously in split screen

DROPLET1_IP="134.199.198.81"
DROPLET2_IP="129.212.186.232"

echo "=================================================================="
echo "🔵🟢 DUAL DROPLET MONITOR"
echo "=================================================================="
echo ""
echo "Press Ctrl+C to exit"
echo ""

while true; do
    clear
    echo "=================================================================="
    echo "🔵 DROPLET 1 (134.199.198.81) - ZIPs 1-20,743"
    echo "=================================================================="
    
    ssh root@$DROPLET1_IP << 'EOF' 2>/dev/null
cd /opt/gasbuddy 2>/dev/null || exit 1
if [ -f "completed_zips_droplet1.txt" ]; then
    COMPLETED=$(wc -l < completed_zips_droplet1.txt)
    FAILED=$(wc -l < failed_zips_droplet1.txt 2>/dev/null || echo 0)
    PCT=$(echo "scale=1; $COMPLETED / 20743 * 100" | bc)
    echo "Progress: $COMPLETED / 20,743 ZIPs ($PCT%)"
    echo "Failed: $FAILED"
    
    # Check if scraper is running
    if pgrep -f "python3.*production_scraper.py" > /dev/null; then
        echo "Status: 🟢 RUNNING"
        # Show last 3 log lines
        echo ""
        echo "Recent activity:"
        tail -3 data/gasbuddy_droplet1_*.csv 2>/dev/null | head -3 | cut -d',' -f1-4 | sed 's/^/  /' || echo "  (no data yet)"
    else
        echo "Status: 🔴 STOPPED"
    fi
else
    echo "Status: ⚪ Not started"
fi
EOF
    
    echo ""
    echo "=================================================================="
    echo "🟢 DROPLET 2 (129.212.186.232) - ZIPs 20,744-41,487"
    echo "=================================================================="
    
    ssh root@$DROPLET2_IP << 'EOF' 2>/dev/null
cd /opt/gasbuddy 2>/dev/null || exit 1
if [ -f "completed_zips_droplet2.txt" ]; then
    COMPLETED=$(wc -l < completed_zips_droplet2.txt)
    FAILED=$(wc -l < failed_zips_droplet2.txt 2>/dev/null || echo 0)
    PCT=$(echo "scale=1; $COMPLETED / 20744 * 100" | bc)
    echo "Progress: $COMPLETED / 20,744 ZIPs ($PCT%)"
    echo "Failed: $FAILED"
    
    # Check if scraper is running
    if pgrep -f "python3.*production_scraper.py" > /dev/null; then
        echo "Status: 🟢 RUNNING"
        # Show last 3 log lines
        echo ""
        echo "Recent activity:"
        tail -3 data/gasbuddy_droplet2_*.csv 2>/dev/null | head -3 | cut -d',' -f1-4 | sed 's/^/  /' || echo "  (no data yet)"
    else
        echo "Status: 🔴 STOPPED"
    fi
else
    echo "Status: ⚪ Not started"
fi
EOF
    
    echo ""
    echo "=================================================================="
    echo "Updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Refreshing in 10 seconds... (Ctrl+C to exit)"
    echo "=================================================================="
    
    sleep 10
done

