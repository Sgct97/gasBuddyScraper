#!/usr/bin/env python3
"""Extract Apollo State from HTML"""

import json
import re

with open('page_source.html', 'r') as f:
    html = f.read()

# Find the Apollo State
match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.*?});?\s*</script>', html, re.DOTALL)

if match:
    json_str = match.group(1)
    data = json.loads(json_str)
    
    with open('apollo_state_clean.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Extracted Apollo State")
    print(f"✓ Total keys: {len(data.keys())}")
    print(f"✓ Root keys: {list(data.keys())[:20]}")
    
    # Look for station data
    station_keys = [k for k in data.keys() if 'station' in k.lower()]
    print(f"\n✓ Station-related keys: {len(station_keys)}")
    for key in station_keys[:10]:
        print(f"  - {key}")
else:
    print("✗ Could not find Apollo State")

