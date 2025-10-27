#!/usr/bin/env python3
"""
Test a single GraphQL call right after loading HTML
"""
import requests
import json
import re

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

# Create session
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
})

print("Step 1: Load HTML page...")
html_response = session.get("https://www.gasbuddy.com/home?search=77494", timeout=15)
print(f"  Status: {html_response.status_code}")
print(f"  Cookies: {dict(session.cookies)}")

# Extract CSRF
html = html_response.text
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', html, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None
print(f"  CSRF: {csrf_token}")

if not csrf_token:
    print("ERROR: No CSRF token found!")
    exit(1)

print("\nStep 2: Make GraphQL call...")

headers = {
    "accept": "*/*",
    "apollo-require-preflight": "true",
    "content-type": "application/json",
    "gbcsrf": csrf_token,
    "referer": "https://www.gasbuddy.com/home?search=77494",
    "sec-ch-ua": '"Not=A?Brand";v="24", "Chromium";v="140"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
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

print(f"  Sending to: https://www.gasbuddy.com/graphql")
print(f"  Headers: {list(headers.keys())}")
print(f"  Payload variables: {payload['variables']}")

response = session.post("https://www.gasbuddy.com/graphql", json=payload, headers=headers, timeout=15)

print(f"\nResponse:")
print(f"  Status: {response.status_code}")
print(f"  Headers: {dict(response.headers)}")

if response.status_code == 200:
    try:
        data = response.json()
        if 'data' in data:
            stations = data['data']['locationBySearchTerm']['stations']['results']
            total = data['data']['locationBySearchTerm']['stations']['count']
            cursor = data['data']['locationBySearchTerm']['stations']['cursor']
            print(f"\n✅ SUCCESS!")
            print(f"  Stations: {len(stations)}")
            print(f"  Total: {total}")
            print(f"  Next cursor: {cursor.get('next') if cursor else None}")
        else:
            print(f"\n❌ No data in response:")
            print(json.dumps(data, indent=2)[:500])
    except Exception as e:
        print(f"\n❌ Parse error: {e}")
        print(response.text[:500])
else:
    print(f"\n❌ Failed:")
    print(response.text[:500])

