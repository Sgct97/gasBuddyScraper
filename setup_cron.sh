#!/bin/bash
# Setup production cron jobs for GasBuddy scraper
# Run this on each droplet to configure scheduled tasks

DROPLET_ID=${1:-1}  # Default to 1 if not specified

echo "=================================================================="
echo "⏰ CRON JOB SETUP - DROPLET $DROPLET_ID"
echo "=================================================================="
echo ""

if [ "$DROPLET_ID" != "1" ] && [ "$DROPLET_ID" != "2" ]; then
    echo "❌ Invalid droplet ID. Usage: ./setup_cron.sh [1|2]"
    exit 1
fi

echo "Setting up cron jobs for Droplet $DROPLET_ID..."
echo ""

# Create cron schedule
CRON_FILE="/tmp/gasbuddy_cron_$DROPLET_ID.txt"

cat > "$CRON_FILE" << 'EOF'
# GasBuddy Scraper - Production Cron Jobs
# Generated automatically - DO NOT EDIT MANUALLY

# Set environment variables
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
DROPLET_ID=DROPLET_ID_PLACEHOLDER

# ============================================================================
# SCRAPER RUNS - Twice daily with randomized start times
# ============================================================================
# Morning run: 6:00 AM - 7:00 AM (random minute)
RANDOM_MIN_1 * 6 * * * cd /opt/gasbuddy && sleep $((RANDOM \% 3600)) && /usr/bin/python3 production_scraper_dropletDROPLET_ID_PLACEHOLDER.py >> logs/cron_scraper.log 2>&1

# Evening run: 6:00 PM - 7:00 PM (random minute)
RANDOM_MIN_2 * 18 * * * cd /opt/gasbuddy && sleep $((RANDOM \% 3600)) && /usr/bin/python3 production_scraper_dropletDROPLET_ID_PLACEHOLDER.py >> logs/cron_scraper.log 2>&1

# ============================================================================
# HEALTH MONITORING - Every 5 minutes
# ============================================================================
*/5 * * * * cd /opt/gasbuddy && DROPLET_ID=DROPLET_ID_PLACEHOLDER /usr/bin/python3 health_check.py >> logs/cron_health.log 2>&1

# ============================================================================
# WATCHDOG - Every 2 minutes (auto-restart dead scrapers)
# ============================================================================
*/2 * * * * cd /opt/gasbuddy && DROPLET_ID=DROPLET_ID_PLACEHOLDER /usr/bin/python3 watchdog.py >> logs/cron_watchdog.log 2>&1

# ============================================================================
# POST-RUN AUTOMATION (Droplet-specific)
# ============================================================================
EOF

# Add droplet-specific jobs
if [ "$DROPLET_ID" = "1" ]; then
    cat >> "$CRON_FILE" << 'EOF'
# Droplet 1: Auto-transfer to Droplet 2 (runs continuously in background)
# Start at boot and keep running
@reboot cd /opt/gasbuddy && nohup ./post_run_droplet1.sh >> logs/post_run_droplet1.log 2>&1 &
EOF
elif [ "$DROPLET_ID" = "2" ]; then
    cat >> "$CRON_FILE" << 'EOF'
# Droplet 2: Auto-merge CSVs (runs continuously in background)
@reboot cd /opt/gasbuddy && nohup ./post_run_droplet2.sh >> logs/post_run_droplet2.log 2>&1 &

# Droplet 2: Send review emails (runs continuously in background)
@reboot cd /opt/gasbuddy && nohup /usr/bin/python3 send_review_email.py >> logs/send_review_email.log 2>&1 &

# Droplet 2: Approval watcher (checks every 5 min via continuous process)
@reboot cd /opt/gasbuddy && nohup /usr/bin/python3 approval_watcher.py >> logs/approval_watcher.log 2>&1 &

# Droplet 2: Client delivery (checks every 60s via continuous process)
@reboot cd /opt/gasbuddy && nohup /usr/bin/python3 client_delivery.py >> logs/client_delivery.log 2>&1 &
EOF
fi

# Replace placeholders
sed -i "s/DROPLET_ID_PLACEHOLDER/$DROPLET_ID/g" "$CRON_FILE"

# Generate random minutes for scraper runs (0-59)
RANDOM_MIN_1=$((RANDOM % 60))
RANDOM_MIN_2=$((RANDOM % 60))
sed -i "s/RANDOM_MIN_1/$RANDOM_MIN_1/g" "$CRON_FILE"
sed -i "s/RANDOM_MIN_2/$RANDOM_MIN_2/g" "$CRON_FILE"

echo "📋 Cron schedule generated:"
echo ""
cat "$CRON_FILE"
echo ""
echo "=================================================================="
echo ""

# Ask for confirmation
echo "⚠️  This will REPLACE your existing crontab!"
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Setup cancelled"
    rm "$CRON_FILE"
    exit 0
fi

echo ""

# Backup existing crontab
echo "💾 Backing up existing crontab..."
crontab -l > "/opt/gasbuddy/crontab_backup_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true

# Install new crontab
echo "📥 Installing new crontab..."
crontab "$CRON_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Crontab installed successfully!"
else
    echo "❌ Failed to install crontab"
    rm "$CRON_FILE"
    exit 1
fi

# Cleanup
rm "$CRON_FILE"

# Show installed crontab
echo ""
echo "=================================================================="
echo "✅ CRON SETUP COMPLETE - DROPLET $DROPLET_ID"
echo "=================================================================="
echo ""
echo "Installed schedule:"
echo ""
crontab -l
echo ""
echo "=================================================================="
echo ""
echo "Schedule summary:"
echo "  🔄 Scrapers: 2x daily (6-7am, 6-7pm) with random start"
echo "  💓 Health checks: Every 5 minutes"
echo "  🐕 Watchdog: Every 2 minutes"
if [ "$DROPLET_ID" = "1" ]; then
    echo "  📤 Auto-transfer: Continuous (starts at boot)"
elif [ "$DROPLET_ID" = "2" ]; then
    echo "  🔄 Auto-merge: Continuous (starts at boot)"
    echo "  📧 Email systems: Continuous (starts at boot)"
fi
echo ""
echo "Next steps:"
echo "  1. Verify cron is running: systemctl status cron"
echo "  2. Monitor cron logs: tail -f /opt/gasbuddy/logs/cron_*.log"
echo "  3. Test manually: cd /opt/gasbuddy && ./watchdog.py"
echo ""
echo "To start background processes now (don't wait for reboot):"
if [ "$DROPLET_ID" = "1" ]; then
    echo "  cd /opt/gasbuddy && nohup ./post_run_droplet1.sh >> logs/post_run_droplet1.log 2>&1 &"
elif [ "$DROPLET_ID" = "2" ]; then
    echo "  cd /opt/gasbuddy && nohup ./post_run_droplet2.sh >> logs/post_run_droplet2.log 2>&1 &"
    echo "  cd /opt/gasbuddy && nohup python3 send_review_email.py >> logs/send_review_email.log 2>&1 &"
    echo "  cd /opt/gasbuddy && nohup python3 approval_watcher.py >> logs/approval_watcher.log 2>&1 &"
    echo "  cd /opt/gasbuddy && nohup python3 client_delivery.py >> logs/client_delivery.log 2>&1 &"
fi
echo ""

