#!/usr/bin/env python3
"""
Inspect session cookies and CSRF token for expiration metadata
"""
from curl_cffi import requests
import json
import re
from datetime import datetime, timedelta

PROXY_USERNAME = "gasBuddyScraper_5gUpP"
PROXY_PASSWORD = "gasBuddyScraper_123"
PROXY_HOST = "isp.oxylabs.io"
PROXY_URL = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:8001"

print("="*70)
print("INSPECTING SESSION METADATA FOR EXPIRATION INFO")
print("="*70)

session = requests.Session()
proxies = {"http": PROXY_URL, "https": PROXY_URL}

print("\n1. Making initial request to establish session...")
response = session.get(
    "https://www.gasbuddy.com/",
    proxies=proxies,
    impersonate="chrome120",
    timeout=30
)

# Extract CSRF token
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

print(f"\n2. CSRF Token Analysis:")
print(f"   Token: {csrf_token}")
print(f"   Length: {len(csrf_token)} chars")
print(f"   Format: {'.' in csrf_token and 'version.signature' or 'opaque string'}")

# Analyze CSRF structure
if '.' in csrf_token:
    parts = csrf_token.split('.')
    print(f"   Parts: {len(parts)}")
    print(f"      Part 1 (version?): {parts[0]}")
    print(f"      Part 2 (token): {parts[1][:20]}...")
    print("\n   ⚠️  CSRF token does NOT contain expiration timestamp")
    print("   Server-side validation determines if it's expired")

print(f"\n3. Session Cookies Analysis:")

# curl_cffi stores cookies differently - need to use items()
cookies_dict = dict(session.cookies)
print(f"   Total cookies: {len(cookies_dict)}")

has_expiration = False

# Also check raw cookie headers
cookie_headers = response.headers.get('set-cookie', '')
print(f"\n   Raw Set-Cookie headers:")
if cookie_headers:
    # Split multiple set-cookie headers
    cookie_lines = cookie_headers.split('\n') if '\n' in cookie_headers else [cookie_headers]
    for line in cookie_lines:
        print(f"      {line[:100]}...")
        
        # Check for Max-Age or Expires
        if 'Max-Age=' in line:
            has_expiration = True
            max_age_match = re.search(r'Max-Age=(\d+)', line)
            if max_age_match:
                seconds = int(max_age_match.group(1))
                hours = seconds / 3600
                print(f"         ✅ Max-Age: {seconds}s ({hours:.1f} hours)")
        
        if 'expires=' in line.lower():
            has_expiration = True
            exp_match = re.search(r'expires=([^;]+)', line, re.IGNORECASE)
            if exp_match:
                exp_str = exp_match.group(1)
                print(f"         ✅ Expires: {exp_str}")
                
                # Try to parse the expiration date
                try:
                    from email.utils import parsedate_to_datetime
                    exp_datetime = parsedate_to_datetime(exp_str)
                    now = datetime.now(exp_datetime.tzinfo)
                    ttl = exp_datetime - now
                    
                    print(f"         ⏱️  TTL: {ttl}")
                    print(f"         ⏱️  Hours left: {ttl.total_seconds() / 3600:.1f}")
                    print(f"         ⏱️  Minutes left: {ttl.total_seconds() / 60:.1f}")
                except Exception as e:
                    print(f"         ⚠️  Could not parse date: {e}")
else:
    print(f"      (No Set-Cookie headers found)")

print(f"\n   Cookie values:")
for name, value in cookies_dict.items():
    print(f"      {name}: {value[:50]}...")

print(f"\n4. Response Headers (caching/expiration):")
relevant_headers = ['cache-control', 'expires', 'age', 'set-cookie']
for header in relevant_headers:
    if header in response.headers:
        print(f"   {header}: {response.headers[header]}")

print("\n" + "="*70)
print("ANSWER: Can we determine session validity programmatically?")
print("="*70)

if has_expiration:
    print("\n✅ YES - Cookies have explicit expiration timestamps!")
    print("   We can programmatically determine session validity")
    print("   Note: CSRF token itself has no embedded expiration,")
    print("   but likely tied to cookie lifetime")
else:
    print("\n⚠️  NO - Cookies appear to be session-only")
    print("   Need to test empirically how long they work")

print("\n💡 Recommendation:")
print("   Since we can't read expiration from token/cookies,")
print("   we should:")
print("   1. Test empirically (5min, 10min, 30min, 1hr, 2hr)")
print("   2. In production, refresh session every 30-60 minutes as safety")
print("   3. Implement error handling for 401/403 (session expired)")
print("="*70)

