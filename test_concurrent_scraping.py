#!/usr/bin/env python3
"""
Test CONCURRENT scraping: Query multiple ZIPs simultaneously with one session
"""
from curl_cffi import requests
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

# Thread-local storage for session (curl_cffi sessions aren't thread-safe)
thread_local = threading.local()

def get_session():
    """Get a session for the current thread"""
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session

def scrape_zip(zip_code, csrf_token, worker_id):
    """Scrape a single ZIP code with pagination"""
    session = get_session()
    start_time = time.time()
    
    print(f"[Worker {worker_id}] Starting ZIP {zip_code}...")
    
    all_stations = []
    cursor = "0"
    page = 1
    
    headers = {
        "accept": "*/*",
        "apollo-require-preflight": "true",
        "content-type": "application/json",
        "gbcsrf": csrf_token,
        "referer": f"https://www.gasbuddy.com/home?search={zip_code}",
        "origin": "https://www.gasbuddy.com",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin"
    }
    
    while page <= 10:  # Safety limit
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
                impersonate="chrome120",
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                stations = data['data']['locationBySearchTerm']['stations']['results']
                
                if len(stations) == 0:
                    break
                
                all_stations.extend(stations)
                cursor = str(len(all_stations))
                page += 1
                
                # Small delay between pages
                time.sleep(1)
            else:
                print(f"[Worker {worker_id}] ZIP {zip_code} failed: {response.status_code}")
                break
        except Exception as e:
            print(f"[Worker {worker_id}] ZIP {zip_code} error: {e}")
            break
    
    elapsed = time.time() - start_time
    print(f"[Worker {worker_id}] ✅ ZIP {zip_code}: {len(all_stations)} stations in {elapsed:.1f}s")
    
    return {
        'zip': zip_code,
        'stations': len(all_stations),
        'pages': page - 1,
        'time': elapsed,
        'worker': worker_id
    }

print("="*70)
print("TESTING: CONCURRENT SCRAPING")
print("="*70)

# Step 1: Get session/CSRF token
print("\n1. Getting session/CSRF token...")
main_session = requests.Session()

response = main_session.get(
    "https://www.gasbuddy.com/",
    impersonate="chrome120",
    timeout=30
)

csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

print(f"   CSRF: {csrf_token[:20]}...")

# Test ZIPs with varying sizes
test_zips = [
    "77494",  # 34 stations (2 pages)
    "33773",  # 7 stations (1 page)
    "90210",  # Few stations
    "19019",  # 139 stations (7 pages)
    "02101",  # Boston area
    "85001",  # Phoenix area
    "10001",  # NYC area (few)
    "60601",  # Chicago area (few)
]

print(f"\n2. Testing {len(test_zips)} ZIPs with different worker counts...")

# Test with different numbers of workers
for num_workers in [1, 3, 5]:
    print(f"\n" + "="*70)
    print(f"TEST: {num_workers} concurrent workers")
    print("="*70)
    
    start_time = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(scrape_zip, zip_code, csrf_token, i % num_workers): zip_code 
            for i, zip_code in enumerate(test_zips)
        }
        
        # Collect results as they complete
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                zip_code = futures[future]
                print(f"   ❌ {zip_code} raised exception: {e}")
    
    total_time = time.time() - start_time
    total_stations = sum(r['stations'] for r in results)
    
    print(f"\n{'='*70}")
    print(f"RESULTS: {num_workers} workers")
    print(f"{'='*70}")
    print(f"Total time: {total_time:.1f}s")
    print(f"Total stations: {total_stations}")
    print(f"ZIPs completed: {len(results)}/{len(test_zips)}")
    print(f"Average per ZIP: {total_time/len(results):.1f}s")
    
    if num_workers == 1:
        sequential_time = total_time
    else:
        speedup = sequential_time / total_time
        print(f"Speedup vs sequential: {speedup:.1f}x")

print("\n" + "="*70)
print("CONCLUSIONS")
print("="*70)
print("\n✅ Key findings:")
print("  1. Can we use one session for concurrent requests?")
print("  2. Does rate limiting kick in with parallel requests?")
print("  3. What's the optimal number of workers?")
print("  4. What speedup do we achieve?")
print("="*70)

