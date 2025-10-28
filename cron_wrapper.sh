#!/bin/bash
# Cron Wrapper with Randomized Start Time
# Adds random delay to avoid detection patterns
# Handles logging, monitoring, and auto-download

SCRAPER_DIR="/opt/gasbuddy"
LOG_DIR="$SCRAPER_DIR/logs"
DATA_DIR="$SCRAPER_DIR/data"
CLIENT_HOST="YOUR_LOCAL_IP_OR_HOSTNAME"  # User will need to set this
CLIENT_USER="YOUR_LOCAL_USERNAME"  # User will need to set this
CLIENT_DEST="/path/to/local/gasbuddy/data"  # User will need to set this

# Random delay (0-30 minutes)
RANDOM_DELAY=$((RANDOM % 1800))
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting in $RANDOM_DELAY seconds (randomized delay)"
sleep $RANDOM_DELAY

# Change to scraper directory
cd $SCRAPER_DIR

# Create timestamp
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
RUN_LOG="$LOG_DIR/run_$TIMESTAMP.log"

# Ensure log directory exists
mkdir -p $LOG_DIR
mkdir -p $DATA_DIR

echo "=========================================="  | tee $RUN_LOG
echo "GASBUDDY SCRAPER - AUTOMATED RUN"           | tee -a $RUN_LOG
echo "=========================================="  | tee -a $RUN_LOG
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"      | tee -a $RUN_LOG
echo "Random delay: $RANDOM_DELAY seconds"        | tee -a $RUN_LOG
echo ""                                            | tee -a $RUN_LOG

# Pre-run health check
echo "Running pre-flight health check..." | tee -a $RUN_LOG
python3 monitor.py >> $RUN_LOG 2>&1

# Run the scraper
echo "" | tee -a $RUN_LOG
echo "Starting scraper..." | tee -a $RUN_LOG
echo "" | tee -a $RUN_LOG

START_TIME=$(date +%s)

# Run scraper and capture exit code
python3 production_scraper.py >> $RUN_LOG 2>&1
EXIT_CODE=$?

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(((DURATION % 3600) / 60))

echo "" | tee -a $RUN_LOG
echo "=========================================="  | tee -a $RUN_LOG
echo "SCRAPER COMPLETED"                          | tee -a $RUN_LOG
echo "=========================================="  | tee -a $RUN_LOG
echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')"     | tee -a $RUN_LOG
echo "Duration: ${HOURS}h ${MINUTES}m"            | tee -a $RUN_LOG
echo "Exit code: $EXIT_CODE"                      | tee -a $RUN_LOG
echo ""                                            | tee -a $RUN_LOG

# Post-run health check
echo "Running post-run health check..." | tee -a $RUN_LOG
python3 monitor.py >> $RUN_LOG 2>&1

# Update status
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Scrape completed successfully" | tee -a $RUN_LOG
    
    # Find the most recent CSV file
    LATEST_CSV=$(ls -t $DATA_DIR/gasbuddy_full_*.csv 2>/dev/null | head -1)
    
    if [ -n "$LATEST_CSV" ]; then
        CSV_SIZE=$(du -h "$LATEST_CSV" | cut -f1)
        echo "📊 CSV generated: $(basename $LATEST_CSV) ($CSV_SIZE)" | tee -a $RUN_LOG
        
        # Auto-download to local machine
        if [ -n "$CLIENT_HOST" ] && [ "$CLIENT_HOST" != "YOUR_LOCAL_IP_OR_HOSTNAME" ]; then
            echo "" | tee -a $RUN_LOG
            echo "📥 Auto-downloading to local machine..." | tee -a $RUN_LOG
            
            # Copy CSV to local machine
            scp "$LATEST_CSV" "${CLIENT_USER}@${CLIENT_HOST}:${CLIENT_DEST}/" >> $RUN_LOG 2>&1
            
            if [ $? -eq 0 ]; then
                echo "✅ Download complete: $(basename $LATEST_CSV)" | tee -a $RUN_LOG
            else
                echo "❌ Download failed - manual download required" | tee -a $RUN_LOG
                echo "   Command: scp root@134.199.198.81:$LATEST_CSV /local/path/" | tee -a $RUN_LOG
            fi
        else
            echo "⚠️  Auto-download not configured" | tee -a $RUN_LOG
            echo "   Manual download: scp root@134.199.198.81:$LATEST_CSV /local/path/" | tee -a $RUN_LOG
        fi
        
        # Archive old CSVs (keep last 5)
        echo "" | tee -a $RUN_LOG
        echo "🗄️  Archiving old CSVs..." | tee -a $RUN_LOG
        cd $DATA_DIR
        ls -t gasbuddy_full_*.csv 2>/dev/null | tail -n +6 | while read old_csv; do
            echo "   Removing: $old_csv" | tee -a $RUN_LOG
            rm "$old_csv"
        done
    else
        echo "⚠️  No CSV file generated" | tee -a $RUN_LOG
    fi
else
    echo "❌ Scrape failed with exit code $EXIT_CODE" | tee -a $RUN_LOG
fi

echo "" | tee -a $RUN_LOG
echo "Log file: $RUN_LOG" | tee -a $RUN_LOG
echo "=========================================="  | tee -a $RUN_LOG

# Clean up old logs (keep last 30 days)
find $LOG_DIR -name "run_*.log" -mtime +30 -delete
find $LOG_DIR -name "monitor_*.log" -mtime +30 -delete

exit $EXIT_CODE

