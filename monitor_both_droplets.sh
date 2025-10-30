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

# System stats
MEM_USED=$(free -h | grep Mem | awk '{print $3}')
MEM_TOTAL=$(free -h | grep Mem | awk '{print $2}')
MEM_PCT=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')
CPU_PCT=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)

echo "💾 Memory: $MEM_USED / $MEM_TOTAL (${MEM_PCT}%)"
echo "🖥️  CPU: ${CPU_PCT}%"
echo ""

# Check if there's a current run
if [ -f "current_run_droplet1.txt" ]; then
    RUN_ID=$(cat current_run_droplet1.txt)
    echo "📋 Run ID: $RUN_ID"
    
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
    PCT=$(awk "BEGIN {printf \"%.1f\", ($COMPLETED/$TOTAL)*100}")
    REMAINING=$((TOTAL - COMPLETED))
    
    echo "📊 Progress: $COMPLETED / $TOTAL ZIPs (${PCT}%)"
    echo "⏳ Remaining: $REMAINING ZIPs"
    echo "❌ Failed: $FAILED"
    
    # Calculate speed if progress file has timestamp
    if [ -f "runs/progress_${RUN_ID}_droplet1.pkl" ]; then
        START_TIME=$(stat -c %Y "runs/progress_${RUN_ID}_droplet1.pkl" 2>/dev/null || stat -f %B "runs/progress_${RUN_ID}_droplet1.pkl" 2>/dev/null)
        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - START_TIME))
        if [ $ELAPSED -gt 0 ]; then
            SPEED=$(awk "BEGIN {printf \"%.1f\", ($COMPLETED*60/$ELAPSED)}")
            echo "⚡ Speed: $SPEED ZIPs/min"
            if [ $COMPLETED -gt 0 ]; then
                ETA_MIN=$(awk "BEGIN {printf \"%.0f\", ($REMAINING/$SPEED)}")
                ETA_HR=$(awk "BEGIN {printf \"%.1f\", ($ETA_MIN/60)}")
                echo "🕐 ETA: ${ETA_HR}h (${ETA_MIN}min)"
            fi
        fi
    fi
    
    # CSV file size
    if [ -f "data/gasbuddy_droplet1_${RUN_ID}.csv" ]; then
        CSV_SIZE=$(ls -lh "data/gasbuddy_droplet1_${RUN_ID}.csv" | awk '{print $5}')
        echo "📁 CSV: $CSV_SIZE"
    fi
    
    # Check if scraper is running
    echo ""
    if pgrep -f "python3.*production_scraper_droplet1" > /dev/null; then
        THREADS=$(ps -eLf | grep production_scraper_droplet1 | grep -v grep | wc -l)
        echo "Status: 🟢 RUNNING ($THREADS threads)"
    else
        # Check if run is complete
        if [ -f "runs/complete_${RUN_ID}_droplet1.txt" ]; then
            echo "Status: ✅ COMPLETE"
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

# System stats
MEM_USED=$(free -h | grep Mem | awk '{print $3}')
MEM_TOTAL=$(free -h | grep Mem | awk '{print $2}')
MEM_PCT=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')
CPU_PCT=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)

echo "💾 Memory: $MEM_USED / $MEM_TOTAL (${MEM_PCT}%)"
echo "🖥️  CPU: ${CPU_PCT}%"
echo ""

# Check if there's a current run
if [ -f "current_run_droplet2.txt" ]; then
    RUN_ID=$(cat current_run_droplet2.txt)
    echo "📋 Run ID: $RUN_ID"
    
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
    PCT=$(awk "BEGIN {printf \"%.1f\", ($COMPLETED/$TOTAL)*100}")
    REMAINING=$((TOTAL - COMPLETED))
    
    echo "📊 Progress: $COMPLETED / $TOTAL ZIPs (${PCT}%)"
    echo "⏳ Remaining: $REMAINING ZIPs"
    echo "❌ Failed: $FAILED"
    
    # Calculate speed if progress file has timestamp
    if [ -f "runs/progress_${RUN_ID}_droplet2.pkl" ]; then
        START_TIME=$(stat -c %Y "runs/progress_${RUN_ID}_droplet2.pkl" 2>/dev/null || stat -f %B "runs/progress_${RUN_ID}_droplet2.pkl" 2>/dev/null)
        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - START_TIME))
        if [ $ELAPSED -gt 0 ]; then
            SPEED=$(awk "BEGIN {printf \"%.1f\", ($COMPLETED*60/$ELAPSED)}")
            echo "⚡ Speed: $SPEED ZIPs/min"
            if [ $COMPLETED -gt 0 ]; then
                ETA_MIN=$(awk "BEGIN {printf \"%.0f\", ($REMAINING/$SPEED)}")
                ETA_HR=$(awk "BEGIN {printf \"%.1f\", ($ETA_MIN/60)}")
                echo "🕐 ETA: ${ETA_HR}h (${ETA_MIN}min)"
            fi
        fi
    fi
    
    # CSV file size
    if [ -f "data/gasbuddy_droplet2_${RUN_ID}.csv" ]; then
        CSV_SIZE=$(ls -lh "data/gasbuddy_droplet2_${RUN_ID}.csv" | awk '{print $5}')
        echo "📁 CSV: $CSV_SIZE"
    fi
    
    # Check if scraper is running
    echo ""
    if pgrep -f "python3.*production_scraper_droplet2" > /dev/null; then
        THREADS=$(ps -eLf | grep production_scraper_droplet2 | grep -v grep | wc -l)
        echo "Status: 🟢 RUNNING ($THREADS threads)"
    else
        # Check if run is complete
        if [ -f "runs/complete_${RUN_ID}_droplet2.txt" ]; then
            echo "Status: ✅ COMPLETE"
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
    echo "📊 COMBINED PROGRESS"
    echo "=================================================================="
    
    # Get combined stats
    D1_COMPLETED=$(ssh root@$DROPLET1_IP 'cd /opt/gasbuddy && if [ -f current_run_droplet1.txt ]; then RUN_ID=$(cat current_run_droplet1.txt); wc -l < runs/completed_${RUN_ID}_droplet1.txt 2>/dev/null || echo 0; else echo 0; fi' 2>/dev/null)
    D2_COMPLETED=$(ssh root@$DROPLET2_IP 'cd /opt/gasbuddy && if [ -f current_run_droplet2.txt ]; then RUN_ID=$(cat current_run_droplet2.txt); wc -l < runs/completed_${RUN_ID}_droplet2.txt 2>/dev/null || echo 0; else echo 0; fi' 2>/dev/null)
    
    TOTAL_COMPLETED=$((D1_COMPLETED + D2_COMPLETED))
    TOTAL_ZIPS=41487
    TOTAL_PCT=$(awk "BEGIN {printf \"%.1f\", ($TOTAL_COMPLETED/$TOTAL_ZIPS)*100}")
    TOTAL_REMAINING=$((TOTAL_ZIPS - TOTAL_COMPLETED))
    
    echo "Total: $TOTAL_COMPLETED / $TOTAL_ZIPS ZIPs (${TOTAL_PCT}%)"
    echo "Remaining: $TOTAL_REMAINING ZIPs"
    
    echo ""
    echo "=================================================================="
    echo "Updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Refreshing in 10 seconds... (Ctrl+C to exit)"
    echo "=================================================================="
    
    sleep 10
done

