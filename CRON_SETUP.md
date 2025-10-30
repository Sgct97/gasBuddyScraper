# GasBuddy Scraper - Cron Job Configuration

## Production Cron Jobs

### Droplet 1 (134.199.198.81)

```bash
# Watchdog - runs every 2 minutes to monitor scrapers
*/2 * * * * cd /opt/gasbuddy && DROPLET_ID=1 python3 watchdog.py >> logs/watchdog_droplet1.log 2>&1

# ========== SCRAPER SCHEDULING ==========
# Runs twice daily at 5 AM and 5 PM EST (10:00 and 22:00 UTC)
0 10,22 * * * cd /opt/gasbuddy && nohup python3 production_scraper_droplet1.py > /dev/null 2>&1 &

# ========== AUTO-START WATCHERS ON REBOOT ==========
@reboot cd /opt/gasbuddy && nohup bash post_run_droplet1.sh > logs/auto_transfer.log 2>&1 &
```

### Droplet 2 (129.212.186.232)

```bash
# Watchdog - runs every 2 minutes to monitor scrapers
*/2 * * * * cd /opt/gasbuddy && DROPLET_ID=2 python3 watchdog.py >> logs/watchdog_droplet2.log 2>&1

# ========== SCRAPER SCHEDULING ==========
# Runs twice daily at 5 AM and 5 PM EST (10:00 and 22:00 UTC) with 10-second stagger
0 10,22 * * * sleep 10 && cd /opt/gasbuddy && nohup python3 production_scraper_droplet2.py > /dev/null 2>&1 &

# ========== AUTO-START WATCHERS ON REBOOT ==========
@reboot cd /opt/gasbuddy && nohup bash post_run_droplet2.sh > logs/auto_merge.log 2>&1 &
@reboot cd /opt/gasbuddy && nohup python3 approval_watcher.py > logs/auto_approval.log 2>&1 &
```

## Installation Instructions

To install these cron jobs on a new droplet:

### Droplet 1:
```bash
ssh root@134.199.198.81
crontab -e
# Paste the Droplet 1 configuration above
```

### Droplet 2:
```bash
ssh root@129.212.186.232
crontab -e
# Paste the Droplet 2 configuration above
```

## Schedule Summary

- **Scraper Runs:** Twice daily at 5:00 AM and 5:00 PM EST (10:00 & 22:00 UTC)
- **Droplet 2 Stagger:** Starts 10 seconds after Droplet 1 to prevent proxy conflicts
- **Watchdog Monitoring:** Every 2 minutes on both droplets
- **Auto-Restart:** All watchers restart automatically if droplets reboot

## Automation Flow

1. **Cron triggers scrapers** at scheduled times
2. **Scrapers run independently** with separate proxy pools
3. **Post-run watchers detect completion**
4. **CSV transfers** from D1 to D2
5. **Merge & deduplication** runs on D2
6. **Review email sent** to admin
7. **Approval watcher monitors** for "OK" reply
8. **Client receives final CSV** 20 minutes after approval
9. **Files archived** and working directories cleaned
10. **System ready** for next run

## Monitoring Commands

Monitor both droplets in real-time:
```bash
cd /Users/spensercourville-taylor/htmlfiles/gasBuddyScraper && bash monitor_both_droplets.sh
```

Check cron jobs:
```bash
ssh root@134.199.198.81 'crontab -l'
ssh root@129.212.186.232 'crontab -l'
```

Check running processes:
```bash
ssh root@134.199.198.81 'ps aux | grep -E "(scraper|watchdog|post_run|approval)" | grep -v grep'
ssh root@129.212.186.232 'ps aux | grep -E "(scraper|watchdog|post_run|approval)" | grep -v grep'
```

## Notes

- **Timezone:** All times in cron are UTC. EST = UTC - 5 hours.
- **Logs:** All automation logs stored in `/opt/gasbuddy/logs/`
- **Archives:** Completed runs stored in `/opt/gasbuddy/archive/YYYY/MM/`
- **Email:** Powered by SendGrid API (info@aiearlybird.com)

