#!/usr/bin/env python3
"""
Test if GasBuddy paginates results for ZIPs with many stations
"""

import requests
import json
import time

def extract_apollo(html):
    start = html.find('window.__APOLLO_STATE__')
    if start == -1:
        return {}
    eq_pos = html.find('=', start)
    json_start = eq_pos + 1
    brace_count = 0
    in_string = False
    escape = False
    for i in range(json_start, len(html)):
        char = html[i]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    try:
                        return json.loads(html[json_start:i+1].strip())
                    except:
                        return {}
    return {}

headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Test a variety of ZIPs - some suburban (likely more stations)
test_zips = [
    "77494",  # Katy, TX (suburban Houston - lots of stations)
    "85260",  # Scottsdale, AZ
    "92101",  # San Diego downtown
    "30318",  # Atlanta
    "33773",  # Your test ZIP (control - we know this one)
]

print("="*60)
print("PAGINATION TEST")
print("="*60)

for zip_code in test_zips:
    print(f"\nTesting ZIP: {zip_code}")
    
    try:
        url = f"https://www.gasbuddy.com/home?search={zip_code}"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"  ✗ Status: {response.status_code}")
            time.sleep(2)
            continue
        
        data = extract_apollo(response.text)
        
        found = False
        for key in data.keys():
            if key.startswith('Location:'):
                loc = data[key]
                for k in loc.keys():
                    if 'stations' in k:
                        found = True
                        station_data = loc[k]
                        total = station_data.get('count', 0)
                        results = station_data.get('results', [])
                        returned = len(results)
                        cursor = station_data.get('cursor', {})
                        cursor_next = cursor.get('next', 'N/A')
                        
                        print(f"  Total stations: {total}")
                        print(f"  Returned: {returned}")
                        print(f"  Cursor.next: {cursor_next}")
                        
                        if total > returned:
                            print(f"  🚨 PAGINATION DETECTED! Missing {total - returned} stations")
                            print(f"     Need to implement cursor following!")
                        elif total == returned:
                            print(f"  ✅ All stations in one request")
                        else:
                            print(f"  ⚠️  Returned > Total? Weird...")
                        
                        break
        
        if not found:
            print(f"  ✗ No location data found")
        
        time.sleep(2)  # Be polite to avoid rate limits
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        time.sleep(3)

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
print("\nCONCLUSION:")
print("If we found pagination → Need to implement cursor following")
print("If no pagination → ZIP search alone is sufficient!")

