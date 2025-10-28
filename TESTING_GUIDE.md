# 🧪 COMPLETE INTEGRATION TESTING GUIDE

## Overview
This guide walks through testing the entire GasBuddy automation system from end to end.

---

## ✅ PRE-DEPLOYMENT CHECKLIST

Before deploying to production:

### 1. Email Configuration
```bash
# On Droplet 2 (or locally)
./setup_email.py
./test_email_flow.py
```

**Expected result:** ✅ All email tests pass

### 2. Deploy All Files to Both Droplets

**Droplet 1:**
```bash
scp production_scraper_droplet1.py droplet1_zips.txt full_graphql_query.txt \
    write_csv_incremental.py post_run_droplet1.sh \
    health_check.py watchdog.py setup_cron.sh archive_old_data.py \
    root@134.199.198.81:/opt/gasbuddy/

ssh root@134.199.198.81 "cd /opt/gasbuddy && chmod +x *.py *.sh"
```

**Droplet 2:**
```bash
scp production_scraper_droplet2.py droplet2_zips.txt full_graphql_query.txt \
    write_csv_incremental.py post_run_droplet2.sh merge_csvs.py \
    send_review_email.py approval_watcher.py client_delivery.py \
    email_utils.py health_check.py watchdog.py setup_cron.sh \
    archive_old_data.py email_config.txt \
    root@129.212.186.232:/opt/gasbuddy/

ssh root@129.212.186.232 "cd /opt/gasbuddy && chmod +x *.py *.sh"
```

---

## 🧪 PHASE-BY-PHASE TESTING

### **TEST 1: Scraper Isolation (Phase 1)**

**Purpose:** Verify each run creates unique timestamped files

**Steps:**
```bash
# On Droplet 1
ssh root@134.199.198.81
cd /opt/gasbuddy
python3 production_scraper_droplet1.py &

# Wait a few minutes, then check
ls runs/
cat current_run_droplet1.txt
```

**Expected:**
- Unique RUN_ID in `current_run_droplet1.txt`
- Files: `progress_RUNID_droplet1.pkl`, `completed_RUNID_droplet1.txt`
- CSV: `data/gasbuddy_droplet1_RUNID.csv`

---

### **TEST 2: Auto-Transfer (Phase 2a)**

**Purpose:** Verify CSV automatically transfers from Droplet 1 → Droplet 2

**Steps:**
```bash
# On Droplet 1 - Start transfer watcher
ssh root@134.199.198.81
cd /opt/gasbuddy
nohup ./post_run_droplet1.sh > logs/post_run_droplet1.log 2>&1 &

# Wait for scraper to finish (or manually create completion marker)
# Check transfer log
tail -f logs/post_run_droplet1.log
```

**Then on Droplet 2:**
```bash
ssh root@129.212.186.232
ls /opt/gasbuddy/incoming/
```

**Expected:**
- `✅ Transfer complete!` in Droplet 1 log
- CSV appears in Droplet 2 `/opt/gasbuddy/incoming/`

---

### **TEST 3: Auto-Merge (Phase 2b)**

**Purpose:** Verify both CSVs merge automatically with deduplication

**Steps:**
```bash
# On Droplet 2 - Start merge watcher
ssh root@129.212.186.232
cd /opt/gasbuddy
nohup ./post_run_droplet2.sh > logs/post_run_droplet2.log 2>&1 &

# Wait for both scrapers to finish
# Check merge log
tail -f logs/post_run_droplet2.log
```

**Expected:**
- `✅ Merge complete!` in log
- Merged CSV in `/opt/gasbuddy/merged/gasbuddy_merged_RUNID.csv`
- Completion marker: `/opt/gasbuddy/merged/complete_RUNID.txt`

---

### **TEST 4: Review Email (Phase 2c)**

**Purpose:** Verify you receive email with merged CSV

**Steps:**
```bash
# On Droplet 2 - Start review email sender
ssh root@129.212.186.232
cd /opt/gasbuddy
nohup python3 send_review_email.py > logs/send_review_email.log 2>&1 &

# Check log
tail -f logs/send_review_email.log
```

**Expected:**
- `✅ Review email sent!` in log
- Email received in your inbox with subject: "🔍 GasBuddy Scrape YYYYMMDD - Awaiting Review"
- CSV attached to email

---

### **TEST 5: Approval Detection (Phase 3a)**

**Purpose:** Verify system detects your approval reply

**Steps:**
```bash
# On Droplet 2 - Start approval watcher
ssh root@129.212.186.232
cd /opt/gasbuddy
nohup python3 approval_watcher.py > logs/approval_watcher.log 2>&1 &

# Reply to review email with "APPROVED"
# Wait 5 minutes (check interval)

# Check log
tail -f logs/approval_watcher.log
```

**Expected:**
- `✅ APPROVED: RUNID` in log
- `📅 Scheduled for delivery at HH:MM` in log
- File created: `/opt/gasbuddy/pending_delivery/deliver_RUNID.txt`

---

### **TEST 6: Client Delivery (Phase 3b)**

**Purpose:** Verify CSV automatically sends to client after 20 minutes

**Steps:**
```bash
# On Droplet 2 - Start client delivery
ssh root@129.212.186.232
cd /opt/gasbuddy
nohup python3 client_delivery.py > logs/client_delivery.log 2>&1 &

# Wait 20 minutes after approval
# Check log
tail -f logs/client_delivery.log
```

