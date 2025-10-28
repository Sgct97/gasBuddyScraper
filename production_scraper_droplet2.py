#!/usr/bin/env python3
"""
PRODUCTION GasBuddy Scraper - DROPLET 2
- Scrapes ZIPs 20,744-41,487 (second half)
- 10 concurrent workers with proxy rotation (8011-8020)
- Session refresh every 25 minutes
- Resume capability with progress tracking
- Retry logic for failed ZIPs
- Canadian province filtering
- CSV export with timestamp
"""
from curl_cffi import requests
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import random
import sys
import csv
import pickle
from datetime import datetime, timedelta
import os
from write_csv_incremental import write_stations_to_csv

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

# ============================================================================
# PRODUCTION CONFIGURATION
# ============================================================================

# Oxylabs ISP proxy configuration
PROXY_USERNAME = "gasBuddyScraper_5gUpP"
PROXY_PASSWORD = "gasBuddyScraper_123"
PROXY_HOST = "isp.oxylabs.io"
PROXY_PORTS = [8011, 8012, 8013, 8014, 8015, 8016, 8017, 8018, 8019, 8020]

PROXY_URLS = [
    f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{port}"
    for port in PROXY_PORTS
]

# Production settings - DROPLET 2
NUM_WORKERS = 10
SESSION_REFRESH_MINUTES = 25  # Refresh before Cloudflare cookie expires (30min)
ZIP_FILE = 'droplet2_zips.txt'  # Second half of ZIPs
PROGRESS_FILE = 'scraper_progress_droplet2.pkl'
COMPLETED_FILE = 'completed_zips_droplet2.txt'
FAILED_FILE = 'failed_zips_droplet2.txt'
MAX_RETRIES = 3

# Thread-local storage for sessions
thread_local = threading.local()

# Global state (protected by lock)
state_lock = threading.Lock()
session_start_time = None
total_completed = 0
total_failed = 0
csv_filename = None  # Set at runtime

def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session

# ============================================================================
# RESUME & PROGRESS TRACKING
# ============================================================================

def load_zip_codes():
    """Load all ZIP codes and filter out already completed ones"""
    print(f"📂 Loading ZIP codes from {ZIP_FILE}...")
    with open(ZIP_FILE, 'r') as f:
        all_zips = [line.strip() for line in f if line.strip()]
    
    print(f"   Found {len(all_zips):,} total ZIP codes")
    
    # Load completed ZIPs
    completed_zips = set()
    if os.path.exists(COMPLETED_FILE):
        with open(COMPLETED_FILE, 'r') as f:
            completed_zips = set(line.strip() for line in f if line.strip())
        print(f"   Already completed: {len(completed_zips):,} ZIPs")
    
    # Filter out completed
    remaining_zips = [z for z in all_zips if z not in completed_zips]
    
    # Randomize order (anti-pattern, better distribution)
    random.shuffle(remaining_zips)
    
    print(f"   ✅ Remaining to scrape: {len(remaining_zips):,} ZIPs")
    print(f"   🔀 Order randomized for better distribution")
    
    return remaining_zips, len(completed_zips)

def save_progress(zip_code, success=True):
    """Save completed or failed ZIP to file"""
    try:
        with state_lock:
            if success:
                with open(COMPLETED_FILE, 'a') as f:
                    f.write(f"{zip_code}\n")
            else:
                with open(FAILED_FILE, 'a') as f:
                    f.write(f"{zip_code}\n")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not save progress for {zip_code}: {e}")

def needs_session_refresh():
    """Check if session needs refresh (25 minutes since start)"""
    global session_start_time
    if session_start_time is None:
        return True
    elapsed = datetime.now() - session_start_time
    return elapsed > timedelta(minutes=SESSION_REFRESH_MINUTES)

