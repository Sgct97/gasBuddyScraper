#!/usr/bin/env python3
"""
Test optimized approach: One CSRF request, then pure GraphQL
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("TESTING OPTIMIZED BANDWIDTH APPROACH")
print("="*70)

session = requests.Session()
total_bytes = 0

# Step 1: ONE TIME - Get CSRF token from homepage
print("\n1. ONE-TIME SESSION SETUP: Get CSRF token...")
csrf_response = session.get(
    "https://www.gasbuddy.com/",  # Just homepage, no search
    impersonate="chrome120",
    timeout=30
)

csrf_size = len(csrf_response.content)
total_bytes += csrf_size

print(f"   Response size: {csrf_size:,} bytes ({csrf_size/1024:.2f} KB)")

# Extract CSRF
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', csrf_response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None
print(f"   CSRF token: {csrf_token[:20]}...")

# Step 2: Now scrape multiple ZIPs using ONLY GraphQL
print("\n2. SCRAPING MULTIPLE ZIPS (GraphQL only)...")

test_zips = ["77494", "33773", "90210"]  # Test with 3 ZIPs

for zip_code in test_zips:
    print(f"\n   ZIP {zip_code}:")
    time.sleep(3)  # Be polite
    
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
    
    # Get first page (cursor 0)
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
    
    response_size = len(response.content)
    total_bytes += response_size
    
    if response.status_code == 200:
        data = response.json()
        try:
            stations = data['data']['locationBySearchTerm']['stations']['results']
            page_info = data['data']['locationBySearchTerm']['stations'].get('pageInfo', {})
            has_next = page_info.get('hasNextPage', False)
            
            print(f"      Request size: {response_size:,} bytes ({response_size/1024:.2f} KB)")
            print(f"      Stations: {len(stations)}")
            print(f"      Has more pages: {has_next}")
        except Exception as e:
            print(f"      ❌ Parse error: {e}")
            print(f"      Response preview: {str(response.json())[:200]}")
    else:
        print(f"      ❌ Failed: {response.status_code}")

# Summary
print("\n" + "="*70)
print("BANDWIDTH SUMMARY")
print("="*70)
print(f"\nOne-time CSRF setup: {csrf_size:,} bytes ({csrf_size/1024:.2f} KB)")
print(f"Scraping {len(test_zips)} ZIPs: {(total_bytes - csrf_size):,} bytes ({(total_bytes - csrf_size)/1024:.2f} KB)")
print(f"Average per ZIP: {(total_bytes - csrf_size)/len(test_zips)/1024:.2f} KB")
print(f"\nTotal: {total_bytes:,} bytes ({total_bytes/1024:.2f} KB)")

# Extrapolate to full scale
avg_per_zip_kb = (total_bytes - csrf_size) / len(test_zips) / 1024
csrf_kb = csrf_size / 1024

print("\n" + "="*70)
print("FULL SCALE PROJECTION (30,000 ZIPs)")
print("="*70)

total_kb = csrf_kb + (avg_per_zip_kb * 30000)
total_mb = total_kb / 1024
total_gb = total_mb / 1024

print(f"\nPer scrape: {total_gb:.2f} GB")
print(f"Per day (2x): {total_gb * 2:.2f} GB")
print(f"Per month (60x): {total_gb * 60:.2f} GB")

print("\n💡 Compared to old approach (759 GB/month):")
print(f"   New: {total_gb * 60:.0f} GB/month")
print(f"   Savings: {((759 - (total_gb * 60))/759)*100:.0f}%")

print("\n" + "="*70)
print("UPDATED COSTS")
print("="*70)
monthly_gb = total_gb * 60
print(f"\nWithout proxies: Still ~$28-56/month (VPS)")
print(f"With proxies @ $10/GB: ${monthly_gb * 10:.0f}/month (down from $7,591)")
print(f"With proxies @ $3/GB: ${monthly_gb * 3:.0f}/month (down from $2,277)")
print("="*70)

