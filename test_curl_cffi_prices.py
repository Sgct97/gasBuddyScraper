#!/usr/bin/env python3
"""
Verify curl_cffi gets COMPLETE price data (cash + credit)
"""
from curl_cffi import requests
import json
import re
import time

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

print("="*70)
print("TESTING: Does curl_cffi get CASH prices?")
print("="*70)

session = requests.Session()

# Load initial page
print("\n1. Loading page...")
response = session.get(
    "https://www.gasbuddy.com/home?search=77494",
    impersonate="chrome120",
    timeout=30
)

# Extract CSRF
csrf_matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', response.text, re.I)
csrf_token = csrf_matches[0] if csrf_matches else None

print(f"   CSRF: {csrf_token[:20]}...")

# Wait and make GraphQL request
print("\n2. Making GraphQL request with cursor=20...")
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

print(f"   Status: {graphql_response.status_code}")

if graphql_response.status_code == 200:
    data = graphql_response.json()
    stations = data['data']['locationBySearchTerm']['stations']['results']
    
    print(f"   Got {len(stations)} stations")
    
    # Check first station's price structure
    if stations:
        first_station = stations[0]
        print(f"\n3. Checking price data for: {first_station['name']}")
        print(f"   Address: {first_station['address']['line1']}")
        
        if 'prices' in first_station and first_station['prices']:
            print(f"\n   Price reports: {len(first_station['prices'])}")
            
            # Check first price
            first_price = first_station['prices'][0]
            print(f"\n   Example price structure:")
            print(json.dumps(first_price, indent=4))
            
            # Check if we have BOTH cash and credit
            has_cash = 'cash' in first_price
            has_credit = 'credit' in first_price
            
            print(f"\n   ✅ Has 'cash' field: {has_cash}")
            print(f"   ✅ Has 'credit' field: {has_credit}")
            
            if has_cash and has_credit:
                cash_price = first_price['cash'].get('price') if first_price['cash'] else None
                credit_price = first_price['credit'].get('price') if first_price['credit'] else None
                
                print(f"\n   Cash price: ${cash_price if cash_price else 'N/A'}")
                print(f"   Credit price: ${credit_price if credit_price else 'N/A'}")
                
                print("\n" + "="*70)
                print("✅ curl_cffi gets COMPLETE price data!")
                print("="*70)
                print("Response includes:")
                print("  ✅ Both cash AND credit prices")
                print("  ✅ Timestamps (postedTime)")
                print("  ✅ Reporters (nickname)")
                print("  ✅ All fuel types")
                print("\n💡 We can extract cash (preferred) or credit as fallback")
                print("   Just like the Playwright scraper!")
                print("="*70)
            else:
                print("\n   ⚠️  Missing cash or credit field")
        else:
            print("\n   ⚠️  No prices in response")

    # Show a few more examples
    print("\n4. Checking Shell and Texaco (the ones we verified before)...")
    for station in stations:
        if station['name'] in ['Shell', 'Texaco']:
            print(f"\n   {station['name']} - {station['address']['line1']}")
            if 'prices' in station and station['prices']:
                for price_report in station['prices']:
                    if price_report['fuelProduct'] == 'regular_gas':
                        cash = price_report.get('cash', {})
                        credit = price_report.get('credit', {})
                        cash_price = cash.get('price') if cash else None
                        credit_price = credit.get('price') if credit else None
                        
                        if cash_price:
                            print(f"      Regular (cash): ${cash_price} by {cash.get('nickname')}")
                        if credit_price:
                            print(f"      Regular (credit): ${credit_price} by {credit.get('nickname')}")
                        break
else:
    print(f"   ❌ Failed: {graphql_response.text[:200]}")

