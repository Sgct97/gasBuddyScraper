#!/usr/bin/env python3
"""
HTML/JS data extractor - finds embedded JSON data in page source
"""

import requests
import json
import re
from bs4 import BeautifulSoup


def extract_embedded_data(url):
    """Download page and extract all embedded JSON data"""
    print(f"\n=== ANALYZING: {url} ===\n")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    response = requests.get(url, headers=headers)
    html = response.text
    
    print(f"✓ Downloaded {len(html)} bytes")
    print(f"✓ Status: {response.status_code}\n")
    
    # Save raw HTML
    with open('page_source.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✓ Saved to: page_source.html\n")
    
    soup = BeautifulSoup(html, 'html.parser')
    
    findings = []
    
    # 1. Look for Next.js data
    print("🔍 Searching for Next.js __NEXT_DATA__...")
    next_data_scripts = soup.find_all('script', id='__NEXT_DATA__')
    for script in next_data_scripts:
        try:
            data = json.loads(script.string)
            print(f"✓ FOUND! Keys: {list(data.keys())}")
            findings.append({
                'type': 'next_data',
                'data': data
            })
            with open('next_data.json', 'w') as f:
                json.dump(data, f, indent=2)
            print("  Saved to: next_data.json\n")
        except:
            pass
    
    # 2. Look for window.__INITIAL_STATE__ or similar
    print("🔍 Searching for window.__INITIAL_STATE__ patterns...")
    window_patterns = [
        r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});',
        r'window\.__PRELOADED_STATE__\s*=\s*(\{.+?\});',
        r'window\.__DATA__\s*=\s*(\{.+?\});',
        r'window\.initialData\s*=\s*(\{.+?\});',
    ]
    
    for pattern in window_patterns:
        matches = re.findall(pattern, html, re.DOTALL)
        if matches:
            print(f"✓ FOUND pattern: {pattern[:50]}...")
            for i, match in enumerate(matches[:3]):  # First 3 only
                try:
                    data = json.loads(match)
                    findings.append({
                        'type': 'window_state',
                        'data': data
                    })
                    filename = f'window_state_{i}.json'
                    with open(filename, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"  Saved to: {filename}\n")
                except:
                    print(f"  Could not parse JSON\n")
    
    # 3. Look for JSON-LD structured data
    print("🔍 Searching for JSON-LD structured data...")
    jsonld_scripts = soup.find_all('script', type='application/ld+json')
    for i, script in enumerate(jsonld_scripts):
        try:
            data = json.loads(script.string)
            print(f"✓ FOUND! Type: {data.get('@type', 'unknown')}")
            findings.append({
                'type': 'jsonld',
                'data': data
            })
            filename = f'jsonld_{i}.json'
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"  Saved to: {filename}\n")
        except:
            pass
    
    # 4. Search for any large JSON objects in scripts
    print("🔍 Searching for large JSON objects in <script> tags...")
    all_scripts = soup.find_all('script')
    for i, script in enumerate(all_scripts):
        if script.string and len(script.string) > 1000:
            # Try to find JSON objects
            json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', script.string)
            for j, obj_str in enumerate(json_objects):
                if len(obj_str) > 500:  # Significant size
                    try:
                        data = json.loads(obj_str)
                        # Check if it contains station/price data
                        obj_keys = str(data.keys()) if isinstance(data, dict) else str(data)
                        if any(keyword in obj_keys.lower() for keyword in ['station', 'price', 'fuel', 'gas', 'results']):
                            print(f"✓ FOUND potential data in script #{i}")
                            print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")
                            findings.append({
                                'type': 'script_json',
                                'script_index': i,
                                'data': data
                            })
                            filename = f'script_data_{i}_{j}.json'
                            with open(filename, 'w') as f:
                                json.dump(data, f, indent=2)
                            print(f"  Saved to: {filename}\n")
                    except:
                        pass
    
    # 5. Look for data attributes
    print("🔍 Searching for data-* attributes...")
    data_attrs = soup.find_all(attrs=lambda x: x and any(attr.startswith('data-') for attr in x.keys()))
    for elem in data_attrs[:10]:  # First 10
        for attr, value in elem.attrs.items():
            if attr.startswith('data-') and len(str(value)) > 100:
                try:
                    data = json.loads(value)
                    print(f"✓ FOUND in {attr}")
                    findings.append({
                        'type': 'data_attribute',
                        'attribute': attr,
                        'data': data
                    })
                except:
                    pass
    
    # 6. Search for station/price mentions in HTML
    print("\n🔍 Searching for station/price keywords in HTML...")
    keywords = ['station', 'price', 'fuel', 'gasoline', 'diesel']
    for keyword in keywords:
        count = html.lower().count(keyword)
        print(f"  '{keyword}': {count} mentions")
    
    # 7. Look for specific GasBuddy patterns
    print("\n🔍 Searching for GasBuddy-specific patterns...")
    gb_patterns = [
        r'"stationId":\s*"?(\d+)"?',
        r'"stationID":\s*"?(\d+)"?',
        r'"Station_ID":\s*"?(\d+)"?',
        r'"price":\s*"?(\d+\.?\d*)"?',
    ]
    
    for pattern in gb_patterns:
        matches = re.findall(pattern, html)
        if matches:
            print(f"✓ Found pattern {pattern}: {len(matches)} matches")
            print(f"  Examples: {matches[:5]}")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: Found {len(findings)} data sources")
    print(f"{'='*60}\n")
    
    return findings, html


if __name__ == "__main__":
    # Test with 90210
    findings, html = extract_embedded_data("https://www.gasbuddy.com/home?search=90210")
    
    print(f"✓ Complete! Check the generated files for extracted data.")

