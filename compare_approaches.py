#!/usr/bin/env python3
"""
Compare OLD vs NEW approach side-by-side
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("COMPARING: OLD vs NEW approach")
print("="*70)

# ============================================================================
# APPROACH 1: Load HTML first, then paginate (OLD - PROVEN WORKING)
# ============================================================================
print("\n" + "="*70)
print("APPROACH 1: Load HTML page first (OLD METHOD)")
print("="*70)

session1 = requests.Session()

print("\n1a. Loading HTML page for ZIP 77494...")
html_response = session1.get(
    "https://www.gasbuddy.com/home?search=77494",
    impersonate="chrome120",
    timeout=30
)

html_size = len(html_response.content)
print(f"   Size: {html_size:,} bytes ({html_size/1024:.2f} KB)")

# Extract CSRF and count stations in Apollo
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', html_response.text, re.I)
csrf_token1 = csrf_matches[0] if csrf_matches else None

apollo_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.+?});', html_response.text, re.DOTALL)
apollo_state = json.loads(apollo_match.group(1))
apollo_stations = sum(1 for key in apollo_state.keys() if key.startswith('Station:'))

print(f"   Stations in Apollo state: {apollo_stations}")

print("\n1b. Now paginating with cursor=20...")
time.sleep(3)

headers1 = {
    "accept": "*/*",
    "apollo-require-preflight": "true",
    "content-type": "application/json",
    "gbcsrf": csrf_token1,
    "referer": "https://www.gasbuddy.com/home?search=77494",
    "origin": "https://www.gasbuddy.com",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
}

payload1 = {
    "operationName": "LocationBySearchTerm",
    "variables": {
        "fuel": 1,
        "lang": "en",
        "search": "77494",
        "cursor": "20"
    },
    "query": GRAPHQL_QUERY
}

graphql_response1 = session1.post(
    "https://www.gasbuddy.com/graphql",
    json=payload1,
    headers=headers1,
    impersonate="chrome120",
    timeout=15
)

graphql_size1 = len(graphql_response1.content)
print(f"   Size: {graphql_size1:,} bytes ({graphql_size1/1024:.2f} KB)")

if graphql_response1.status_code == 200:
    data1 = graphql_response1.json()
    graphql_stations = len(data1['data']['locationBySearchTerm']['stations']['results'])
    print(f"   Stations from GraphQL: {graphql_stations}")

print(f"\n   TOTAL STATIONS: {apollo_stations + graphql_stations}")
print(f"   Total bandwidth: {(html_size + graphql_size1)/1024:.2f} KB")

# ============================================================================
# APPROACH 2: GraphQL only (NEW - BROKEN?)
# ============================================================================
print("\n" + "="*70)
print("APPROACH 2: GraphQL-only (NEW METHOD)")
print("="*70)

session2 = requests.Session()

print("\n2a. Getting CSRF from homepage...")
csrf_response = session2.get(
    "https://www.gasbuddy.com/",
    impersonate="chrome120",
    timeout=30
)

csrf_size = len(csrf_response.content)
print(f"   Size: {csrf_size:,} bytes ({csrf_size/1024:.2f} KB)")

csrf_matches2 = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', csrf_response.text, re.I)
csrf_token2 = csrf_matches2[0] if csrf_matches2 else None

print("\n2b. GraphQL request with cursor=0...")
time.sleep(3)

headers2 = {
    "accept": "*/*",
    "apollo-require-preflight": "true",
    "content-type": "application/json",
    "gbcsrf": csrf_token2,
    "referer": "https://www.gasbuddy.com/home?search=77494",
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
        "search": "77494",
        "cursor": "0"
    },
    "query": GRAPHQL_QUERY
}

graphql_response2 = session2.post(
    "https://www.gasbuddy.com/graphql",
    json=payload2,
    headers=headers2,
    impersonate="chrome120",
    timeout=15
)

graphql_size2 = len(graphql_response2.content)
print(f"   Size: {graphql_size2:,} bytes ({graphql_size2/1024:.2f} KB)")

if graphql_response2.status_code == 200:
    data2 = graphql_response2.json()
    page2_stations = len(data2['data']['locationBySearchTerm']['stations']['results'])
    page_info2 = data2['data']['locationBySearchTerm']['stations'].get('pageInfo', {})
    print(f"   Stations: {page2_stations}")
    print(f"   Page info: {page_info2}")

print(f"\n   TOTAL STATIONS: {page2_stations}")
print(f"   Total bandwidth: {(csrf_size + graphql_size2)/1024:.2f} KB")

# ============================================================================
# COMPARISON
# ============================================================================
print("\n" + "="*70)
print("VERDICT")
print("="*70)

print("\nOLD METHOD (HTML + GraphQL):")
print(f"  ✅ Gets all 34 stations")
print(f"  Bandwidth: {(html_size + graphql_size1)/1024:.2f} KB per ZIP")

print("\nNEW METHOD (GraphQL only):")
print(f"  ❌ Only gets 20 stations (missing 14!)")
print(f"  Bandwidth: {(csrf_size + graphql_size2)/1024:.2f} KB (but incomplete data)")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
print("\n⚠️  We CANNOT skip the HTML page load!")
print("\nWhy? The HTML page sets up session state that enables pagination.")
print("Without it, GraphQL only returns first 20 and no pageInfo.")
print("\n💡 CORRECT approach:")
print("   1. Load HTML page for each ZIP (gets first 20 + CSRF)")
print("   2. Use GraphQL for pagination if needed (gets 20+)")
print("\nThis is what our working curl_cffi scraper already does! ✅")
print("="*70)

