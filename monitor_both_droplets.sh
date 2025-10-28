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

# Check if there's a current run
if [ -f "current_run_droplet1.txt" ]; then
    RUN_ID=$(cat current_run_droplet1.txt)
    echo "Run ID: $RUN_ID"
    
    # Count progress for this specific run
    COMPLETED=0
    FAILED=0
    if [ -f "runs/completed_${RUN_ID}_droplet1.txt" ]; then
        COMPLETED=$(wc -l < "runs/completed_${RUN_ID}_droplet1.txt")
    fi
    if [ -f "runs/failed_${RUN_ID}_droplet1.txt" ]; then
        FAILED=$(wc -l < "runs/failed_${RUN_ID}_droplet1.txt")
    fi
    
    TOTAL=20743
    PCT=$(echo "scale=1; $COMPLETED / $TOTAL * 100" | bc 2>/dev/null || echo "0")
    
    echo "Progress: $COMPLETED / $TOTAL ZIPs ($PCT%)"
    echo "Failed: $FAILED"
    
    # Check if scraper is running
    if pgrep -f "python3.*production_scraper_droplet1" > /dev/null; then
        echo "Status: 🟢 RUNNING"
        
        # Show recent log activity
        echo ""
        echo "Recent activity:"
        tail -3 logs/scraper_run.log 2>/dev/null | grep -E "Rate:|scraping" | sed 's/^/  /' || echo "  (no logs yet)"
    else
        # Check if run is complete
        if [ -f "runs/complete_${RUN_ID}_droplet1.txt" ]; then
            echo "Status: ✅ COMPLETE"
            echo ""
            cat "runs/complete_${RUN_ID}_droplet1.txt" | sed 's/^/  /'
        else
            echo "Status: 🔴 STOPPED (incomplete)"
        fi
    fi
else
    echo "Status: ⚪ No run in progress"
fi
EOF
    
    echo ""
    echo "=================================================================="
    echo "🟢 DROPLET 2 (129.212.186.232) - ZIPs 20,744-41,487"
    echo "=================================================================="
    
    ssh root@$DROPLET2_IP << 'EOF' 2>/dev/null
cd /opt/gasbuddy 2>/dev/null || exit 1

# Check if there's a current run
if [ -f "current_run_droplet2.txt" ]; then
    RUN_ID=$(cat current_run_droplet2.txt)
    echo "Run ID: $RUN_ID"
    
    # Count progress for this specific run
    COMPLETED=0
    FAILED=0
    if [ -f "runs/completed_${RUN_ID}_droplet2.txt" ]; then
        COMPLETED=$(wc -l < "runs/completed_${RUN_ID}_droplet2.txt")
    fi
    if [ -f "runs/failed_${RUN_ID}_droplet2.txt" ]; then
        FAILED=$(wc -l < "runs/failed_${RUN_ID}_droplet2.txt")
    fi
    
    TOTAL=20744
    PCT=$(echo "scale=1; $COMPLETED / $TOTAL * 100" | bc 2>/dev/null || echo "0")
    
    echo "Progress: $COMPLETED / $TOTAL ZIPs ($PCT%)"
    echo "Failed: $FAILED"
    
    # Check if scraper is running
    if pgrep -f "python3.*production_scraper_droplet2" > /dev/null; then
        echo "Status: 🟢 RUNNING"
        
        # Show recent log activity
        echo ""
        echo "Recent activity:"
        tail -3 logs/scraper_run.log 2>/dev/null | grep -E "Rate:|scraping" | sed 's/^/  /' || echo "  (no logs yet)"
    else
        # Check if run is complete
        if [ -f "runs/complete_${RUN_ID}_droplet2.txt" ]; then
            echo "Status: ✅ COMPLETE"
            echo ""
            cat "runs/complete_${RUN_ID}_droplet2.txt" | sed 's/^/  /'
        else
            echo "Status: 🔴 STOPPED (incomplete)"
        fi
    fi
else
    echo "Status: ⚪ No run in progress"
fi
EOF
    
    echo ""
    echo "=================================================================="
    echo "Updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Refreshing in 10 seconds... (Ctrl+C to exit)"
    echo "=================================================================="
    
    sleep 10
done

