#!/usr/bin/env python3
"""
Test if gbcsrf token is required
"""
import requests
import json
import re

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("TESTING CSRF TOKEN REQUIREMENT")
print("="*70)

# Step 1: Load HTML and extract csrf token
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})

print("\n1. Loading HTML page...")
html_response = session.get("https://www.gasbuddy.com/home?search=77494", timeout=10)
print(f"   Status: {html_response.status_code}")
print(f"   Cookies: {list(session.cookies.keys())}")

# Look for gbcsrf in cookies
csrf_token = session.cookies.get('gbcsrf')
print(f"   gbcsrf cookie: {csrf_token}")

# Also check response headers
print(f"   Response headers with 'csrf': {[k for k in html_response.headers.keys() if 'csrf' in k.lower()]}")

# Try to find it in HTML
html = html_response.text
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([a-zA-Z0-9._+\-/]+)', html, re.I)
if csrf_matches:
    print(f"   Found in HTML: {csrf_matches[:3]}")

# Step 2: Try GraphQL WITH csrf token
print("\n2. Testing GraphQL WITH gbcsrf header...")
url = "https://www.gasbuddy.com/graphql"
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

if csrf_token:
    headers = {
        "Content-Type": "application/json",
        "apollo-require-preflight": "true",
        "gbcsrf": csrf_token,
        "Referer": "https://www.gasbuddy.com/home?search=77494"
    }
    
    response = session.post(url, json=payload, headers=headers, timeout=10)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and data['data']:
            stations = data['data']['locationBySearchTerm']['stations']['results']
            print(f"   ✅✅✅ SUCCESS! Got {len(stations)} stations")
            print(f"\n   First station: {stations[0]['name']}")
        else:
            print(f"   ⚠️  Got 200 but response: {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"   ❌ Failed: {response.text[:200]}")
else:
    print("   ❌ No csrf token found!")

print("\n" + "="*70)

