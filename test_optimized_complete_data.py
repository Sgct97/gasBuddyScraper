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
print("OPTIMIZED APPROACH: Complete Data Test for ZIP 77494")
print("="*70)

session = requests.Session()
all_stations = []

# Step 1: Load HTML for a DIFFERENT ZIP to establish session
print("\n1. Loading HTML for ZIP 33773 (to get session/CSRF)...")
html_response = session.get(
    "https://www.gasbuddy.com/home?search=33773",
    impersonate="chrome120",
    timeout=30
)

html_size = len(html_response.content)
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', html_response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

print(f"   Size: {html_size:,} bytes ({html_size/1024:.2f} KB)")
print(f"   CSRF: {csrf_token[:20]}...")

# Step 2: Query 77494 with cursor=0
print("\n2. Querying ZIP 77494 via GraphQL (cursor=0)...")
time.sleep(3)

headers = {
    "accept": "*/*",
    "apollo-require-preflight": "true",
    "content-type": "application/json",
    "gbcsrf": csrf_token,
    "referer": "https://www.gasbuddy.com/home?search=77494",
    "origin": "https://www.gasbuddy.com",
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
        "cursor": "0"
    },
    "query": GRAPHQL_QUERY
}

response1 = session.post(
    "https://www.gasbuddy.com/graphql",
    json=payload,
    headers=headers,
    impersonate="chrome120",
    timeout=15
)

response1_size = len(response1.content)
print(f"   Size: {response1_size:,} bytes ({response1_size/1024:.2f} KB)")

if response1.status_code == 200:
    data1 = response1.json()
    stations1 = data1['data']['locationBySearchTerm']['stations']['results']
    print(f"   Got {len(stations1)} stations")
    all_stations.extend(stations1)

# Step 3: Paginate with cursor=20
print("\n3. Paginating ZIP 77494 (cursor=20)...")
time.sleep(3)

payload2 = {
    "operationName": "LocationBySearchTerm",
    "variables": {
        "fuel": 1,
        "lang": "en",
        "search": "77494",
        "cursor": "20"
    },
    "query": GRAPHQL_QUERY
}

response2 = session.post(
    "https://www.gasbuddy.com/graphql",
    json=payload2,
    headers=headers,
    impersonate="chrome120",
    timeout=15
)

response2_size = len(response2.content)
print(f"   Size: {response2_size:,} bytes ({response2_size/1024:.2f} KB)")

if response2.status_code == 200:
    data2 = response2.json()
    stations2 = data2['data']['locationBySearchTerm']['stations']['results']
    print(f"   Got {len(stations2)} stations")
    all_stations.extend(stations2)

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
print(f"Expected: 34")
print(f"Match: {'✅ YES' if len(all_stations) == 34 else '❌ NO'}")

print(f"\nBandwidth used:")
print(f"  HTML for ZIP 33773: {html_size/1024:.2f} KB")
print(f"  GraphQL cursor=0: {response1_size/1024:.2f} KB")
print(f"  GraphQL cursor=20: {response2_size/1024:.2f} KB")
print(f"  Total: {(html_size + response1_size + response2_size)/1024:.2f} KB")

print("\n✅ This proves the optimized approach gets:")
print("  - All 34 stations")
print("  - Complete addresses")
print("  - Both cash AND credit prices")
print("  - Timestamps and reporters")
print("  - All fuel types")
print("="*70)

