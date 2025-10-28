#!/bin/bash
# Auto CSV Transfer - Droplet 1 to Droplet 2
# Runs continuously, detects when Droplet 1 finishes, then transfers CSV

DROPLET2_IP="129.212.186.232"
CHECK_INTERVAL=60  # Check every 60 seconds
TRANSFERRED_LOG="/opt/gasbuddy/transferred_runs.log"

cd /opt/gasbuddy || exit 1

echo "=================================================================="
echo "🚀 AUTO TRANSFER WATCHER - DROPLET 1"
echo "=================================================================="
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Target: root@${DROPLET2_IP}:/opt/gasbuddy/incoming/"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "=================================================================="
echo ""

# Keep track of already transferred runs
touch "$TRANSFERRED_LOG"

while true; do
    # Check if there's a current run
    if [ -f "current_run_droplet1.txt" ]; then
        RUN_ID=$(cat current_run_droplet1.txt)
        COMPLETE_FILE="runs/complete_${RUN_ID}_droplet1.txt"
        
        # Check if run is complete AND not already transferred
        if [ -f "$COMPLETE_FILE" ] && ! grep -q "$RUN_ID" "$TRANSFERRED_LOG" 2>/dev/null; then
            echo "[$(date '+%H:%M:%S')] ✅ Run $RUN_ID completed! Starting transfer..."
            
            # Extract CSV filename from complete file
            CSV_FILE=$(grep "csv_file=" "$COMPLETE_FILE" | cut -d'=' -f2)
            
            if [ -f "$CSV_FILE" ]; then
                echo "   CSV: $CSV_FILE"
                
                # Create incoming directory on Droplet 2 if it doesn't exist
                ssh root@$DROPLET2_IP "mkdir -p /opt/gasbuddy/incoming" 2>/dev/null
                
                # Transfer CSV to Droplet 2
                echo "   Transferring..."
                if scp "$CSV_FILE" "root@${DROPLET2_IP}:/opt/gasbuddy/incoming/"; then
                    echo "   ✅ Transfer complete!"
                    
                    # Log this transfer
                    echo "$RUN_ID|$(date --iso-8601=seconds)|$CSV_FILE" >> "$TRANSFERRED_LOG"
                    
                    # Create a transfer marker on Droplet 2
                    ssh root@$DROPLET2_IP "echo 'transferred_at=$(date --iso-8601=seconds)' > /opt/gasbuddy/incoming/transferred_${RUN_ID}_droplet1.txt"
                    
                    echo ""
                else
                    echo "   ❌ Transfer failed! Will retry..."
                    echo ""
                fi
            else
                echo "   ⚠️  CSV file not found: $CSV_FILE"
                echo ""
            fi
        fi
    fi
    
    sleep $CHECK_INTERVAL
done

