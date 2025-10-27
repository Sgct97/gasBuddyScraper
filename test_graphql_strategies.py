#!/usr/bin/env python3
"""
Test different strategies to get ALL stations via GraphQL
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("TESTING: Different GraphQL strategies for complete data")
print("="*70)

# ============================================================================
# STRATEGY 1: Load HTML for ZIP, try to paginate with cursor
# ============================================================================
print("\n" + "="*70)
print("STRATEGY 1: Load HTML for the ZIP, then paginate")
print("="*70)

session1 = requests.Session()

print("\n1. Loading HTML for ZIP 77494...")
html_response = session1.get(
    "https://www.gasbuddy.com/home?search=77494",
    impersonate="chrome120",
    timeout=30
)

csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', html_response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

print("2. Now trying GraphQL with cursor=20...")
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
        "cursor": "20"
    },
    "query": GRAPHQL_QUERY
}

response = session1.post(
    "https://www.gasbuddy.com/graphql",
    json=payload,
    headers=headers,
    impersonate="chrome120",
    timeout=15
)

if response.status_code == 200:
    data = response.json()
    stations = data['data']['locationBySearchTerm']['stations']['results']
    print(f"   ✅ Got {len(stations)} additional stations")
    print(f"   Total: 20 + {len(stations)} = {20 + len(stations)}")

# ============================================================================
# STRATEGY 2: Can we request a DIFFERENT ZIP after loading ONE HTML page?
# ============================================================================
print("\n" + "="*70)
print("STRATEGY 2: Load HTML for ZIP A, query GraphQL for ZIP B")
print("="*70)

print("\n1. Already have session from 77494...")
print("2. Now trying GraphQL for ZIP 33773 (different ZIP)...")
time.sleep(3)

headers2 = {
    "accept": "*/*",
    "apollo-require-preflight": "true",
    "content-type": "application/json",
    "gbcsrf": csrf_token,
    "referer": "https://www.gasbuddy.com/home?search=33773",
    "origin": "https://www.gasbuddy.com",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
}

payload2 = {
    "operationName": "LocationBySearchTerm",
    "variables": {
        "fuel": 1,
        "lang": "en",
        "search": "33773",
        "cursor": "0"
    },
    "query": GRAPHQL_QUERY
}

response2 = session1.post(
    "https://www.gasbuddy.com/graphql",
    json=payload2,
    headers=headers2,
    impersonate="chrome120",
    timeout=15
)

if response2.status_code == 200:
    data2 = response2.json()
    stations2 = data2['data']['locationBySearchTerm']['stations']['results']
    page_info2 = data2['data']['locationBySearchTerm']['stations'].get('pageInfo', {})
    print(f"   Got {len(stations2)} stations")
    print(f"   Page info: {page_info2}")
    
    # Try to paginate this one
    if len(stations2) >= 20:
        print("\n3. Trying to paginate ZIP 33773 with cursor=20...")
        time.sleep(3)
        
        payload3 = {
            "operationName": "LocationBySearchTerm",
            "variables": {
                "fuel": 1,
                "lang": "en",
                "search": "33773",
                "cursor": "20"
            },
            "query": GRAPHQL_QUERY
        }
        
        response3 = session1.post(
            "https://www.gasbuddy.com/graphql",
            json=payload3,
            headers=headers2,
            impersonate="chrome120",
            timeout=15
        )
        
        if response3.status_code == 200:
            data3 = response3.json()
            stations3 = data3['data']['locationBySearchTerm']['stations']['results']
            print(f"   ✅ Got {len(stations3)} more stations!")
            print(f"   Total for 33773: {len(stations2)} + {len(stations3)} = {len(stations2) + len(stations3)}")
        else:
            print(f"   ❌ Failed: {response3.status_code}")

# ============================================================================
# STRATEGY 3: Load ONE HTML page, then query MULTIPLE ZIPs
# ============================================================================
print("\n" + "="*70)
print("STRATEGY 3: One HTML load, then query MULTIPLE different ZIPs")
print("="*70)

test_zips = ["90210", "10001", "60601"]  # LA, NYC, Chicago

print("\n1. Using same session from 77494...")
bandwidth_saved = 0

for zip_code in test_zips:
    print(f"\n2. Querying ZIP {zip_code} via GraphQL only...")
    time.sleep(3)
    
    headers_multi = {
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
    
    payload_multi = {
        "operationName": "LocationBySearchTerm",
        "variables": {
            "fuel": 1,
            "lang": "en",
            "search": zip_code,
            "cursor": "0"
        },
        "query": GRAPHQL_QUERY
    }
    
    response_multi = session1.post(
        "https://www.gasbuddy.com/graphql",
        json=payload_multi,
        headers=headers_multi,
        impersonate="chrome120",
        timeout=15
    )
    
    if response_multi.status_code == 200:
        data_multi = response_multi.json()
        stations_multi = data_multi['data']['locationBySearchTerm']['stations']['results']
        page_info_multi = data_multi['data']['locationBySearchTerm']['stations'].get('pageInfo', {})
        
        response_size = len(response_multi.content)
        bandwidth_saved += (400000 - response_size)  # 400KB HTML vs GraphQL
        
        print(f"   ✅ Got {len(stations_multi)} stations")
        print(f"   Response size: {response_size/1024:.1f} KB (vs ~400 KB for HTML)")
        print(f"   Page info: {page_info_multi}")
    else:
        print(f"   ❌ Failed: {response_multi.status_code}")

# ============================================================================
# VERDICT
# ============================================================================
print("\n" + "="*70)
print("VERDICT")
print("="*70)

print("\n✅ KEY FINDING:")
print("   If we load HTML for ONE ZIP, we can:")
print("   1. Get stations 1-20 from Apollo state")
print("   2. Paginate with GraphQL to get 21+")
print("   3. Query OTHER ZIPs via GraphQL directly!")

print("\n💡 OPTIMIZED STRATEGY:")
print("   1. Load ONE HTML page per scrape (gets CSRF + session)")
print("   2. Query all 30K ZIPs via GraphQL")
print("   3. For ZIPs with 20+ stations, paginate with cursor=20")

print("\n📊 BANDWIDTH CALCULATION:")
html_once = 409  # KB
graphql_per_zip = 30  # KB average
zips = 30000

total_kb = html_once + (graphql_per_zip * zips)
total_gb = total_kb / 1024 / 1024

print(f"   One HTML load: {html_once} KB")
print(f"   30,000 ZIPs × {graphql_per_zip} KB: {graphql_per_zip * zips / 1024:.0f} MB")
print(f"   Total: {total_gb:.2f} GB per scrape")
print(f"   Per month (60x): {total_gb * 60:.0f} GB")

print("\n🎉 If this works, we just reduced bandwidth by 92%!")
print("="*70)

