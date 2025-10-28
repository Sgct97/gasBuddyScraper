#!/usr/bin/env python3
"""
Test scraping with Oxylabs ISP proxies
"""
from curl_cffi import requests
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import random

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

# Oxylabs ISP proxy configuration
PROXY_USERNAME = "gasBuddyScraper_5gUpP"
PROXY_PASSWORD = "gasBuddyScraper_123"
PROXY_HOST = "isp.oxylabs.io"
PROXY_PORTS = [8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010]

# Create proxy URLs
PROXY_URLS = [
    f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{port}"
    for port in PROXY_PORTS
]

# Thread-local storage
thread_local = threading.local()

def get_session(use_proxy=False, proxy_url=None):
    """Get a session for the current thread"""
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session

def scrape_zip_with_proxy(zip_code, csrf_token, worker_id, proxy_url=None):
    """Scrape a single ZIP code, optionally with proxy"""
    session = get_session()
    start_time = time.time()
    
    proxy_info = f"Proxy {proxy_url.split('@')[1] if proxy_url else 'None'}"
    print(f"[Worker {worker_id}] Starting ZIP {zip_code} via {proxy_info}...")
    
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
    
    # Set up proxies for curl_cffi
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    
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
                stations = data['data']['locationBySearchTerm']['stations']['results']
                
                if len(stations) == 0:
                    break
                
                all_stations.extend(stations)
                cursor = str(len(all_stations))
                page += 1
                time.sleep(1)
            else:
                print(f"[Worker {worker_id}] ZIP {zip_code} failed: {response.status_code}")
                break
        except Exception as e:
            print(f"[Worker {worker_id}] ZIP {zip_code} error: {e}")
            break
    
    elapsed = time.time() - start_time
    result_symbol = "✅" if len(all_stations) > 0 else "❌"
    print(f"[Worker {worker_id}] {result_symbol} ZIP {zip_code}: {len(all_stations)} stations in {elapsed:.1f}s")
    
    return {
        'zip': zip_code,
        'stations': len(all_stations),
        'pages': page - 1,
        'time': elapsed,
        'worker': worker_id,
        'proxy': proxy_info,
        'success': len(all_stations) > 0
    }

print("="*70)
print("TESTING: SCRAPING WITH OXYLABS ISP PROXIES")
print("="*70)

# Test ZIPs
test_zips = [
    "77494",  # 34 stations
    "33773",  # 7 stations
    "90210",  # Few stations
    "19019",  # 139 stations
    "02101",  # Boston
    "85001",  # Phoenix
    "10001",  # NYC
    "60601",  # Chicago
]

# TEST 1: Without proxies (baseline)
print("\n" + "="*70)
print("TEST 1: WITHOUT PROXIES (baseline)")
print("="*70)

main_session = requests.Session()
response = main_session.get(
    "https://www.gasbuddy.com/",
    impersonate="chrome120",
    timeout=30
)

csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

print(f"\nGot CSRF: {csrf_token[:20]}...")

start_time = time.time()
no_proxy_results = []

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(scrape_zip_with_proxy, zip_code, csrf_token, i % 3, None): zip_code 
        for i, zip_code in enumerate(test_zips)
    }
    
    for future in as_completed(futures):
        try:
            result = no_proxy_results.append(future.result())
        except Exception as e:
            print(f"   ❌ Exception: {e}")

no_proxy_time = time.time() - start_time
no_proxy_stations = sum(r['stations'] for r in no_proxy_results if r)
no_proxy_success = sum(1 for r in no_proxy_results if r and r['success'])

print(f"\nResults WITHOUT proxies:")
print(f"  Time: {no_proxy_time:.1f}s")
print(f"  Stations: {no_proxy_stations}")
print(f"  Successful: {no_proxy_success}/{len(test_zips)}")

# TEST 2: With rotating proxies
print("\n" + "="*70)
print("TEST 2: WITH OXYLABS ISP PROXIES (rotating)")
print("="*70)

# Get new session/CSRF through proxy
time.sleep(5)  # Cool down

proxy_for_session = PROXY_URLS[0]
proxy_session = requests.Session()

print(f"\nGetting session via proxy {proxy_for_session.split('@')[1]}...")

response = proxy_session.get(
    "https://www.gasbuddy.com/",
    proxies={"http": proxy_for_session, "https": proxy_for_session},
    impersonate="chrome120",
    timeout=30
)

csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token_proxy = csrf_matches[0] if csrf_matches else None

print(f"Got CSRF: {csrf_token_proxy[:20]}...")

start_time = time.time()
proxy_results = []

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(
            scrape_zip_with_proxy, 
            zip_code, 
            csrf_token_proxy, 
            i % 3, 
            PROXY_URLS[i % len(PROXY_URLS)]  # Rotate through proxies
        ): zip_code 
        for i, zip_code in enumerate(test_zips)
    }
    
    for future in as_completed(futures):
        try:
            result = proxy_results.append(future.result())
        except Exception as e:
            print(f"   ❌ Exception: {e}")

proxy_time = time.time() - start_time
proxy_stations = sum(r['stations'] for r in proxy_results if r)
proxy_success = sum(1 for r in proxy_results if r and r['success'])

print(f"\nResults WITH proxies:")
print(f"  Time: {proxy_time:.1f}s")
print(f"  Stations: {proxy_stations}")
print(f"  Successful: {proxy_success}/{len(test_zips)}")

# Comparison
print("\n" + "="*70)
print("COMPARISON")
print("="*70)
print(f"\nWithout proxies: {no_proxy_success}/{len(test_zips)} successful, {no_proxy_stations} stations, {no_proxy_time:.1f}s")
print(f"With proxies:    {proxy_success}/{len(test_zips)} successful, {proxy_stations} stations, {proxy_time:.1f}s")

if proxy_success > no_proxy_success:
    print("\n✅ Proxies helped avoid rate limits!")
elif proxy_success == no_proxy_success:
    print("\n➖ Proxies didn't hurt or help (both worked)")
else:
    print("\n⚠️  Proxies performed worse")

print("="*70)

