#!/usr/bin/env python3
"""
Compare curl_cffi vs Playwright to find what's different
"""
from curl_cffi import requests
import json
import re

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("DEEP DIVE: What's different between curl_cffi and Playwright?")
print("="*70)

# Load the successful Playwright request from manual capture
with open('manual_click_capture_20251027_104258.json') as f:
    data = json.load(f)

graphql_req = [r for r in data if 'graphql' in r['url']][0]

print("\n1. SUCCESSFUL Playwright GraphQL Headers:")
print("-" * 70)
working_headers = graphql_req['headers']
for k, v in sorted(working_headers.items()):
    print(f"  {k}: {v}")

print("\n2. Let me try curl_cffi with EXACT same headers...")
print("-" * 70)

# Get session first
session = requests.Session()
initial_response = session.get(
    "https://www.gasbuddy.com/home?search=77494",
    impersonate="chrome120",
    timeout=30
)

# Extract CSRF
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', initial_response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

print(f"Got CSRF: {csrf_token}")
print(f"Cookies from initial request: {dict(session.cookies)}")

# Now try GraphQL with ALL the headers from working request
headers = {
    "accept": working_headers.get('accept', '*/*'),
    "apollo-require-preflight": working_headers.get('apollo-require-preflight', 'true'),
    "content-type": working_headers.get('content-type', 'application/json'),
    "gbcsrf": csrf_token,
    "referer": working_headers.get('referer', 'https://www.gasbuddy.com/home?search=77494'),
    "sec-ch-ua": working_headers.get('sec-ch-ua', '"Not=A?Brand";v="24", "Chromium";v="140"'),
    "sec-ch-ua-mobile": working_headers.get('sec-ch-ua-mobile', '?0'),
    "sec-ch-ua-platform": working_headers.get('sec-ch-ua-platform', '"macOS"'),
    "user-agent": working_headers.get('user-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36')
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

print("\n3. Making GraphQL request with exact headers...")

response = session.post(
    "https://www.gasbuddy.com/graphql",
    json=payload,
    headers=headers,
    impersonate="chrome120",
    timeout=15
)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    if 'data' in data:
        stations = data['data']['locationBySearchTerm']['stations']['results']
        print(f"✅✅✅ IT WORKED! Got {len(stations)} stations")
        print("\nThis means curl_cffi CAN work - just needed exact headers!")
    else:
        print(f"Got 200 but: {data}")
else:
    print(f"Still failed: {response.text[:200]}")
    
print("\n4. Checking cookie differences...")
print(f"curl_cffi cookies: {dict(session.cookies)}")
print("\nLet me check what cookies the browser had...")

# Check if there are any cookies we're missing
print("\nPossible issues:")
print("1. Missing specific cookies from browser")
print("2. Session needs to be 'warmed up' with other requests first")
print("3. GraphQL endpoint checks request order/timing")
print("4. TLS fingerprint differences")

