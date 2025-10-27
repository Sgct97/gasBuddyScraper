#!/usr/bin/env python3
"""
Debug Apollo state structure to see why addresses aren't extracting
"""
from curl_cffi import requests
import json
import re

print("="*70)
print("DEBUGGING APOLLO STATE STRUCTURE")
print("="*70)

session = requests.Session()

print("\nLoading page...")
response = session.get(
    "https://www.gasbuddy.com/home?search=77494",
    impersonate="chrome120",
    timeout=30
)

# Extract Apollo state
apollo_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.+?});', response.text, re.DOTALL)
apollo_state = json.loads(apollo_match.group(1))

print("\n1. Looking at first Station object...")
# Find first station
first_station_key = None
for key in apollo_state.keys():
    if key.startswith('Station:'):
        first_station_key = key
        break

if first_station_key:
    station = apollo_state[first_station_key]
    print(f"\nStation Key: {first_station_key}")
    print(f"Station Data:")
    print(json.dumps(station, indent=2)[:1000])
    
    # Check address reference
    print("\n2. Looking at address reference...")
    if 'address' in station:
        print(f"Address field: {station['address']}")
        if isinstance(station['address'], dict) and '__ref' in station['address']:
            addr_ref = station['address']['__ref']
            print(f"\nAddress data at '{addr_ref}':")
            print(json.dumps(apollo_state.get(addr_ref, {}), indent=2))
    
    # Check prices
    print("\n3. Looking at prices...")
    if 'prices' in station:
        print(f"Prices field (first 3): {station['prices'][:3]}")
        if station['prices'] and isinstance(station['prices'][0], dict) and '__ref' in station['prices'][0]:
            price_ref = station['prices'][0]['__ref']
            print(f"\nFirst price data at '{price_ref}':")
            price_data = apollo_state.get(price_ref, {})
            print(json.dumps(price_data, indent=2))
            
            # Check cash/credit refs
            if 'cash' in price_data and isinstance(price_data['cash'], dict) and '__ref' in price_data['cash']:
                cash_ref = price_data['cash']['__ref']
                print(f"\nCash price data at '{cash_ref}':")
                print(json.dumps(apollo_state.get(cash_ref, {}), indent=2))

print("\n" + "="*70)

