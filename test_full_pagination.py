#!/usr/bin/env python3
"""
Test complete pagination chain - follow cursor until we get all stations
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

headers = {"User-Agent": "Mozilla/5.0"}
zip_code = "77494"  # 34 stations total

print(f"Complete pagination test for ZIP {zip_code}")
print("="*70 + "\n")

all_station_ids = set()
cursor = None
page = 1
max_pages = 10  # Safety limit

while page <= max_pages:
    if cursor:
        url = f"https://www.gasbuddy.com/home?search={zip_code}&cursor={cursor}"
    else:
        url = f"https://www.gasbuddy.com/home?search={zip_code}"
    
    print(f"Page {page}:")
    print(f"  URL: {url}")
    
    r = requests.get(url, headers=headers, timeout=10)
    
    if r.status_code != 200:
        print(f"  ✗ Status {r.status_code}")
        break
    
    data = extract_apollo(r.text)
    
    # Extract stations and cursor
    found = False
    next_cursor = None
    page_stations = set()
    total_count = 0
    
    for key in data.keys():
        if key.startswith('Location:'):
            loc = data[key]
            for k in loc.keys():
                if 'stations' in k:
                    found = True
                    stations_data = loc[k]
                    total_count = stations_data.get('count', 0)
                    results = stations_data.get('results', [])
                    cursor_info = stations_data.get('cursor', {})
                    next_cursor = cursor_info.get('next')
                    
                    for ref in results:
                        if '__ref' in ref:
                            sid = ref['__ref'].split(':')[1]
                            page_stations.add(sid)
                            all_station_ids.add(sid)
    
    new_stations = len(page_stations - all_station_ids) + len(page_stations)
    
    print(f"  Total expected: {total_count}")
    print(f"  This page: {len(page_stations)} stations")
    print(f"  New stations: {new_stations - len(all_station_ids) + len(page_stations)}")
    print(f"  Cumulative total: {len(all_station_ids)}")
    print(f"  Next cursor: {next_cursor}")
    
    # Check if we're done
    if not next_cursor or len(all_station_ids) >= total_count:
        print(f"  ✅ Complete!")
        break
    
    # Continue to next page
    cursor = next_cursor
    page += 1
    print()
    time.sleep(2)  # Be polite

print("\n" + "="*70)
print("FINAL RESULTS:")
print(f"  Expected: {total_count} stations")
print(f"  Retrieved: {len(all_station_ids)} stations")
print(f"  Pages needed: {page}")

if len(all_station_ids) == total_count:
    print("  ✅ SUCCESS - Got all stations!")
else:
    print(f"  ❌ MISSING {total_count - len(all_station_ids)} stations")
    print("\nDebugging info:")
    print(f"  Last cursor value: {cursor}")
    print(f"  All station IDs: {sorted(all_station_ids, key=int)}")

