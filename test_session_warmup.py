#!/usr/bin/env python3
"""
Test if session needs "warm up" - maybe GraphQL checks if we loaded the page recently
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("TEST: Does session need warm-up time?")
print("="*70)

session = requests.Session()

print("\n1. Loading initial page...")
response = session.get(
    "https://www.gasbuddy.com/home?search=77494",
    impersonate="chrome120",
    timeout=30,
    allow_redirects=True
)

print(f"   Status: {response.status_code}")
print(f"   URL: {response.url}")
print(f"   Cookies: {list(session.cookies.keys())}")

# Extract CSRF
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None
print(f"   CSRF: {csrf_token[:20] if csrf_token else 'None'}...")

print("\n2. Waiting 3 seconds (mimicking user behavior)...")
time.sleep(3)

print("\n3. Making GraphQL request...")

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
        "cursor": "20"
    },
    "query": GRAPHQL_QUERY
}

# Try with same session
graphql_response = session.post(
    "https://www.gasbuddy.com/graphql",
    json=payload,
    headers=headers,
    impersonate="chrome120",
    timeout=15
)

print(f"   Status: {graphql_response.status_code}")
print(f"   Headers: {dict(graphql_response.headers)}")

if graphql_response.status_code == 200:
    data = graphql_response.json()
    if 'data' in data:
        stations = data['data']['locationBySearchTerm']['stations']['results']
        print(f"\n✅✅✅ SUCCESS! Got {len(stations)} stations")
        print("\nPure curl_cffi WORKS!")
    else:
        print(f"\nGot 200 but: {json.dumps(data, indent=2)[:500]}")
else:
    print(f"\n❌ Still {graphql_response.status_code}")
    print(f"Response: {graphql_response.text[:300]}")
    
    print("\n" + "="*70)
    print("CONCLUSION: Pure curl_cffi doesn't work")
    print("="*70)
    print("The GraphQL endpoint likely checks:")
    print("  - JavaScript execution proof")
    print("  - WebSocket connections")
    print("  - Browser-specific behavior we can't mimic")
    print("\n💡 NEXT STEP: Hybrid approach (Playwright session → curl_cffi)")
    print("="*70)

