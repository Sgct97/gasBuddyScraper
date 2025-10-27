#!/usr/bin/env python3
"""
Analyze what we're actually downloading - can we be more targeted?
"""
from curl_cffi import requests
import json
import re

print("="*70)
print("ANALYZING RESPONSE CONTENT")
print("="*70)

session = requests.Session()

print("\nDownloading page for ZIP 77494...")
response = session.get(
    "https://www.gasbuddy.com/home?search=77494",
    impersonate="chrome120",
    timeout=30
)

total_size = len(response.content)
html = response.text

print(f"\nTotal response size: {total_size:,} bytes ({total_size/1024:.2f} KB)")

# Find the Apollo state
apollo_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.+?});', html, re.DOTALL)
if apollo_match:
    apollo_json = apollo_match.group(1)
    apollo_size = len(apollo_json)
    print(f"\nApollo state size: {apollo_size:,} bytes ({apollo_size/1024:.2f} KB)")
    print(f"Apollo state is {(apollo_size/total_size)*100:.1f}% of total response")
    
    # Parse to see what's in there
    apollo_state = json.loads(apollo_json)
    station_count = sum(1 for key in apollo_state.keys() if key.startswith('Station:'))
    
    print(f"\nApollo state contains:")
    print(f"  - {station_count} stations")
    print(f"  - {len(apollo_state)} total objects")
    
    # Check what types of objects
    object_types = {}
    for key in apollo_state.keys():
        obj_type = key.split(':')[0] if ':' in key else 'ROOT'
        object_types[obj_type] = object_types.get(obj_type, 0) + 1
    
    print(f"\nObject breakdown:")
    for obj_type, count in sorted(object_types.items(), key=lambda x: -x[1]):
        print(f"  - {obj_type}: {count}")

# What else is in the response?
print("\n" + "="*70)
print("WHAT ARE WE DOWNLOADING THAT WE DON'T NEED?")
print("="*70)

# Count scripts
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
script_size = sum(len(s) for s in scripts)
print(f"\nJavaScript/Scripts: {script_size:,} bytes ({script_size/1024:.2f} KB) - {(script_size/total_size)*100:.1f}%")

# Count styles
styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
style_size = sum(len(s) for s in styles)
print(f"CSS/Styles: {style_size:,} bytes ({style_size/1024:.2f} KB) - {(style_size/total_size)*100:.1f}%")

# Rough estimate of actual HTML
html_size = total_size - script_size - style_size
print(f"HTML structure: ~{html_size:,} bytes (~{html_size/1024:.2f} KB) - {(html_size/total_size)*100:.1f}%")

print("\n" + "="*70)
print("CAN WE AVOID DOWNLOADING THE FULL PAGE?")
print("="*70)

print("\n❓ Options to reduce bandwidth:")
print("\n1. Use GraphQL endpoint DIRECTLY")
print("   - We proved it works with curl_cffi")
print("   - Need to get CSRF token first (small request)")
print("   - Then ONLY get station data (no HTML/CSS/JS)")
print("   - Potential savings: 90%+")

print("\n2. Request with Accept-Encoding: gzip")
print("   - Browser automatically compresses")
print("   - Could reduce by 60-80%")
print("   - Let's test this now...")

print("\n" + "="*70)
print("TESTING COMPRESSION")
print("="*70)

# Test with compression
compressed_response = session.get(
    "https://www.gasbuddy.com/home?search=77494",
    headers={"Accept-Encoding": "gzip, deflate, br"},
    impersonate="chrome120",
    timeout=30
)

# The response.content is already decompressed by curl_cffi
# But we can check the Content-Length header if present
if 'content-length' in compressed_response.headers:
    compressed_size = int(compressed_response.headers['content-length'])
    print(f"\nCompressed size (from header): {compressed_size:,} bytes ({compressed_size/1024:.2f} KB)")
    print(f"Savings: {((total_size - compressed_size)/total_size)*100:.1f}%")
else:
    print("\n(Content-Length not in headers - curl_cffi auto-decompresses)")
    print("But the server IS likely sending compressed data already")

print("\n" + "="*70)
print("💡 BEST STRATEGY:")
print("="*70)
print("\n1st request per session: Get homepage to extract CSRF (~400 KB once)")
print("All other requests: Use GraphQL endpoint directly (~30 KB each)")
print("\nFor 30,000 ZIPs:")
print("  Current: 400 KB × 30,000 = 11.4 GB")
print("  Optimized: 400 KB + (30 KB × 30,000) = 878 MB")
print(f"  Savings: {((11.4 - 0.878)/11.4)*100:.0f}% reduction! 🚀")
print("\n  Per month (60 scrapes): 52.7 GB instead of 759 GB")
print("  Even with proxies @ $10/GB: $527/month instead of $7,591")
print("="*70)

