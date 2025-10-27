#!/usr/bin/env python3
"""
Debug pagination to understand how cursor works
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

# Test with ZIP that needs pagination
zip_code = "77494"  # 34 stations

print(f"Testing pagination for ZIP {zip_code}")
print("="*70)

# Page 1
print("\n=== PAGE 1 ===")
url1 = f"https://www.gasbuddy.com/home?search={zip_code}"
r1 = requests.get(url1, headers=headers)
data1 = extract_apollo(r1.text)

station_ids_page1 = set()
cursor_page1 = None

for key in data1.keys():
    if key.startswith('Location:'):
        print(f"Location key: {key}")
        loc = data1[key]
        
        # Find all keys that contain 'stations'
        print("\nKeys in location:")
        for k in loc.keys():
            print(f"  {k}")
            
            if 'stations' in k:
                stations_data = loc[k]
                total = stations_data.get('count', 0)
                results = stations_data.get('results', [])
                cursor_info = stations_data.get('cursor', {})
                
                print(f"\n  Total stations: {total}")
                print(f"  Results returned: {len(results)}")
                print(f"  Cursor object: {cursor_info}")
                
                for ref in results:
                    if '__ref' in ref:
                        sid = ref['__ref'].split(':')[1]
                        station_ids_page1.add(sid)
                
                cursor_page1 = cursor_info.get('next')
                print(f"  Station IDs: {list(station_ids_page1)[:5]}...")

print(f"\nPage 1 Summary:")
print(f"  Unique stations: {len(station_ids_page1)}")
print(f"  Next cursor: {cursor_page1}")

# Try page 2 with cursor
if cursor_page1:
    print("\n" + "="*70)
    print("=== PAGE 2 - Testing cursor parameter ===")
    time.sleep(2)
    
    # Try different cursor formats
    test_urls = [
        f"https://www.gasbuddy.com/home?search={zip_code}&cursor={cursor_page1}",
        f"https://www.gasbuddy.com/home?search={zip_code}&offset={cursor_page1}",
    ]
    
    for test_url in test_urls:
        print(f"\nTrying: {test_url}")
        r2 = requests.get(test_url, headers=headers, timeout=10)
        print(f"  Status: {r2.status_code}")
        
        if r2.status_code == 200:
            data2 = extract_apollo(r2.text)
            
            station_ids_page2 = set()
            for key in data2.keys():
                if key.startswith('Location:'):
                    loc = data2[key]
                    for k in loc.keys():
                        if 'stations' in k:
                            stations_data = loc[k]
                            results = stations_data.get('results', [])
                            
                            for ref in results:
                                if '__ref' in ref:
                                    sid = ref['__ref'].split(':')[1]
                                    station_ids_page2.add(sid)
            
            print(f"  Stations found: {len(station_ids_page2)}")
            print(f"  New stations: {len(station_ids_page2 - station_ids_page1)}")
            print(f"  Overlap: {len(station_ids_page2 & station_ids_page1)}")
            
            if len(station_ids_page2 - station_ids_page1) > 0:
                print(f"  ✅ This cursor format works!")
                print(f"  New IDs: {list(station_ids_page2 - station_ids_page1)[:5]}")
            else:
                print(f"  ❌ Got same stations - cursor not working")
        
        time.sleep(2)

print("\n" + "="*70)
print("ANALYSIS:")
print("Need to figure out correct pagination mechanism")

