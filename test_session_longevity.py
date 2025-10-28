#!/usr/bin/env python3
"""
Test session longevity and CSRF token expiration
"""
from curl_cffi import requests
import json
import re
import time
import base64
from datetime import datetime

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

# Oxylabs proxy
PROXY_USERNAME = "gasBuddyScraper_5gUpP"
PROXY_PASSWORD = "gasBuddyScraper_123"
PROXY_HOST = "isp.oxylabs.io"
PROXY_URL = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:8001"

print("="*70)
print("TESTING: SESSION LONGEVITY & CSRF TOKEN")
print("="*70)

# Step 1: Get session and inspect CSRF token
print("\n1. Getting session and analyzing CSRF token...")

session = requests.Session()
proxies = {"http": PROXY_URL, "https": PROXY_URL}

response = session.get(
    "https://www.gasbuddy.com/",
    proxies=proxies,
    impersonate="chrome120",
    timeout=30
)

csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

print(f"\n   Full CSRF token: {csrf_token}")
print(f"   Length: {len(csrf_token)} characters")

# Try to decode if it's base64 or JWT-like
parts = csrf_token.split('.')
print(f"   Parts (split by '.'): {len(parts)}")

for i, part in enumerate(parts):
    print(f"\n   Part {i}: {part}")
    
    # Try base64 decode
    if len(part) > 10:
        try:
            decoded = base64.b64decode(part + '==')  # Add padding
            print(f"      Base64 decoded: {decoded}")
        except:
            pass
        
        try:
            decoded = base64.urlsafe_b64decode(part + '==')
            print(f"      URL-safe Base64: {decoded}")
        except:
            pass

# Check cookies
print("\n2. Checking session cookies...")
for cookie in session.cookies:
    print(f"   {cookie.name}:")
    print(f"      Value: {cookie.value[:50]}...")
    print(f"      Domain: {cookie.domain}")
    print(f"      Path: {cookie.path}")
    print(f"      Expires: {cookie.expires}")
    if cookie.expires:
        expire_time = datetime.fromtimestamp(cookie.expires)
        now = datetime.now()
        ttl = expire_time - now
        print(f"      TTL: {ttl}")

# Check response headers for caching/expiration
print("\n3. Response headers (caching related)...")
cache_headers = ['cache-control', 'expires', 'age', 'date', 'last-modified', 'etag']
for header in cache_headers:
    if header in response.headers:
        print(f"   {header}: {response.headers[header]}")

# Step 2: Test CSRF token at different intervals
print("\n" + "="*70)
print("4. TESTING CSRF TOKEN LONGEVITY")
print("="*70)

test_intervals = [
    (0, "Immediately"),
    (60, "1 minute"),
    (300, "5 minutes"),
    (600, "10 minutes"),
    (1800, "30 minutes"),
    (3600, "1 hour"),
]

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

start_time = time.time()

for delay_seconds, label in test_intervals:
    if delay_seconds > 0:
        wait_time = delay_seconds - (time.time() - start_time)
        if wait_time > 0:
            print(f"\n   Waiting {wait_time:.0f}s for next test ({label})...")
            time.sleep(wait_time)
    
    elapsed = time.time() - start_time
    print(f"\n   Testing after {elapsed:.0f}s ({label})...")
    
    try:
        test_response = session.post(
            "https://www.gasbuddy.com/graphql",
            json=payload,
            headers=headers,
            proxies=proxies,
            impersonate="chrome120",
            timeout=15
        )
        
        if test_response.status_code == 200:
            data = test_response.json()
            stations = data['data']['locationBySearchTerm']['stations']['results']
            print(f"      ✅ SUCCESS: Got {len(stations)} stations (status 200)")
        elif test_response.status_code == 401:
            print(f"      ❌ EXPIRED: 401 Unauthorized - CSRF token expired")
            break
        elif test_response.status_code == 403:
            print(f"      ❌ FORBIDDEN: 403 - May indicate session expired")
            break
        else:
            print(f"      ⚠️  Status {test_response.status_code}")
            
    except Exception as e:
        print(f"      ❌ ERROR: {e}")
        break

print("\n" + "="*70)
print("CONCLUSIONS")
print("="*70)
print("\n📊 CSRF Token Analysis:")
print("   - Structure suggests version.token format")
print("   - Need to observe when it expires in practice")
print("\n⏱️  Session Longevity:")
print("   - Run this test to see how long tokens stay valid")
print("   - If valid >1 hour, one session can scrape all 30K ZIPs")
print("   - If expires sooner, need to refresh session periodically")
print("="*70)

