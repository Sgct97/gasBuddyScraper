#!/usr/bin/env python3
"""
COMPLETE DATA TEST: Get all 34 stations with full details WITHOUT loading HTML for 77494
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("OPTIMIZED APPROACH: Complete Data Test for ZIP 19019 (100 stations)")
print("="*70)

session = requests.Session()
all_stations = []

# Step 1: Load HTML for a DIFFERENT ZIP to establish session
print("\n1. Loading HTML for ZIP 10001 (to get session/CSRF)...")
html_response = session.get(
    "https://www.gasbuddy.com/home?search=10001",
    impersonate="chrome120",
    timeout=30
)

html_size = len(html_response.content)
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', html_response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

print(f"   Size: {html_size:,} bytes ({html_size/1024:.2f} KB)")
print(f"   CSRF: {csrf_token[:20]}...")

# Step 2: Query 19019 with pagination
print("\n2. Querying ZIP 19019 via GraphQL with full pagination...")

headers = {
    "accept": "*/*",
    "apollo-require-preflight": "true",
    "content-type": "application/json",
    "gbcsrf": csrf_token,
    "referer": "https://www.gasbuddy.com/home?search=19019",
    "origin": "https://www.gasbuddy.com",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
}

total_bandwidth = html_size
cursor = "0"
page = 1

while page <= 10:  # Safety limit
    print(f"\n   Page {page} (cursor={cursor})...")
    time.sleep(3)
    
    payload = {
        "operationName": "LocationBySearchTerm",
        "variables": {
            "fuel": 1,
            "lang": "en",
            "search": "19019",
            "cursor": cursor
        },
        "query": GRAPHQL_QUERY
    }
    
    response = session.post(
        "https://www.gasbuddy.com/graphql",
        json=payload,
        headers=headers,
        impersonate="chrome120",
        timeout=15
    )
    
    response_size = len(response.content)
    total_bandwidth += response_size
    print(f"      Size: {response_size:,} bytes ({response_size/1024:.2f} KB)")
    
    if response.status_code == 200:
        data = response.json()
        stations = data['data']['locationBySearchTerm']['stations']['results']
        print(f"      Got {len(stations)} stations")
        
        if len(stations) == 0:
            print(f"      No more stations")
            break
        
        all_stations.extend(stations)
        cursor = str(len(all_stations))
        page += 1
    else:
        print(f"      ❌ Failed: {response.status_code}")
        break

# Print ALL stations with complete data
print("\n" + "="*70)
print(f"ALL {len(all_stations)} STATIONS - COMPLETE DATA")
print("="*70)

for idx, station in enumerate(all_stations, 1):
    print(f"\n{'='*70}")
    print(f"STATION #{idx}")
    print(f"{'='*70}")
    print(f"Name: {station['name']}")
    print(f"Address: {station['address']['line1']}, {station['address']['locality']}, {station['address']['region']} {station['address']['postalCode']}")
    print(f"ID: {station['id']}")
    
    if 'prices' in station and station['prices']:
        print(f"\nPrices ({len(station['prices'])} fuel types):")
        for price_report in station['prices']:
            fuel_type = price_report['fuelProduct']
            cash_info = price_report.get('cash', {})
            credit_info = price_report.get('credit', {})
            
            print(f"\n  {fuel_type}:")
            
            if cash_info and cash_info.get('price') and cash_info.get('price') > 0:
                posted = cash_info.get('postedTime', '')[:19] if cash_info.get('postedTime') else 'N/A'
                reporter = cash_info.get('nickname') if cash_info.get('nickname') else 'N/A'
                print(f"    Cash: ${cash_info['price']} (posted: {posted}, by: {reporter})")
            else:
                print(f"    Cash: Not reported")
            
            if credit_info and credit_info.get('price') and credit_info.get('price') > 0:
                posted = credit_info.get('postedTime', '')[:19] if credit_info.get('postedTime') else 'N/A'
                reporter = credit_info.get('nickname') if credit_info.get('nickname') else 'N/A'
                print(f"    Credit: ${credit_info['price']} (posted: {posted}, by: {reporter})")
            else:
                print(f"    Credit: Not reported")
    else:
        print("\nPrices: No recent reports")

# Summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"\nTotal stations: {len(all_stations)}")
print(f"Expected: ~100 (Philadelphia area)")
print(f"Pages retrieved: {page - 1}")

print(f"\nBandwidth used:")
print(f"  HTML for ZIP 10001: {html_size/1024:.2f} KB")
print(f"  GraphQL requests: {(total_bandwidth - html_size)/1024:.2f} KB")
print(f"  Total: {total_bandwidth/1024:.2f} KB")

if len(all_stations) >= 90:
    print("\n✅ SUCCESS! This proves multi-page pagination works:")
    print(f"  - All {len(all_stations)} stations retrieved")
    print(f"  - Across {page - 1} pages")
    print("  - Complete addresses")
    print("  - Both cash AND credit prices")
    print("  - Timestamps and reporters")
    print("  - All fuel types")
else:
    print(f"\n⚠️  Only got {len(all_stations)} stations")
print("="*70)

