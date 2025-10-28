# Dual Droplet Architecture Plan

## Overview
Upgrade from 1 droplet to 2 droplets to reduce scrape time from 10 hours to 5 hours.

## Critical Requirements (DO NOT BREAK)
- ✅ CSRF token management & 30-min refresh
- ✅ Session warmup (HTML load once, then GraphQL)
- ✅ Canadian province filtering
- ✅ Incremental CSV writing (prevent OOM)
- ✅ Progress tracking (completed_zips.txt, failed_zips.txt)
- ✅ Retry logic for 429 errors (3 retries with backoff)
- ✅ Anti-detection headers (comprehensive set)
- ✅ Randomized delays (1.5-3.5 seconds)
- ✅ Proxy rotation (10 proxies per droplet)
- ✅ NULL checking for rural ZIPs with no stations

## Architecture

### Droplet 1 (Primary)
- **Name:** Gas-Buddy-Scraper-1
- **IP:** 134.199.198.81 (existing)
- **ZIPs:** 1-20,943 (first half of all_us_zips.txt)
- **Proxies:** isp.oxylabs.io:8001-8010
- **Workers:** 10
- **Output:** gasbuddy_droplet1_[timestamp].csv
- **Schedule:** 12:00 AM and 12:00 PM (daily)

### Droplet 2 (Secondary)
- **Name:** Gas-Buddy-Scraper-2
- **IP:** [NEW - to be provided]
- **ZIPs:** 20,944-41,887 (second half of all_us_zips.txt)
- **Proxies:** isp.oxylabs.io:8011-8020 (NEW - to be provided)
- **Workers:** 10
- **Output:** gasbuddy_droplet2_[timestamp].csv
- **Schedule:** 12:00 AM and 12:00 PM (daily)

### CSV Merging
- **Location:** Local machine or either droplet
- **Process:** Download both CSVs → Merge → Dedupe → Sort
- **Final Output:** gasbuddy_full_[timestamp].csv

## Files to Create/Modify

### New Files:
1. `config_droplet1.py` - Configuration for droplet 1
2. `config_droplet2.py` - Configuration for droplet 2
3. `production_scraper_v2.py` - Updated scraper that reads from config
4. `split_zips.py` - Script to split all_us_zips.txt into two files
5. `merge_csvs.py` - Script to merge, dedupe, and validate both CSVs
6. `deploy_droplet1.sh` - Deployment script for droplet 1
7. `deploy_droplet2.sh` - Deployment script for droplet 2
8. `monitor_both.py` - Monitor both droplets simultaneously

### Modified Files:
- `production_scraper.py` → Keep as backup, don't modify
- `cron_wrapper.sh` → Update to use new config system
- `monitor.py` → Keep as-is (per-droplet monitoring)

### Unchanged Files (Copy to both droplets):
- `write_csv_incremental.py` - CSV writer
- `requirements.txt` - Dependencies
- `all_us_zips.txt` - Will be split into droplet1_zips.txt and droplet2_zips.txt

## Implementation Steps

### Phase 1: Preparation (Local)
1. ✅ Create config files for both droplets
2. ✅ Create production_scraper_v2.py (config-based)
3. ✅ Create split_zips.py and generate zip lists
4. ✅ Create merge_csvs.py
5. ✅ Test locally that config system works
6. ✅ Commit to GitHub

### Phase 2: Droplet 1 Upgrade
1. ✅ Backup existing production_scraper.py
2. ✅ Deploy new files to droplet 1
3. ✅ Update cron with new config
4. ✅ Test run with 10 ZIPs
5. ✅ Verify CSV output

### Phase 3: Droplet 2 Setup (After user provides IP and proxies)
1. ✅ Deploy all files to droplet 2
2. ✅ Configure with droplet 2 settings
3. ✅ Setup cron jobs
4. ✅ Test run with 10 ZIPs
5. ✅ Verify CSV output

### Phase 4: Production Run
1. ✅ Start both droplets simultaneously
2. ✅ Monitor progress on both
3. ✅ Download both CSVs
4. ✅ Merge and validate
5. ✅ Deliver to client

## Rollback Plan
If anything goes wrong:
- Droplet 1 has backup of working production_scraper.py
- Can instantly revert to single-droplet mode
- No data loss (progress files preserved)

## Testing Checklist
- [ ] Config loading works correctly
- [ ] ZIP splitting is clean (no overlap, no gaps)
- [ ] Both droplets can run independently
- [ ] CSV merge handles duplicates
- [ ] Progress tracking works per-droplet
- [ ] Cron jobs scheduled correctly
- [ ] Monitoring shows both droplets
- [ ] Rollback procedure tested

## Risk Mitigation
- Keep original production_scraper.py untouched
- Test with 10-ZIP runs first
- Stagger schedules by 1 hour if rate limits appear
- Monitor first 24 hours closely

## Timeline
- Phase 1 (Prep): 30 minutes - CAREFUL AND THOROUGH
- Phase 2 (Droplet 1): 15 minutes
- Phase 3 (Droplet 2): 15 minutes (waiting on user)
- Phase 4 (Production): Ongoing

