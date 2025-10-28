#!/usr/bin/env python3
"""
Test larger scale scraping (100+ ZIPs) with datacenter/ISP proxies
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

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

# Oxylabs ISP proxy configuration
PROXY_USERNAME = "gasBuddyScraper_5gUpP"
PROXY_PASSWORD = "gasBuddyScraper_123"
PROXY_HOST = "isp.oxylabs.io"
PROXY_PORTS = [8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010]

PROXY_URLS = [
    f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{port}"
    for port in PROXY_PORTS
]

thread_local = threading.local()

def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session

def scrape_zip(zip_code, csrf_token, worker_id, proxy_url):
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
                stations = data['data']['locationBySearchTerm']['stations']['results']
                
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
                return {'zip': zip_code, 'stations': 0, 'error': '429 Rate Limit', 'worker': worker_id, 'data': []}
            else:
                return {'zip': zip_code, 'stations': 0, 'error': f'{response.status_code}', 'worker': worker_id, 'data': []}
        except Exception as e:
            return {'zip': zip_code, 'stations': 0, 'error': str(e), 'worker': worker_id, 'data': []}
    
    return {
        'zip': zip_code, 
        'stations': len(all_stations), 
        'pages': page-1, 
        'worker': worker_id, 
        'error': None,
        'data': all_station_details
    }

print("="*70)
print("TESTING: LARGE SCALE SCRAPING WITH PROXIES")
print("="*70)

# Generate 300 diverse test ZIPs (mix of urban, suburban, and rural)
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
                results.append(result)
                
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
        
        for result in results:
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

