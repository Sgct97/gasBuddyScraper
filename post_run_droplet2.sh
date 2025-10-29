#!/bin/bash
# Auto Merge & Dedup - Droplet 2
# Runs continuously, waits for both droplets to finish, then merges CSVs

CHECK_INTERVAL=60  # Check every 60 seconds
MERGED_LOG="/opt/gasbuddy/merged_runs.log"
INCOMING_DIR="/opt/gasbuddy/incoming"

cd /opt/gasbuddy || exit 1

echo "=================================================================="
echo "🔄 AUTO MERGE WATCHER - DROPLET 2"
echo "=================================================================="
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Incoming directory: $INCOMING_DIR"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "=================================================================="
echo ""

# Create directories
mkdir -p "$INCOMING_DIR"
mkdir -p "merged"
touch "$MERGED_LOG"

while true; do
    # Check if Droplet 2 has finished its run
    if [ -f "current_run_droplet2.txt" ]; then
        RUN_ID=$(cat current_run_droplet2.txt)
        DROPLET2_COMPLETE="runs/complete_${RUN_ID}_droplet2.txt"
        DROPLET1_TRANSFER_MARKER="$INCOMING_DIR/transferred_${RUN_ID}_droplet1.txt"
        
        # Check if both droplets are done AND not already merged
        if [ -f "$DROPLET2_COMPLETE" ] && [ -f "$DROPLET1_TRANSFER_MARKER" ] && ! grep -q "$RUN_ID" "$MERGED_LOG" 2>/dev/null; then
            echo "[$(date '+%H:%M:%S')] ✅ Both droplets ready for RUN_ID: $RUN_ID"
            echo ""
            
            # Extract CSV filenames
            DROPLET2_CSV=$(grep "csv_file=" "$DROPLET2_COMPLETE" | cut -d'=' -f2)
            DROPLET1_CSV=$(ls $INCOMING_DIR/gasbuddy_droplet1_${RUN_ID}.csv 2>/dev/null | head -1)
            
            if [ -f "$DROPLET2_CSV" ] && [ -f "$DROPLET1_CSV" ]; then
                echo "   Droplet 1 CSV: $(basename $DROPLET1_CSV)"
                echo "   Droplet 2 CSV: $(basename $DROPLET2_CSV)"
                echo ""
                
                # Run merge script
                echo "   🔄 Starting merge & deduplication..."
                MERGE_OUTPUT="merged/gasbuddy_merged_${RUN_ID}.csv"
                
                if python3 merge_csvs.py "$DROPLET1_CSV" "$DROPLET2_CSV" "$MERGE_OUTPUT"; then
                    echo ""
                    echo "   ✅ Merge complete!"
                    echo "   📁 Output: $MERGE_OUTPUT"
                    
                    # Count final stations
                    FINAL_COUNT=$(wc -l < "$MERGE_OUTPUT")
                    FINAL_COUNT=$((FINAL_COUNT - 1))  # Exclude header
                    
                    echo "   📊 Final station count: $FINAL_COUNT"
                    
                    # Log this merge
                    echo "$RUN_ID|$(date --iso-8601=seconds)|$MERGE_OUTPUT|$FINAL_COUNT" >> "$MERGED_LOG"
                    
                    # Create completion marker for email system
                    MERGE_COMPLETE="merged/complete_${RUN_ID}.txt"
                    cat > "$MERGE_COMPLETE" <<EOF
run_id=$RUN_ID
completed_at=$(date --iso-8601=seconds)
merged_csv=$MERGE_OUTPUT
droplet1_csv=$DROPLET1_CSV
droplet2_csv=$DROPLET2_CSV
total_stations=$FINAL_COUNT
EOF
                    
                    echo "   ✅ Merge marked complete: $MERGE_COMPLETE"
                    echo ""
                    echo "   🎯 Ready for email review!"
                    echo ""
                    
                    # Archive and cleanup on both droplets
                    echo "   📦 Archiving completed run on both droplets..."
                    ssh root@134.199.198.81 "cd /opt/gasbuddy && bash archive_completed_run.sh $RUN_ID 1" &
                    bash archive_completed_run.sh $RUN_ID 2
                    wait
                    echo "   ✅ Both droplets archived and ready for next run"
                    echo ""
                else
                    echo "   ❌ Merge failed! Will retry..."
                    echo ""
                fi
            else
                echo "   ⚠️  CSV files not found!"
                echo "   D1: $DROPLET1_CSV ($([ -f "$DROPLET1_CSV" ] && echo "exists" || echo "missing"))"
                echo "   D2: $DROPLET2_CSV ($([ -f "$DROPLET2_CSV" ] && echo "exists" || echo "missing"))"
                echo ""
            fi
        fi
    fi
    
    sleep $CHECK_INTERVAL
done

