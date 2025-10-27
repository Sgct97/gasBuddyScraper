#!/usr/bin/env python3
"""
VERIFY: Can we paginate using GraphQL-only approach?
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("TESTING: GraphQL-only pagination for ZIP 77494 (34 stations)")
print("="*70)

session = requests.Session()

# Get CSRF token
print("\n1. Getting CSRF token...")
csrf_response = session.get(
    "https://www.gasbuddy.com/",
    impersonate="chrome120",
    timeout=30
)

csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', csrf_response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None
print(f"   CSRF: {csrf_token[:20]}...")

all_stations = []
cursor = "0"
page_num = 1

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

# Try to paginate
while True:
    print(f"\n2. GraphQL request - Page {page_num} (cursor={cursor})...")
    time.sleep(3)
    
    payload = {
        "operationName": "LocationBySearchTerm",
        "variables": {
            "fuel": 1,
            "lang": "en",
            "search": "77494",
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
    
    if response.status_code != 200:
        print(f"   ❌ Failed: {response.status_code}")
        break
    
    data = response.json()
    stations_data = data['data']['locationBySearchTerm']['stations']
    stations = stations_data['results']
    page_info = stations_data.get('pageInfo', {})
    
    print(f"   Got {len(stations)} stations")
    print(f"   Page info: {page_info}")
    
    # Add to collection
    all_stations.extend(stations)
    
    # Check if there's more
    has_next = page_info.get('hasNextPage', False)
    next_cursor = page_info.get('endCursor')
    
    if not has_next or not next_cursor:
        print(f"   No more pages")
        break
    
    cursor = next_cursor
    page_num += 1
    
    if page_num > 5:  # Safety limit
        print("   Safety limit reached")
        break

# Summary
print("\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"\nTotal stations retrieved: {len(all_stations)}")
print(f"Expected: 34")
print(f"Match: {'✅ YES' if len(all_stations) == 34 else '❌ NO'}")

if len(all_stations) < 34:
    print("\n⚠️  PROBLEM: GraphQL-only approach might not get all stations!")
    print("   Let me test the OLD approach for comparison...")
else:
    print("\n✅ CONFIRMED: GraphQL-only approach gets all stations!")
    print("\nStation IDs retrieved:")
    for i, station in enumerate(all_stations[:5], 1):
        print(f"  {i}. {station['name']} (ID: {station['id']})")
    if len(all_stations) > 5:
        print(f"  ... and {len(all_stations) - 5} more")

