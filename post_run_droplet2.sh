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
    # Find most recent unmerged completion from Droplet 2
    DROPLET2_COMPLETE=$(ls -t runs/complete_*_droplet2.txt 2>/dev/null | head -1)
    
    if [ -n "$DROPLET2_COMPLETE" ]; then
        # Extract Droplet 2's RUN_ID
        RUN_ID_D2=$(basename "$DROPLET2_COMPLETE" | sed 's/complete_//;s/_droplet2.txt//')
        
        # Find most recent transfer from Droplet 1
        DROPLET1_TRANSFER_MARKER=$(ls -t $INCOMING_DIR/transferred_*_droplet1.txt 2>/dev/null | head -1)
        
        if [ -n "$DROPLET1_TRANSFER_MARKER" ]; then
            # Extract Droplet 1's RUN_ID from transfer marker
            RUN_ID_D1=$(basename "$DROPLET1_TRANSFER_MARKER" | sed 's/transferred_//;s/_droplet1.txt//')
            
            # Create unique merge ID from both RUN_IDs
            MERGE_ID="${RUN_ID_D1}_${RUN_ID_D2}"
            
            # Check if this pair has already been merged
            if ! grep -q "$MERGE_ID" "$MERGED_LOG" 2>/dev/null; then
                echo "[$(date '+%H:%M:%S')] ✅ Both droplets ready!"
                echo "   Droplet 1 RUN_ID: $RUN_ID_D1"
                echo "   Droplet 2 RUN_ID: $RUN_ID_D2"
                echo ""
                
                # Extract CSV filenames
                DROPLET2_CSV=$(grep "csv_file=" "$DROPLET2_COMPLETE" | cut -d'=' -f2)
                DROPLET1_CSV=$(ls $INCOMING_DIR/gasbuddy_droplet1_${RUN_ID_D1}.csv 2>/dev/null | head -1)
            
            if [ -f "$DROPLET2_CSV" ] && [ -f "$DROPLET1_CSV" ]; then
                echo "   Droplet 1 CSV: $(basename $DROPLET1_CSV)"
                echo "   Droplet 2 CSV: $(basename $DROPLET2_CSV)"
                echo ""
                
                # Run merge script
                echo "   🔄 Starting merge & deduplication..."
                MERGE_OUTPUT="merged/gasbuddy_merged_${MERGE_ID}.csv"
                
                if python3 merge_csvs.py "$DROPLET1_CSV" "$DROPLET2_CSV" "$MERGE_OUTPUT"; then
                    echo ""
                    echo "   ✅ Merge complete!"
                    echo "   📁 Output: $MERGE_OUTPUT"
                    
                    # Count final stations
                    FINAL_COUNT=$(wc -l < "$MERGE_OUTPUT")
                    FINAL_COUNT=$((FINAL_COUNT - 1))  # Exclude header
                    
                    echo "   📊 Final station count: $FINAL_COUNT"
                    
                    # Log this merge
                    echo "$MERGE_ID|$(date --iso-8601=seconds)|$MERGE_OUTPUT|$FINAL_COUNT" >> "$MERGED_LOG"
                    
                    # Create completion marker for email system
                    MERGE_COMPLETE="merged/complete_${MERGE_ID}.txt"
                    cat > "$MERGE_COMPLETE" <<EOF
merge_id=$MERGE_ID
run_id_droplet1=$RUN_ID_D1
run_id_droplet2=$RUN_ID_D2
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
                    ssh root@134.199.198.81 "cd /opt/gasbuddy && bash archive_completed_run.sh $RUN_ID_D1 1" &
                    bash archive_completed_run.sh $RUN_ID_D2 2
                    wait
                    
                    # Clean up incoming directory (D1's transferred files)
                    echo "   🧹 Cleaning incoming directory..."
                    rm -f "$INCOMING_DIR/gasbuddy_droplet1_${RUN_ID_D1}.csv" 2>/dev/null && echo "      ✅ D1 CSV removed"
                    rm -f "$INCOMING_DIR/transferred_${RUN_ID_D1}_droplet1.txt" 2>/dev/null && echo "      ✅ Transfer marker removed"
                    
                    echo "   ✅ Both droplets archived and ready for next run"
                    echo ""
                    
                    # Trigger review email
                    echo "   📧 Triggering review email..."
                    STATION_COUNT=$(wc -l < "$MERGE_OUTPUT" | tail -1)
                    STATION_COUNT=$((STATION_COUNT - 1))  # Subtract header
                    python3 /opt/gasbuddy/send_review_email.py "$MERGE_ID" "$MERGE_OUTPUT" "$STATION_COUNT" && echo "      ✅ Review email sent"
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
    fi
    
    sleep $CHECK_INTERVAL
done