def get_csrf_token(proxy_url):
    """Get CSRF token by loading a sample page"""
    global session_start_time
    
    print(f"\n🔐 Getting new CSRF token via {proxy_url.split('@')[1]}...")
    session = get_session()
    
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    proxies = {"http": proxy_url, "https": proxy_url}
    
    try:
        # Add delay for Cloudflare
        time.sleep(3)
        
        response = session.get(
            "https://www.gasbuddy.com/home?search=10001",
            headers=headers,
            proxies=proxies,
            impersonate="chrome120",
            timeout=30
        )
        
        print(f"   Response status: {response.status_code}")
        
        if response.status_code == 200:
            # Try multiple patterns
            csrf_match = re.search(r'"csrfToken":"([^"]+)"', response.text)
            if not csrf_match:
                csrf_match = re.search(r'gbcsrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
            
            if csrf_match:
                csrf_token = csrf_match.group(1)
                session_start_time = datetime.now()
                print(f"   ✅ Session established at {session_start_time.strftime('%H:%M:%S')}")
                print(f"   CSRF: {csrf_token[:20]}...")
                return csrf_token
            else:
                print(f"   ⚠️  Got 200 but no CSRF token found")
                print(f"   Response length: {len(response.text)} bytes")
    except Exception as e:
        print(f"   ❌ Failed to get CSRF: {e}")
    
    return None

# ============================================================================
# SCRAPING LOGIC
# ============================================================================

def scrape_zip(zip_code, csrf_token, worker_id, proxy_url, retry_count=0):
    """Scrape a single ZIP code with anti-detection headers"""
    # Canadian provinces to exclude (GasBuddy mixes Canadian data in US ZIP searches)
    CANADIAN_PROVINCES = {'AB', 'BC', 'MB', 'NB', 'NL', 'NT', 'NS', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'}
    
    session = get_session()
    
    # Anti-detection: Full browser-like headers
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "apollo-require-preflight": "true",
        "content-type": "application/json",
        "gbcsrf": csrf_token,
        "referer": f"https://www.gasbuddy.com/home?search={zip_code}",
        "origin": "https://www.gasbuddy.com",
        "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    proxies = {"http": proxy_url, "https": proxy_url}
    all_stations = []
    all_station_details = []  # Store full data for samples
    cursor = "0"
    page = 1
    
    while page <= 10:
        payload = {
            "operationName": "LocationBySearchTerm",
            "variables": {
                "fuel": 1,
                "lang": "en",
                "search": zip_code,
                "cursor": cursor
            },
            "query": GRAPHQL_QUERY
        }
        
        try:
            response = session.post(
                "https://www.gasbuddy.com/graphql",
                json=payload,
                headers=headers,
                proxies=proxies,
                impersonate="chrome120",
                timeout=20
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle ZIPs with no stations (rural areas)
                if not data.get('data') or not data['data'].get('locationBySearchTerm'):
                    break  # No more data for this ZIP
                
                location_data = data['data']['locationBySearchTerm']
                if not location_data or not location_data.get('stations'):
                    break  # No stations for this ZIP
                
                stations = location_data['stations']['results']
                
                # Filter out Canadian stations (GasBuddy mixes them into US ZIP searches)
                us_only_stations = [
                    s for s in stations 
                    if s.get('address', {}).get('region', '') not in CANADIAN_PROVINCES
                ]
                
                if len(us_only_stations) == 0:
                    break
                
                all_stations.extend(us_only_stations)
                all_station_details.extend(us_only_stations)  # Keep full data
                cursor = str(len(all_stations))
                page += 1
                # Anti-detection: Randomized delay (1.5-3.5 seconds) - slower to avoid rate limits
                time.sleep(random.uniform(1.5, 3.5))
            elif response.status_code == 429:
                error_msg = '429 Rate Limit'
                if retry_count < MAX_RETRIES:
                    time.sleep(random.uniform(10, 20))  # Wait longer on rate limit
                    return scrape_zip(zip_code, csrf_token, worker_id, proxy_url, retry_count + 1)
                return {'zip': zip_code, 'stations': 0, 'error': error_msg, 'worker': worker_id, 'data': [], 'retries': retry_count}
            else:
                error_msg = f'{response.status_code}'
                if retry_count < MAX_RETRIES:
                    time.sleep(random.uniform(3, 7))
                    return scrape_zip(zip_code, csrf_token, worker_id, proxy_url, retry_count + 1)
                return {'zip': zip_code, 'stations': 0, 'error': error_msg, 'worker': worker_id, 'data': [], 'retries': retry_count}
        except Exception as e:
            error_msg = str(e)
            if retry_count < MAX_RETRIES:
                time.sleep(random.uniform(3, 7))
                return scrape_zip(zip_code, csrf_token, worker_id, proxy_url, retry_count + 1)
            return {'zip': zip_code, 'stations': 0, 'error': error_msg, 'worker': worker_id, 'data': [], 'retries': retry_count}
    
    return {
        'zip': zip_code, 
        'stations': len(all_stations), 
        'pages': page-1, 
        'worker': worker_id, 
        'error': None,
        'data': all_station_details,
        'retries': retry_count
    }

# ============================================================================
# CSV EXPORT
# ============================================================================

# export_to_csv function removed - using incremental writing instead

# ============================================================================
# MAIN PRODUCTION LOGIC
# ============================================================================

if __name__ == "__main__":
    start_time = datetime.now()
    
    # Initialize CSV filename for incremental writing
    csv_filename = f"data/gasbuddy_droplet2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    import os
    os.makedirs('data', exist_ok=True)
    
    print("="*70)
    print("🚀 PRODUCTION GASBUDDY SCRAPER - DROPLET 2")
    print("="*70)
    print(f"ZIP Range: 20,744-41,487 (second half)")
    print(f"Proxies: {PROXY_HOST}:8011-8020")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load ZIP codes (with resume capability)
    zip_codes_to_scrape, already_completed = load_zip_codes()
    
    if len(zip_codes_to_scrape) == 0:
        print("\n✅ All ZIP codes already completed!")
        exit(0)
    
    # Establish initial session and get CSRF token
    csrf_token = get_csrf_token(PROXY_URLS[0])
    if not csrf_token:
        print("\n❌ Failed to establish initial session. Exiting.")
        exit(1)
    
    # Run scraping with workers
    print(f"\n{'='*70}")
    print(f"SCRAPING: {NUM_WORKERS} concurrent workers")
    print(f"{'='*70}\n")
    
    results = []
    completed = already_completed
    failed = 0
    start_time_scraping = time.time()
    
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # Submit all ZIPs to workers with proper proxy rotation
        future_to_zip = {}
        for i, zip_code in enumerate(zip_codes_to_scrape):
            # Check if session needs refresh before submitting
            if needs_session_refresh():
                print(f"\n🔄 Session refresh needed (25 minutes elapsed)")
                csrf_token = get_csrf_token(PROXY_URLS[0])
                if not csrf_token:
                    print("   ⚠️  Session refresh failed, continuing with old token...")
            
            # Rotate proxies: each worker gets assigned a proxy
            proxy_url = PROXY_URLS[i % len(PROXY_URLS)]
            worker_id = i % NUM_WORKERS
            
            future = executor.submit(scrape_zip, zip_code, csrf_token, worker_id, proxy_url)
            future_to_zip[future] = zip_code
        
        # Process results as they complete
        for future in as_completed(future_to_zip):
            zip_code = future_to_zip[future]
            try:
                result = future.result()
                # Write station data to CSV immediately (no memory accumulation)
                stations_data = result.get('data', [])
                if stations_data:
                    with state_lock:
                        write_stations_to_csv(stations_data, csv_filename)
                
                # Store result without full data
                result_summary = {
                    'zip': result['zip'],
                    'stations': result['stations'],
                    'pages': result.get('pages', 1),
                    'worker': result['worker'],
                    'error': result.get('error'),
                    'retries': result.get('retries', 0)
                }
                results.append(result_summary)
                
                # Save progress
                if result.get('error'):
                    save_progress(zip_code, success=False)
                    failed += 1
                else:
                    save_progress(zip_code, success=True)
                    completed += 1
                
                # Periodic memory cleanup - flush to disk every 500 ZIPs
                    # This will be handled at the end, just noting progress
                
                # Live progress updates (every 50 ZIPs or first 20)
                if completed % 50 == 0 or completed <= 20:
                    elapsed = time.time() - start_time_scraping
                    rate = (completed - already_completed) / elapsed if elapsed > 0 else 0
                    stations_so_far = sum(r.get('stations', 0) for r in results)
                    pct = (completed / (41487)) * 100
                    eta_seconds = ((41487 - completed) / rate) if rate > 0 else 0
                    eta_hours = eta_seconds / 3600
                    
                    print(f"[{time.strftime('%H:%M:%S')}] {completed:,}/41,487 ({pct:.1f}%) | "
                          f"Rate: {rate:.2f} ZIP/s | Stations: {stations_so_far:,} | "
                          f"Failed: {failed} | ETA: {eta_hours:.1f}h")
                    sys.stdout.flush()
                    
            except Exception as e:
                print(f"   Exception processing {zip_code}: {e}")
                save_progress(zip_code, success=False)
                failed += 1
    
    total_time = time.time() - start_time_scraping
    total_stations = sum(r.get('stations', 0) for r in results)
    
    # Final summary
    print(f"\n{'='*70}")
    print("SCRAPING COMPLETE")
    print(f"{'='*70}")
    print(f"Total time: {total_time/3600:.2f} hours")
    print(f"Total ZIP codes processed: {len(results):,}")
    print(f"Total stations collected: {total_stations:,}")
    print(f"Successful: {completed - already_completed:,}")
    print(f"Failed: {failed}")
    print(f"Throughput: {len(results)/total_time:.2f} ZIPs/second")
    
    # CSV already written incrementally
    print(f"\n{'='*70}")
    print(f"CSV EXPORT COMPLETE")
    print(f"{'='*70}")
    print(f"✅ CSV file: {csv_filename}")
    
    # Count total lines in CSV
    try:
        with open(csv_filename, 'r') as f:
            total_stations_in_csv = sum(1 for line in f) - 1  # -1 for header
        print(f"✅ Total stations in CSV: {total_stations_in_csv:,}")
    except:
        pass
    
    print(f"\n{'='*70}")
    print("✅ PRODUCTION RUN COMPLETE")
    print(f"{'='*70}")
    print(f"CSV file: {csv_filename}")
    print(f"Completed ZIPs logged: {COMPLETED_FILE}")
    print(f"Failed ZIPs logged: {FAILED_FILE}")
    print(f"{'='*70}\n")

# Old test code below - keeping for reference but not executed
"""
test_zips = [
    # High volume urban (50-200 stations each)
    "77494", "19019", "02101", "85001", "33125", "90210", "60601", "10001",
    "94102", "75201", "77002", "30301", "20001", "98101", "80202", "53202",
    
    # Medium volume (20-50 stations)
    "33773", "37201", "64101", "46201", "28201", "29201", "23220", "43215",
    "55401", "68102", "40202", "70112", "73102", "87102", "89101", "92101",
    "91001", "78701", "32801", "33602", "48201", "21201", "15201", "44101",
    "63101", "97201", "84101", "95101", "76101", "37203", "85003", "90001",
    
    # Suburban/smaller cities
    "30002", "77301", "33710", "85203", "90650", "98012", "80014", "60018",
    "30144", "75052", "77084", "85032", "92802", "94404", "80234", "60074",
    "30324", "77382", "33777", "85282", "90720", "98133", "80204", "60169",
    
    # Rural/small town mix
    "59001", "82001", "83001", "87001", "88001", "99001", "49001", "35801",
    "72201", "65801", "83702", "97330", "99801", "57001", "82901", "59701",
]

# Pad to 300 ZIPs by cycling through the list
while len(test_zips) < 300:
    test_zips.append(test_zips[len(test_zips) % len(test_zips)])

test_zips = test_zips[:300]  # Exactly 300

print(f"\nTesting with {len(test_zips)} ZIPs...")

# Get session through proxy with anti-detection
print("\n1. Establishing session via proxy with anti-detection...")
main_session = requests.Session()
proxy_url = PROXY_URLS[0]

# Anti-detection: Add random delay before first request
time.sleep(random.uniform(1, 3))

response = main_session.get(
    "https://www.gasbuddy.com/",
    proxies={"http": proxy_url, "https": proxy_url},
    impersonate="chrome120",
    timeout=30
)

print(f"   Session established via {proxy_url.split('@')[1]}")

csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

print(f"   CSRF: {csrf_token[:20]}...")

# Test with 10 workers (optimal based on 10 proxies)
for num_workers in [10]:
    print(f"\n{'='*70}")
    print(f"TEST: {num_workers} concurrent workers")
    print(f"{'='*70}")
    
    start_time = time.time()
    results = []
    errors = []
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(
                scrape_zip,
                zip_code,
                csrf_token,
                i % num_workers,
                PROXY_URLS[i % len(PROXY_URLS)]  # Rotate proxies
            ): zip_code
            for i, zip_code in enumerate(test_zips)
        }
        
        completed = 0
        for future in as_completed(futures):
            try:
                result = future.result()
                # Write station data to CSV immediately (no memory accumulation)
                stations_data = result.get('data', [])
                if stations_data:
                    with state_lock:
                        write_stations_to_csv(stations_data, csv_filename)
                
                # Store result without full data
                result_summary = {
                    'zip': result['zip'],
                    'stations': result['stations'],
                    'pages': result.get('pages', 1),
                    'worker': result['worker'],
                    'error': result.get('error'),
                    'retries': result.get('retries', 0)
                }
                results.append(result_summary)
                
                if result['error']:
                    errors.append(result)
                
                completed += 1
                # Live progress updates (every 10 ZIPs or first 15)
                if completed % 10 == 0 or completed <= 15:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed
                    stations_so_far = sum(r['stations'] for r in results if not r.get('error'))
                    errors_so_far = sum(1 for r in results if r.get('error'))
                    pct = (completed / len(test_zips)) * 100
                    eta = (len(test_zips) - completed) / rate if rate > 0 else 0
                    print(f"   [{time.strftime('%H:%M:%S')}] {completed}/{len(test_zips)} ({pct:.0f}%) | "
                          f"Rate: {rate:.1f} ZIP/s | Stations: {stations_so_far:,} | "
                          f"Errors: {errors_so_far} | ETA: {eta/60:.0f}m")
                    sys.stdout.flush()
                    
            except Exception as e:
                print(f"   Exception: {e}")
    
    total_time = time.time() - start_time
    total_stations = sum(r['stations'] for r in results if not r.get('error'))
    success_count = sum(1 for r in results if not r.get('error'))
    rate_limit_count = sum(1 for r in errors if '429' in str(r.get('error', '')))
    
    print(f"\n{'='*70}")
    print(f"RESULTS: {num_workers} workers")
    print(f"{'='*70}")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"Total stations: {total_stations:,}")
    print(f"ZIPs completed: {success_count}/{len(test_zips)}")
    print(f"Rate limits (429): {rate_limit_count}")
    print(f"Other errors: {len(errors) - rate_limit_count}")
    print(f"Throughput: {len(test_zips)/total_time:.2f} ZIPs/second")
    print(f"Average per ZIP: {total_time/len(test_zips):.1f}s")
    
    if rate_limit_count > 0:
        print(f"\n⚠️  Hit {rate_limit_count} rate limits - may need more proxies or slower rate")
    else:
        print(f"\n✅ No rate limits with {num_workers} workers!")
    
    # Estimate for full 42K scale
    estimated_time_42k = (42000 / len(test_zips)) * total_time
    print(f"\n📊 Extrapolated to 42,000 ZIPs (all US ZIPs):")
    print(f"   Estimated time: {estimated_time_42k/3600:.1f} hours per scrape")
    print(f"   Daily (2x): {estimated_time_42k/3600*2:.1f} hours")
    print(f"   With {len(PROXY_URLS)} proxies rotating")
    print(f"   Bandwidth per scrape: {(total_stations * 40 / 1024 / 1024) * (42000/len(test_zips)):.1f} GB")
    print(f"   Bandwidth per month (60x): {(total_stations * 40 / 1024 / 1024) * (42000/len(test_zips)) * 60:.1f} GB")
    print(f"   💰 Cost @ $16/month unlimited: $16/month flat rate!")
    
    # Pagination analysis
    print(f"\n📄 PAGINATION ANALYSIS:")
    multi_page = [r for r in results if r.get('pages', 0) > 1]
    if multi_page:
        print(f"   ZIPs requiring pagination: {len(multi_page)}/{len(results)}")
        print(f"   Max pages for single ZIP: {max(r.get('pages', 0) for r in results)}")
        print(f"\n   Top 5 ZIPs by page count:")
        sorted_by_pages = sorted(results, key=lambda x: x.get('pages', 0), reverse=True)[:5]
        for r in sorted_by_pages:
            if r.get('pages', 0) > 1:
                print(f"      ZIP {r['zip']}: {r['stations']} stations across {r['pages']} pages")
    else:
        print(f"   All ZIPs fit in single page (20 or fewer stations)")
    
    # Sample data analysis
    print(f"\n📦 SAMPLE DATA (showing 5 random stations with prices):")
    stations_with_data = [r for r in results if r.get('data') and len(r['data']) > 0]
    if stations_with_data:
        for i, result in enumerate(random.sample(stations_with_data, min(5, len(stations_with_data))), 1):
            # Pick a random station from this ZIP
            station = random.choice(result['data'])
            print(f"\n   Sample {i} - ZIP {result['zip']}:")
            print(f"      Name: {station['name']}")
            print(f"      Address: {station['address']['line1']}, {station['address']['locality']}, {station['address']['region']}")
            print(f"      ID: {station['id']}")
            
            if 'prices' in station and station['prices']:
                has_price = False
                for price_report in station['prices']:
                    if price_report['fuelProduct'] == 'regular_gas':
                        cash_info = price_report.get('cash', {})
                        credit_info = price_report.get('credit', {})
                        
                        if cash_info and cash_info.get('price') and cash_info.get('price') > 0:
                            print(f"      Regular (cash): ${cash_info['price']} by {cash_info.get('nickname', 'N/A')}")
                            has_price = True
                        elif credit_info and credit_info.get('price') and credit_info.get('price') > 0:
                            print(f"      Regular (credit): ${credit_info['price']} by {credit_info.get('nickname', 'N/A')}")
                            has_price = True
                        break
                
                if not has_price:
                    print(f"      Regular gas: No recent price reports")
            else:
                print(f"      Prices: No data available")
    
    # Export to CSV
    print(f"\n💾 EXPORTING TO CSV...")
    csv_filename = f"gasbuddy_data_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'station_id', 'station_name', 'brand', 
            'address_line1', 'city', 'state', 'zip',
            'latitude', 'longitude',
            'regular_cash_price', 'regular_cash_posted_time', 'regular_cash_reporter',
            'regular_credit_price', 'regular_credit_posted_time', 'regular_credit_reporter',
            'midgrade_cash_price', 'midgrade_credit_price',
            'premium_cash_price', 'premium_credit_price',
            'diesel_cash_price', 'diesel_credit_price',
            'has_convenience_store', 'has_car_wash', 'has_restrooms',
            'accepts_credit_cards', 'rating'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        total_exported = 0
        
        # Create a pseudo-results structure from accumulated station data
    pseudo_results = [{'data': []  # removed}]
    
    for result in pseudo_results:
            if not result.get('data'):
                continue
                
            for station in result['data']:
                # Extract address (Canadian stations already filtered in scrape_zip)
                address = station.get('address', {})
                
                # Extract prices by fuel type
                prices_by_type = {}
                if 'prices' in station and station['prices']:
                    for price_report in station['prices']:
                        fuel_type = price_report.get('fuelProduct', '')
                        cash_info = price_report.get('cash', {})
                        credit_info = price_report.get('credit', {})
                        
                        prices_by_type[fuel_type] = {
                            'cash_price': cash_info.get('price') if cash_info else None,
                            'cash_time': cash_info.get('postedTime') if cash_info else None,
                            'cash_reporter': cash_info.get('nickname') if cash_info else None,
                            'credit_price': credit_info.get('price') if credit_info else None,
                            'credit_time': credit_info.get('postedTime') if credit_info else None,
                            'credit_reporter': credit_info.get('nickname') if credit_info else None,
                        }
                
                # Extract amenities
                amenities = station.get('amenities', {})
                
                # Build CSV row
                row = {
                    'station_id': station.get('id', ''),
                    'station_name': station.get('name', ''),
                    'brand': station.get('brand', {}).get('name', '') if station.get('brand') else '',
                    'address_line1': address.get('line1', ''),
                    'city': address.get('locality', ''),
                    'state': address.get('region', ''),
                    'zip': address.get('postalCode', ''),
                    'latitude': address.get('latitude', ''),
                    'longitude': address.get('longitude', ''),
                    'regular_cash_price': prices_by_type.get('regular_gas', {}).get('cash_price', ''),
                    'regular_cash_posted_time': prices_by_type.get('regular_gas', {}).get('cash_time', ''),
                    'regular_cash_reporter': prices_by_type.get('regular_gas', {}).get('cash_reporter', ''),
                    'regular_credit_price': prices_by_type.get('regular_gas', {}).get('credit_price', ''),
                    'regular_credit_posted_time': prices_by_type.get('regular_gas', {}).get('credit_time', ''),
                    'regular_credit_reporter': prices_by_type.get('regular_gas', {}).get('credit_reporter', ''),
                    'midgrade_cash_price': prices_by_type.get('midgrade', {}).get('cash_price', ''),
                    'midgrade_credit_price': prices_by_type.get('midgrade', {}).get('credit_price', ''),
                    'premium_cash_price': prices_by_type.get('premium', {}).get('cash_price', ''),
                    'premium_credit_price': prices_by_type.get('premium', {}).get('credit_price', ''),
                    'diesel_cash_price': prices_by_type.get('diesel', {}).get('cash_price', ''),
                    'diesel_credit_price': prices_by_type.get('diesel', {}).get('credit_price', ''),
                    'has_convenience_store': amenities.get('hasConvenienceStore', ''),
                    'has_car_wash': amenities.get('hasCarWash', ''),
                    'has_restrooms': amenities.get('hasRestrooms', ''),
                    'accepts_credit_cards': amenities.get('acceptsCreditCards', ''),
                    'rating': station.get('starRating', ''),
                }
                
                writer.writerow(row)
                total_exported += 1
    
    print(f"   ✅ Exported {total_exported:,} stations to {csv_filename}")

print("\n" + "="*70)
print("CONCLUSIONS")
print("="*70)
print("\n✅ Key findings will show:")
print("  1. Optimal worker count for 30K ZIPs")
print("  2. Whether 10 proxies are sufficient")
print("  3. Expected completion time")
print("  4. Rate limiting behavior at scale")
print("="*70)

"""
