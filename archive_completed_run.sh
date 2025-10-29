#!/bin/bash
# Archive completed run and prepare for next run
# Call this after merge completes successfully on Droplet 2

RUN_ID=$1
DROPLET=$2  # "1" or "2"

if [ -z "$RUN_ID" ] || [ -z "$DROPLET" ]; then
    echo "Usage: $0 <RUN_ID> <DROPLET_NUMBER>"
    exit 1
fi

cd /opt/gasbuddy || exit 1

echo "=================================================================="
echo "📦 ARCHIVING RUN: $RUN_ID (Droplet $DROPLET)"
echo "=================================================================="
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Create archive directory structure: archive/YYYY/MM/
YEAR=$(echo $RUN_ID | cut -c1-4)
MONTH=$(echo $RUN_ID | cut -c5-6)
ARCHIVE_DIR="archive/$YEAR/$MONTH"
mkdir -p "$ARCHIVE_DIR"

echo "📁 Archive location: $ARCHIVE_DIR"
echo ""

# Move files to archive
echo "Moving files..."
mv "data/gasbuddy_droplet${DROPLET}_${RUN_ID}.csv" "$ARCHIVE_DIR/" 2>/dev/null && echo "  ✅ CSV moved"
mv "runs/progress_${RUN_ID}_droplet${DROPLET}.pkl" "$ARCHIVE_DIR/" 2>/dev/null && echo "  ✅ Progress file moved"
mv "runs/completed_${RUN_ID}_droplet${DROPLET}.txt" "$ARCHIVE_DIR/" 2>/dev/null && echo "  ✅ Completed list moved"
mv "runs/failed_${RUN_ID}_droplet${DROPLET}.txt" "$ARCHIVE_DIR/" 2>/dev/null && echo "  ✅ Failed list moved"
mv "runs/complete_${RUN_ID}_droplet${DROPLET}.txt" "$ARCHIVE_DIR/" 2>/dev/null && echo "  ✅ Completion marker moved"

# Remove current_run marker (allows next run to start fresh)
if [ -f "current_run_droplet${DROPLET}.txt" ]; then
    CURRENT_RUN=$(cat "current_run_droplet${DROPLET}.txt")
    if [ "$CURRENT_RUN" == "$RUN_ID" ]; then
        rm -f "current_run_droplet${DROPLET}.txt"
        echo "  ✅ Current run marker removed (ready for new run)"
    else
        echo "  ⚠️  Current run marker points to different RUN_ID: $CURRENT_RUN"
    fi
fi

# Log to audit trail
echo "$RUN_ID|$(date --iso-8601=seconds)|Droplet$DROPLET|$ARCHIVE_DIR" >> archive_log.txt

echo ""
echo "=================================================================="
echo "✅ ARCHIVE COMPLETE"
echo "=================================================================="
echo "Run $RUN_ID has been archived to: $ARCHIVE_DIR"
echo "Next scraper run will start fresh with new RUN_ID"
echo ""