**Expected:**
- `⏳ Waiting to deliver RUNID (X minutes remaining)`
- After 20 min: `✅ Delivered successfully!`
- Client receives email with subject: "GasBuddy Data - [DATE]"
- CSV attached

---

### **TEST 7: Audit Trail (Phase 3c)**

**Purpose:** Verify all actions logged

**Steps:**
```bash
ssh root@129.212.186.232
cat /opt/gasbuddy/audit.log
```

**Expected format:**
```
run_id|completed_at|approved_at|delivered_at|total_stations|csv_file|status
20251028_183045|2025-10-28T18:30:45|2025-10-28T19:00:00|2025-10-28T19:20:00|125847|/path/to/csv|delivered
```

---

### **TEST 8: Health Monitoring (Phase 4)**

**Purpose:** Verify health checks work and send alerts

**Steps:**
```bash
# Test health check manually
ssh root@134.199.198.81
cd /opt/gasbuddy
DROPLET_ID=1 python3 health_check.py

# Simulate a problem (kill scraper mid-run)
pkill -f production_scraper

# Run health check again (should detect issue)
DROPLET_ID=1 python3 health_check.py
```

**Expected:**
- First run: `✅ HEALTHY`
- Second run: `❌ UNHEALTHY` + email alert sent

---

### **TEST 9: Watchdog Auto-Restart (Phase 5a)**

**Purpose:** Verify watchdog restarts dead scrapers

**Steps:**
```bash
# Start a scraper
ssh root@134.199.198.81
cd /opt/gasbuddy
python3 production_scraper_droplet1.py &

# Wait a moment, then kill it
pkill -f production_scraper

# Run watchdog (should restart)
DROPLET_ID=1 python3 watchdog.py
```

**Expected:**
- `🚨 ALERT: Scraper process dead but run incomplete!`
- `✅ Scraper restarted successfully`
- Email notification sent

---

### **TEST 10: Cron Jobs (Phase 5b)**

**Purpose:** Verify scheduled tasks work

**Steps:**
```bash
# Install cron jobs
ssh root@134.199.198.81
cd /opt/gasbuddy
./setup_cron.sh 1  # For Droplet 1

# Verify cron schedule
crontab -l

# Check cron is running
systemctl status cron

# Monitor cron logs
tail -f logs/cron_*.log
```

**Expected:**
- Cron schedule displays correctly
- After 2 minutes: watchdog runs
- After 5 minutes: health check runs
- At 6am/6pm: scraper starts (with random delay)

---

### **TEST 11: Storage Management (Phase 5c)**

**Purpose:** Verify archiving works

**Steps:**
```bash
# Create some old test files (simulate age)
ssh root@134.199.198.81
cd /opt/gasbuddy/data
touch -d "100 days ago" old_test_file.csv

# Run archiving
cd /opt/gasbuddy
python3 archive_old_data.py
```

**Expected:**
- `📦 Archived: old_test_file.csv`
- File moved to `/opt/gasbuddy/archive/YYYY/MM/`

---

## 🎯 FULL END-TO-END TEST

**Complete flow from scrape to client delivery:**

1. ✅ Both scrapers run simultaneously
2. ✅ Droplet 1 finishes → auto-transfers CSV to Droplet 2
3. ✅ Droplet 2 finishes → auto-merges both CSVs
4. ✅ Review email sent to you with merged CSV
5. ✅ You reply with "APPROVED"
6. ✅ System detects approval, schedules delivery
7. ✅ After 20 minutes → CSV sent to client
8. ✅ All actions logged in audit.log
9. ✅ Health checks pass throughout
10. ✅ Monitor shows accurate progress

**Timeline:** ~7 hours total (5.5h scraping + 1h wait + 20min approval delay)

---

## 📊 MONITORING COMMANDS

**Real-time monitoring:**
```bash
# From your local machine
cd /Users/spensercourville-taylor/htmlfiles/gasBuddyScraper
./monitor_both_droplets.sh
```

**Check specific components:**
```bash
# Health status
ssh root@DROPLET_IP "cd /opt/gasbuddy && DROPLET_ID=N python3 health_check.py"

# Email systems
ssh root@129.212.186.232 "ps aux | grep -E 'send_review|approval|client_delivery'"

# Cron jobs
ssh root@DROPLET_IP "crontab -l"

# Disk usage
ssh root@DROPLET_IP "cd /opt/gasbuddy && python3 archive_old_data.py"
```

---

## ❌ TROUBLESHOOTING

### Scraper not starting
- Check PID lock: `rm /opt/gasbuddy/scraper_dropletN.pid`
- Check logs: `tail -100 /opt/gasbuddy/logs/scraper_run.log`

### Email not sending
- Verify config: `cat /opt/gasbuddy/email_config.txt`
- Test manually: `./test_email_flow.py`

### Transfer not working
- Check SSH keys: `ssh-copy-id root@DROPLET2_IP`
- Check transfer log: `tail -f logs/post_run_droplet1.log`

### Cron not running
- Check service: `systemctl status cron`
- Check logs: `grep CRON /var/log/syslog`

---

## ✅ DEPLOYMENT COMPLETE WHEN:

- [x] All 11 individual tests pass
- [x] Full end-to-end test completes successfully
- [x] Cron jobs installed on both droplets
- [x] Email configuration tested and working
- [x] Monitor shows both scrapers running
- [x] Audit log records complete workflow

**System is production-ready!** 🎉

