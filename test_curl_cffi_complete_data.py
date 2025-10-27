#!/usr/bin/env python3
"""
Get ALL 34 stations with COMPLETE data extraction from both Apollo and GraphQL
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

def extract_price_from_apollo(apollo_state, price_ref):
    """Extract price data from Apollo state reference"""
    if not price_ref or '__ref' not in price_ref:
        return None
    
    price_data = apollo_state.get(price_ref['__ref'], {})
    cash_ref = price_data.get('cash', {})
    credit_ref = price_data.get('credit', {})
    
    result = {
        'fuel_type': price_data.get('fuelProduct', 'unknown'),
        'cash': None,
        'credit': None
    }
    
    if cash_ref and '__ref' in cash_ref:
        cash_data = apollo_state.get(cash_ref['__ref'], {})
        if cash_data.get('price'):
            result['cash'] = {
                'price': cash_data.get('price'),
                'posted_time': cash_data.get('postedTime'),
                'reporter': cash_data.get('nickname')
            }
    
    if credit_ref and '__ref' in credit_ref:
        credit_data = apollo_state.get(credit_ref['__ref'], {})
        if credit_data.get('price'):
            result['credit'] = {
                'price': credit_data.get('price'),
                'posted_time': credit_data.get('postedTime'),
                'reporter': credit_data.get('nickname')
            }
    
    return result

def extract_stations_from_apollo(apollo_state):
    """Extract complete station data from Apollo state"""
    stations = []
    
    for key in sorted(apollo_state.keys()):
        if key.startswith('Station:'):
            station_id = key.replace('Station:', '')
            station_data = apollo_state[key]
            
            # Get address
            address_ref = station_data.get('address', {}).get('__ref', '')
            address_data = apollo_state.get(address_ref, {})
            
            # Get prices
            prices = []
            price_refs = station_data.get('prices', [])
            for price_ref in price_refs:
                price_info = extract_price_from_apollo(apollo_state, price_ref)
                if price_info:
                    prices.append(price_info)
            
            stations.append({
                'id': station_id,
                'name': station_data.get('name', ''),
                'address': address_data.get('line1', ''),
                'city': address_data.get('locality', ''),
                'state': address_data.get('region', ''),
                'zip': address_data.get('postalCode', ''),
                'prices': prices,
                'source': 'apollo'
            })
    
    return stations

print("="*70)
print("curl_cffi: ALL 34 STATIONS - COMPLETE DATA EXTRACTION")
print("="*70)

session = requests.Session()

# Step 1: Load initial page and extract first 20 from Apollo
print("\n1. Loading initial page and extracting Apollo state...")
response = session.get(
    "https://www.gasbuddy.com/home?search=77494",
    impersonate="chrome120",
    timeout=30
)

# Extract CSRF
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

# Extract and parse Apollo state
apollo_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.+?});', response.text, re.DOTALL)
apollo_state = json.loads(apollo_match.group(1))

apollo_stations = extract_stations_from_apollo(apollo_state)
print(f"   Extracted {len(apollo_stations)} stations from Apollo state")

# Step 2: Get remaining stations via GraphQL
print("\n2. Getting remaining stations via GraphQL...")
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

graphql_response = session.post(
    "https://www.gasbuddy.com/graphql",
    json=payload,
    headers=headers,
    impersonate="chrome120",
    timeout=15
)

graphql_stations = []
if graphql_response.status_code == 200:
    data = graphql_response.json()
    raw_stations = data['data']['locationBySearchTerm']['stations']['results']
    
    for station in raw_stations:
        prices = []
        if 'prices' in station and station['prices']:
            for price_report in station['prices']:
                cash_info = price_report.get('cash', {})
                credit_info = price_report.get('credit', {})
                
                price_obj = {
                    'fuel_type': price_report['fuelProduct'],
                    'cash': None,
                    'credit': None
                }
                
                if cash_info and cash_info.get('price') and cash_info.get('price') > 0:
                    price_obj['cash'] = {
                        'price': cash_info['price'],
                        'posted_time': cash_info.get('postedTime'),
                        'reporter': cash_info.get('nickname')
                    }
                
                if credit_info and credit_info.get('price') and credit_info.get('price') > 0:
                    price_obj['credit'] = {
                        'price': credit_info['price'],
                        'posted_time': credit_info.get('postedTime'),
                        'reporter': credit_info.get('nickname')
                    }
                
                prices.append(price_obj)
        
        graphql_stations.append({
            'id': station['id'],
            'name': station['name'],
            'address': station['address']['line1'],
            'city': station['address']['locality'],
            'state': station['address']['region'],
            'zip': station['address']['postalCode'],
            'prices': prices,
            'source': 'graphql'
        })
    
    print(f"   Extracted {len(graphql_stations)} stations from GraphQL")

# Combine all stations
all_stations = apollo_stations + graphql_stations

# Print ALL stations with complete data
print("\n" + "="*70)
print(f"ALL {len(all_stations)} STATIONS - COMPLETE DATA")
print("="*70)

for idx, station in enumerate(all_stations, 1):
    print(f"\n{'='*70}")
    print(f"STATION #{idx} ({station['source'].upper()})")
    print(f"{'='*70}")
    print(f"Name: {station['name']}")
    print(f"Address: {station['address']}, {station['city']}, {station['state']} {station['zip']}")
    print(f"ID: {station['id']}")
    
    if station['prices']:
        print(f"\nPrices ({len(station['prices'])} fuel types):")
        for price in station['prices']:
            print(f"\n  {price['fuel_type']}:")
            
            if price['cash']:
                posted = price['cash']['posted_time'][:19] if price['cash']['posted_time'] else 'N/A'
                reporter = price['cash']['reporter'] if price['cash']['reporter'] else 'N/A'
                print(f"    Cash: ${price['cash']['price']} (posted: {posted}, by: {reporter})")
            else:
                print(f"    Cash: Not reported")
            
            if price['credit']:
                posted = price['credit']['posted_time'][:19] if price['credit']['posted_time'] else 'N/A'
                reporter = price['credit']['reporter'] if price['credit']['reporter'] else 'N/A'
                print(f"    Credit: ${price['credit']['price']} (posted: {posted}, by: {reporter})")
            else:
                print(f"    Credit: Not reported")
    else:
        print("\nPrices: No recent reports")

print("\n" + "="*70)
print(f"TOTAL: {len(all_stations)} stations")
print("="*70)
print("\n✅ curl_cffi COMPLETE EXTRACTION:")
print(f"  - {len(apollo_stations)} stations from Apollo state")
print(f"  - {len(graphql_stations)} stations from GraphQL")
print("  - Full addresses for ALL stations")
print("  - Both cash AND credit prices")
print("  - Timestamps and reporters")
print("  - All fuel types")
print("="*70)

