#!/usr/bin/env python3
"""
Measure actual bandwidth usage for scraping one ZIP code
"""
from curl_cffi import requests
import json
import re
import time
import sys

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("MEASURING BANDWIDTH USAGE")
print("="*70)

session = requests.Session()
total_sent = 0
total_received = 0

# Step 1: Initial page load
print("\n1. Initial page load (HTML + Apollo state)...")
initial_url = "https://www.gasbuddy.com/home?search=77494"
print(f"   URL: {initial_url}")

response = session.get(
    initial_url,
    impersonate="chrome120",
    timeout=30
)

# Calculate request size (rough estimate)
request_size = len(initial_url)
request_size += 500  # Headers (User-Agent, Accept, etc.)

response_size = len(response.content)

print(f"   Request size: {request_size:,} bytes ({request_size/1024:.2f} KB)")
print(f"   Response size: {response_size:,} bytes ({response_size/1024:.2f} KB)")

total_sent += request_size
total_received += response_size

# Extract CSRF for GraphQL
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

# Count stations in Apollo state
apollo_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.+?});', response.text, re.DOTALL)
if apollo_match:
    apollo_state = json.loads(apollo_match.group(1))
    station_count = sum(1 for key in apollo_state.keys() if key.startswith('Station:'))
    print(f"   Stations extracted: {station_count}")

# Step 2: GraphQL pagination (if needed)
print("\n2. GraphQL pagination request...")
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

payload_json = json.dumps(payload)

# Calculate GraphQL request size
graphql_request_size = len("https://www.gasbuddy.com/graphql")
graphql_request_size += len(payload_json)
graphql_request_size += sum(len(k) + len(v) for k, v in headers.items())

graphql_response = session.post(
    "https://www.gasbuddy.com/graphql",
    json=payload,
    headers=headers,
    impersonate="chrome120",
    timeout=15
)

graphql_response_size = len(graphql_response.content)

print(f"   Request size: {graphql_request_size:,} bytes ({graphql_request_size/1024:.2f} KB)")
print(f"   Response size: {graphql_response_size:,} bytes ({graphql_response_size/1024:.2f} KB)")

if graphql_response.status_code == 200:
    data = graphql_response.json()
    graphql_stations = data['data']['locationBySearchTerm']['stations']['results']
    print(f"   Stations extracted: {len(graphql_stations)}")

total_sent += graphql_request_size
total_received += graphql_response_size

# Summary
print("\n" + "="*70)
print("BANDWIDTH SUMMARY FOR ONE ZIP CODE (77494)")
print("="*70)
print(f"\nTotal Data SENT:     {total_sent:,} bytes ({total_sent/1024:.2f} KB)")
print(f"Total Data RECEIVED: {total_received:,} bytes ({total_received/1024:.2f} KB)")
print(f"\nTOTAL BANDWIDTH:     {(total_sent + total_received):,} bytes ({(total_sent + total_received)/1024:.2f} KB)")

# Extrapolate to full scrape
print("\n" + "="*70)
print("BANDWIDTH PROJECTION FOR FULL SCRAPE")
print("="*70)

# US has ~41,000 ZIP codes, but not all have gas stations
# Let's estimate 30,000 ZIPs with gas stations
estimated_zips = 30000

total_bandwidth_bytes = (total_sent + total_received) * estimated_zips
total_bandwidth_gb = total_bandwidth_bytes / (1024**3)

print(f"\nEstimated ZIPs with gas stations: {estimated_zips:,}")
print(f"Bandwidth per ZIP: {(total_sent + total_received)/1024:.2f} KB")
print(f"\nPer scrape (once): {total_bandwidth_gb:.2f} GB")
print(f"Per day (2x): {total_bandwidth_gb * 2:.2f} GB")
print(f"Per month (60x): {total_bandwidth_gb * 60:.2f} GB")

print("\n" + "="*70)
print("PROXY COST ESTIMATES")
print("="*70)

# Typical residential proxy pricing
# - Low-end: $3-5/GB
# - Mid-range: $10-15/GB  
# - High-end: $20-30/GB

costs_per_gb = {
    "Budget residential": 3,
    "Standard residential": 10,
    "Premium residential": 15,
    "Elite residential": 25
}

for proxy_type, cost_per_gb in costs_per_gb.items():
    daily_cost = total_bandwidth_gb * 2 * cost_per_gb
    monthly_cost = total_bandwidth_gb * 60 * cost_per_gb
    print(f"\n{proxy_type} (${cost_per_gb}/GB):")
    print(f"  Per scrape: ${total_bandwidth_gb * cost_per_gb:.2f}")
    print(f"  Per day (2x): ${daily_cost:.2f}")
    print(f"  Per month: ${monthly_cost:.2f}")

print("\n" + "="*70)
print("NOTES:")
print("="*70)
print("• This measurement is for ONE ZIP that needs pagination (34 stations)")
print("• ZIPs with <20 stations only need the initial page load (no GraphQL)")
print("• ~70% of ZIPs likely have <20 stations = less bandwidth")
print("• Compression could reduce bandwidth by 60-80%")
print("• Some proxy providers offer unlimited plans for rotating proxies")
print("="*70)

