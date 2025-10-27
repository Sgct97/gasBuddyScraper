#!/usr/bin/env python3
"""
Open GasBuddy page and let user manually click the "more" button
Captures all network requests to see what actually happens
"""
from playwright.sync_api import sync_playwright
import json
from datetime import datetime

captured_requests = []

def handle_request(request):
    """Capture all outgoing requests"""
    captured_requests.append({
        'url': request.url,
        'method': request.method,
        'headers': dict(request.headers),
        'post_data': request.post_data if request.method == 'POST' else None,
        'timestamp': datetime.now().isoformat()
    })

def handle_response(response):
    """Capture responses"""
    for req in captured_requests:
        if req['url'] == response.url and 'status' not in req:
            req['status'] = response.status
            req['status_text'] = response.status_text
            # Try to get response body for GraphQL calls
            if 'graphql' in response.url:
                try:
                    req['response_body'] = response.json()
                except:
                    req['response_body'] = response.text()[:500]
            break

print("="*70)
print("MANUAL BUTTON CLICK CAPTURE")
print("="*70)
print("\nThis will:")
print("1. Open GasBuddy search for ZIP 77494")
print("2. Keep the browser open for you to manually click")
print("3. Capture all network requests")
print("4. Save everything to a JSON file")
print("\nYou'll have 60 seconds to click the 'more' button")
print("="*70)
print("\n🚀 Starting browser...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headless=False so you can see it!
    context = browser.new_context()
    page = context.new_page()
    
    # Set up request/response listeners
    page.on("request", handle_request)
    page.on("response", handle_response)
    
    print("\n📖 Loading page...")
    page.goto("https://www.gasbuddy.com/home?search=77494", wait_until="domcontentloaded", timeout=60000)
    print("✅ Page loaded!")
    
    print("\n" + "="*70)
    print("🖱️  NOW CLICK THE 'more 77494 Gas Stations' BUTTON IN THE BROWSER")
    print("="*70)
    print("Waiting for 60 seconds...")
    print("Close the browser window when done (or wait for timeout)")
    
    try:
        page.wait_for_timeout(60000)  # Wait 60 seconds
    except:
        pass
    
    print("\n✅ Done! Saving captured requests...")
    
    browser.close()

# Save all captured requests
filename = f"manual_click_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, 'w') as f:
    json.dump(captured_requests, f, indent=2)

print(f"\n✅ Saved {len(captured_requests)} requests to: {filename}")

# Show GraphQL requests
graphql_requests = [r for r in captured_requests if 'graphql' in r['url']]
print(f"\n📊 GraphQL requests captured: {len(graphql_requests)}")

for i, req in enumerate(graphql_requests, 1):
    print(f"\n  Request {i}:")
    print(f"    Status: {req.get('status', 'N/A')}")
    print(f"    Method: {req['method']}")
    if req['post_data']:
        try:
            data = json.loads(req['post_data'])
            print(f"    Operation: {data.get('operationName')}")
            print(f"    Variables: {data.get('variables')}")
        except:
            print(f"    POST data: {req['post_data'][:100]}")
    
    if 'response_body' in req and isinstance(req['response_body'], dict):
        if 'data' in req['response_body']:
            try:
                stations = req['response_body']['data']['locationBySearchTerm']['stations']['results']
                total = req['response_body']['data']['locationBySearchTerm']['stations']['count']
                cursor = req['response_body']['data']['locationBySearchTerm']['stations']['cursor']
                print(f"    ✅ Got {len(stations)} stations (total: {total})")
                print(f"    Next cursor: {cursor.get('next') if cursor else None}")
            except:
                print(f"    Response: {str(req['response_body'])[:100]}")

print("\n" + "="*70)
print(f"Full details saved in: {filename}")
print("="*70)

