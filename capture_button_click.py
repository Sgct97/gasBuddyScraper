#!/usr/bin/env python3
"""
Capture network requests when clicking "more" button
"""

import asyncio
from playwright.async_api import async_playwright
import json

async def capture_more_button():
    captured_requests = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Capture all network requests
        async def handle_request(request):
            if 'api' in request.url.lower() or 'graphql' in request.url.lower() or 'station' in request.url.lower():
                print(f"\n🔍 Request captured:")
                print(f"   URL: {request.url}")
                print(f"   Method: {request.method}")
                if request.post_data:
                    print(f"   POST data: {request.post_data[:200]}")
                
                captured_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'post_data': request.post_data
                })
        
        async def handle_response(response):
            if 'api' in response.url.lower() or 'graphql' in response.url.lower():
                print(f"\n📥 Response:")
                print(f"   URL: {response.url}")
                print(f"   Status: {response.status}")
                try:
                    body = await response.text()
                    print(f"   Size: {len(body)} bytes")
                    if 'json' in response.headers.get('content-type', ''):
                        data = json.loads(body)
                        print(f"   JSON keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")
                except:
                    pass
        
        page.on('request', handle_request)
        page.on('response', handle_response)
        
        print("Loading page...")
        await page.goto("https://www.gasbuddy.com/home?search=77494", wait_until='networkidle')
        
        print("\n✓ Page loaded. Looking for 'more' button...")
        await asyncio.sleep(2)
        
        # Try to find the "more" button
        possible_selectors = [
            'text=more 77494',
            'text=more',
            'button:has-text("more")',
            'a:has-text("more")',
            '[class*="more"]',
            '[class*="load"]',
            'text=Load More',
            'text=Show More',
        ]
        
        button = None
        for selector in possible_selectors:
            try:
                button = await page.wait_for_selector(selector, timeout=2000)
                if button:
                    print(f"✓ Found button with selector: {selector}")
                    break
            except:
                continue
        
        if not button:
            print("⚠ Could not find 'more' button automatically")
            print("Taking screenshot to see page...")
            await page.screenshot(path='page_with_more_button.png')
            print("✓ Screenshot saved: page_with_more_button.png")
            
            # Get page HTML for manual inspection
            content = await page.content()
            with open('page_content.html', 'w') as f:
                f.write(content)
            print("✓ HTML saved: page_content.html")
            
            # Search for "more" in the HTML
            if 'more' in content.lower():
                print("\n'more' text found in HTML - searching context:")
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'more' in line.lower() and '77494' in line:
                        print(f"Line {i}: {line.strip()[:150]}")
        else:
            print("\nClicking 'more' button...")
            await button.click()
            
            print("\nWaiting for new requests...")
            await asyncio.sleep(5)
            
            await page.screenshot(path='after_click.png')
            print("✓ Screenshot saved: after_click.png")
        
        await browser.close()
    
    # Save captured requests
    with open('captured_requests.json', 'w') as f:
        json.dump(captured_requests, f, indent=2)
    
    print(f"\n✓ Captured {len(captured_requests)} requests")
    print("✓ Saved to captured_requests.json")
    
    return captured_requests

if __name__ == "__main__":
    print("="*70)
    print("CAPTURING 'MORE' BUTTON NETWORK REQUESTS")
    print("="*70)
    asyncio.run(capture_more_button())

