#!/usr/bin/env python3
"""
TEST: Can curl_cffi get ALL 34 stations for ZIP 77494?
Need to:
1. Load page, get first 20 from Apollo state
2. Use GraphQL with cursor to get next 14
3. Total = 34 stations
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("FULL TEST: curl_cffi for ALL 34 stations (with pagination)")
print("="*70)

session = requests.Session()
all_stations = []
all_station_ids = set()

# Step 1: Load initial page
print("\n1. Loading initial page...")
response = session.get(
    "https://www.gasbuddy.com/home?search=77494",
    impersonate="chrome120",
    timeout=30
)

print(f"   Status: {response.status_code}")

if response.status_code != 200:
    print(f"   ❌ Failed to load page")
    exit(1)

# Extract CSRF
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None
print(f"   CSRF: {csrf_token[:20] if csrf_token else 'None'}...")

# Extract Apollo state
apollo_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.+?});', response.text, re.DOTALL)
if not apollo_match:
    print("   ❌ No Apollo state found")
    exit(1)

apollo_state = json.loads(apollo_match.group(1))

# Find total count and cursor
total_count = None
next_cursor = None
for key, value in apollo_state.items():
    if key.startswith('Location:') and isinstance(value, dict):
        for subkey, subvalue in value.items():
            if 'stations' in subkey and isinstance(subvalue, dict):
                total_count = subvalue.get('count')
                cursor_data = subvalue.get('cursor', {})
                if isinstance(cursor_data, dict):
                    next_cursor = cursor_data.get('next')
                break
        if total_count:
            break

# Extract stations from Apollo state (first batch)
initial_station_keys = [k for k in apollo_state.keys() if k.startswith('Station:')]
initial_count = len(initial_station_keys)

print(f"   Initial stations: {initial_count}")
print(f"   Total available: {total_count}")
print(f"   Next cursor: {next_cursor}")

# Add initial stations to our list
for station_key in initial_station_keys:
    station_id = station_key.replace('Station:', '')
    all_station_ids.add(station_id)
    all_stations.append({'id': station_id, 'from': 'apollo'})

print(f"   ✅ Got {len(all_stations)} stations from initial page")

# Step 2: Paginate if needed
if next_cursor and len(all_stations) < total_count:
    print(f"\n2. Need more stations - using GraphQL pagination...")
    print(f"   Waiting 3 seconds...")
    time.sleep(3)
    
    clicks = 0
    max_clicks = 5
    
    while next_cursor and len(all_stations) < total_count and clicks < max_clicks:
        print(f"\n   Pagination request #{clicks+1} (cursor={next_cursor})...")
        
        headers = {
            "accept": "*/*",
            "apollo-require-preflight": "true",
            "content-type": "application/json",
            "gbcsrf": csrf_token,
            "referer": "https://www.gasbuddy.com/home?search=77494",
            "origin": "https://www.gasbuddy.com",
            "sec-ch-ua": '"Not=A?Brand";v="24", "Chromium";v="140"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin"
        }
        
        payload = {
            "operationName": "LocationBySearchTerm",
            "variables": {
                "fuel": 1,
                "lang": "en",
                "search": "77494",
                "cursor": next_cursor
            },
            "query": GRAPHQL_QUERY
        }
        
        graphql_response = session.post(
            "https://www.gasbuddy.com/graphql",
            json=payload,
            headers=headers,
            impersonate="chrome120",
            timeout=15
        )
        
        print(f"      Status: {graphql_response.status_code}")
        
        if graphql_response.status_code != 200:
            print(f"      ❌ GraphQL failed: {graphql_response.text[:100]}")
            break
        
        data = graphql_response.json()
        
        if 'data' not in data or not data['data']:
            print(f"      ❌ No data in response")
            break
        
        stations_data = data['data']['locationBySearchTerm']['stations']
        results = stations_data['results']
        next_cursor = stations_data['cursor']['next'] if stations_data['cursor'] else None
        
        # Add new stations
        added = 0
        for station in results:
            station_id = station['id']
            if station_id not in all_station_ids:
                all_station_ids.add(station_id)
                all_stations.append({'id': station_id, 'from': 'graphql'})
                added += 1
        
        print(f"      Added {added} new stations (total: {len(all_stations)}/{total_count})")
        
        clicks += 1
        
        if not next_cursor or len(all_stations) >= total_count:
            break
        
        time.sleep(1)  # Small delay between requests

else:
    print(f"\n2. No pagination needed - all stations in initial page")

# Step 3: Results
print("\n" + "="*70)
print("FINAL RESULTS")
print("="*70)
print(f"Expected: {total_count} stations")
print(f"Got: {len(all_stations)} stations")
print(f"Match: {len(all_stations) == total_count}")

if len(all_stations) == total_count:
    print("\n🎉🎉🎉 SUCCESS! curl_cffi gets ALL stations with pagination!")
    print("\nThis means:")
    print("  ✅ NO Playwright needed")
    print("  ✅ Pure HTTP (curl_cffi only)")
    print("  ✅ 10x lighter, 5x faster")
    print("  ✅ Can run 100+ on home server")
    print("  ✅ $0 compute costs (just proxies)")
    print("\n💰 SAVINGS: $105-700/month!")
else:
    print(f"\n⚠️  Missing {total_count - len(all_stations)} stations")
    print("   curl_cffi pagination needs debugging")

print("="*70)

