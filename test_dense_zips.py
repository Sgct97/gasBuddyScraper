#!/usr/bin/env python3
"""
Test known dense urban ZIPs to find one with 40+ stations (needs 2+ pages)
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("FINDING A ZIP WITH 40+ STATIONS FOR MULTI-PAGE TEST")
print("="*70)

session = requests.Session()

# Get CSRF token once
print("\n1. Getting session/CSRF...")
csrf_response = session.get(
    "https://www.gasbuddy.com/",
    impersonate="chrome120",
    timeout=30
)

csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', csrf_response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None
print(f"   CSRF: {csrf_token[:20]}...")

# Test dense urban areas
test_zips = {
    "10001": "Manhattan, NYC",
    "90012": "Downtown LA",
    "60601": "Downtown Chicago", 
    "75201": "Downtown Dallas",
    "77002": "Downtown Houston",
    "33125": "Miami",
    "19019": "Philadelphia",
    "02101": "Boston",
    "85001": "Phoenix",
    "94102": "San Francisco"
}

print("\n2. Testing dense ZIPs...")

dense_zips = []

headers = {
    "accept": "*/*",
    "apollo-require-preflight": "true",
    "content-type": "application/json",
    "gbcsrf": csrf_token,
    "origin": "https://www.gasbuddy.com",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
}

for zip_code, location in test_zips.items():
    print(f"\n   Testing {zip_code} ({location})...")
    time.sleep(2)
    
    headers["referer"] = f"https://www.gasbuddy.com/home?search={zip_code}"
    
    payload = {
        "operationName": "LocationBySearchTerm",
        "variables": {
            "fuel": 1,
            "lang": "en",
            "search": zip_code,
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
    
    if response.status_code == 200:
        data = response.json()
        stations = data['data']['locationBySearchTerm']['stations']['results']
        count = len(stations)
        print(f"      Got {count} stations on first page")
        
        if count >= 20:
            dense_zips.append((zip_code, location, count))
            print(f"      ✅ Potential candidate (has pagination)")

print("\n" + "="*70)
print("CANDIDATES FOR MULTI-PAGE TEST")
print("="*70)

if dense_zips:
    print("\nZIPs that returned 20 stations (likely have more):")
    for zip_code, location, count in dense_zips:
        print(f"  {zip_code} ({location}): {count} on page 1")
    
    # Test pagination on the first candidate
    best_zip, best_location, _ = dense_zips[0]
    print(f"\n" + "="*70)
    print(f"TESTING PAGINATION ON {best_zip} ({best_location})")
    print("="*70)
    
    all_stations = []
    cursor = "0"
    page = 1
    
    while page <= 5:  # Test up to 5 pages
        print(f"\nPage {page} (cursor={cursor})...")
        time.sleep(3)
        
        headers["referer"] = f"https://www.gasbuddy.com/home?search={best_zip}"
        
        payload = {
            "operationName": "LocationBySearchTerm",
            "variables": {
                "fuel": 1,
                "lang": "en",
                "search": best_zip,
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
        
        if response.status_code == 200:
            data = response.json()
            stations = data['data']['locationBySearchTerm']['stations']['results']
            print(f"   Got {len(stations)} stations")
            
            if len(stations) == 0:
                print(f"   No more stations")
                break
            
            all_stations.extend(stations)
            
            # Next cursor
            cursor = str(len(all_stations))
            page += 1
        else:
            print(f"   Failed: {response.status_code}")
            break
    
    print(f"\n✅ TOTAL for {best_zip}: {len(all_stations)} stations across {page-1} pages")
    
    if len(all_stations) > 40:
        print(f"\n🎉 Found a good test ZIP: {best_zip} with {len(all_stations)} stations!")
        print(f"   This requires {(len(all_stations)-1)//20 + 1} pages")
    else:
        print(f"\n   Only {len(all_stations)} stations - not enough for multi-page test")
else:
    print("\n⚠️  None of these ZIPs had 20+ stations")
    print("   May need to try other areas or methods")

print("="*70)

