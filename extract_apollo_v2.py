#!/usr/bin/env python3
import json
import re

with open('page_source.html', 'r') as f:
    html = f.read()

# Find the start
start = html.find('window.__APOLLO_STATE__')
if start == -1:
    print("Not found!")
    exit(1)

# Find the = sign
eq_pos = html.find('=', start)
json_start = eq_pos + 1

# Find the matching closing brace
brace_count = 0
in_string = False
escape = False
json_end = None

for i in range(json_start, len(html)):
    char = html[i]
    
    if escape:
        escape = False
        continue
        
    if char == '\\':
        escape = True
        continue
    
    if char == '"' and not escape:
        in_string = not in_string
        continue
    
    if not in_string:
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break

if json_end:
    json_str = html[json_start:json_end].strip()
    try:
        data = json.loads(json_str)
        
        with open('apollo_final.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Successfully extracted Apollo State!")
        print(f"✓ Size: {len(json_str)} bytes")
        print(f"✓ Total root keys: {len(data)}")
        
        # Analyze structure
        print(f"\n✓ Sample keys:")
        for key in list(data.keys())[:10]:
            print(f"  - {key}")
        
        # Look for station data
        station_keys = [k for k in data.keys() if 'Station' in k]
        print(f"\n✓ Station keys found: {len(station_keys)}")
        if station_keys:
            print(f"  First station key: {station_keys[0]}")
            print(f"  Data: {json.dumps(data[station_keys[0]], indent=2)[:300]}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print(f"JSON excerpt: {json_str[:500]}")
else:
    print("Could not find end of JSON")

