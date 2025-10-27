#!/usr/bin/env python3
"""
THE REAL TEST: Can we get ALL stations for 77494 without loading its HTML?
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("TESTING: Can we get ALL 34 stations WITHOUT loading HTML for 77494?")
print("="*70)

session = requests.Session()

# Load HTML for a DIFFERENT ZIP to establish session
print("\n1. Loading HTML for ZIP 33773 (NOT our target)...")
html_response = session.get(
    "https://www.gasbuddy.com/home?search=33773",
    impersonate="chrome120",
    timeout=30
)

csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', html_response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None
print(f"   Got CSRF token: {csrf_token[:20]}...")

# Now try to query 77494 (our target with 34 stations)
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

response = session.post(
    "https://www.gasbuddy.com/graphql",
    json=payload,
    headers=headers,
    impersonate="chrome120",
    timeout=15
)

all_stations = []

if response.status_code == 200:
    data = response.json()
    stations = data['data']['locationBySearchTerm']['stations']['results']
    page_info = data['data']['locationBySearchTerm']['stations'].get('pageInfo', {})
    
    print(f"   Got {len(stations)} stations")
    print(f"   Page info: {page_info}")
    all_stations.extend(stations)
    
    # Now try to paginate with cursor=20
    print("\n3. Trying to paginate 77494 with cursor=20...")
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
    
    if response2.status_code == 200:
        data2 = response2.json()
        stations2 = data2['data']['locationBySearchTerm']['stations']['results']
        print(f"   Got {len(stations2)} more stations")
        all_stations.extend(stations2)
    else:
        print(f"   ❌ Failed: {response2.status_code}")
else:
    print(f"   ❌ Failed: {response.status_code}")

# Summary
print("\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"\nTotal stations for 77494: {len(all_stations)}")
print(f"Expected: 34")

if len(all_stations) == 34:
    print("\n🎉 SUCCESS! We can get all stations WITHOUT loading HTML for that ZIP!")
    print("\n💡 OPTIMIZATION UNLOCKED:")
    print("   1. Load ONE HTML page per scrape session (any ZIP)")
    print("   2. Query all 30K ZIPs via GraphQL")
    print("   3. Paginate with cursor=20, 40, 60... as needed")
    print("\n   Bandwidth per scrape: ~0.86 GB instead of 12.65 GB")
    print("   Monthly (60 scrapes): ~52 GB instead of 759 GB")
    print("   Cost with proxies @ $10/GB: $520/month instead of $7,591!")
elif len(all_stations) == 20:
    print("\n❌ FAILED: Only got first 20 stations")
    print("\n   We MUST load HTML for each ZIP to enable pagination")
    print("   No optimization possible - stuck with 759 GB/month")
else:
    print(f"\n⚠️  Got {len(all_stations)} stations (unexpected)")

print("="*70)

