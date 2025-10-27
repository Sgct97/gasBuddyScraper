#!/usr/bin/env python3
"""
Browser-based reconnaissance using Playwright
Captures actual API calls, headers, and network traffic
"""

import json
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
from typing import List, Dict, Any


class BrowserRecon:
    """Browser-based reconnaissance to capture real network traffic"""
    
    def __init__(self):
        self.api_calls = []
        self.resources = []
        self.cookies = []
        self.local_storage = {}
        
    async def capture_network_traffic(self, url: str, zip_code: str = "90210"):
        """Capture all network requests made by the page"""
        print(f"\n=== CAPTURING NETWORK TRAFFIC FOR {url} ===")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)  # Non-headless to see what happens
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            # Network request listener
            async def handle_request(request):
                if any(keyword in request.url.lower() for keyword in 
                       ['api', 'graphql', 'station', 'price', 'search', 'json']):
                    print(f"  → {request.method} {request.url}")
                    self.api_calls.append({
                        'timestamp': datetime.now().isoformat(),
                        'method': request.method,
                        'url': request.url,
                        'headers': dict(request.headers),
                        'post_data': request.post_data
                    })
            
            # Response listener
            async def handle_response(response):
                if any(keyword in response.url.lower() for keyword in 
                       ['api', 'graphql', 'station', 'price', 'search']):
                    try:
                        content_type = response.headers.get('content-type', '')
                        if 'json' in content_type:
                            body = await response.text()
                            print(f"  ← {response.status} {response.url[:100]}")
                            print(f"     Content-Type: {content_type}")
                            print(f"     Size: {len(body)} bytes")
                            
                            # Try to parse JSON
                            try:
                                data = json.loads(body)
                                print(f"     JSON Keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")
                                
                                # Store the response
                                self.api_calls[-1]['response'] = {
                                    'status': response.status,
                                    'headers': dict(response.headers),
                                    'body': data,
                                    'size': len(body)
                                }
                            except json.JSONDecodeError:
                                print(f"     (Not valid JSON)")
                    except Exception as e:
                        print(f"     Error capturing response: {e}")
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            # Navigate to homepage
            print("\n1. Loading homepage...")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Capture cookies
            self.cookies = await context.cookies()
            print(f"\n✓ Captured {len(self.cookies)} cookies")
            
            # Capture localStorage
            self.local_storage = await page.evaluate("() => Object.assign({}, window.localStorage)")
            print(f"✓ Captured {len(self.local_storage)} localStorage items")
            
            # Try searching for a location
            print(f"\n2. Searching for ZIP: {zip_code}...")
            try:
                # Look for search input
                search_selectors = [
                    'input[type="search"]',
                    'input[placeholder*="location"]',
                    'input[placeholder*="zip"]',
                    'input[name="search"]',
                    '#search',
                    '.search-input'
                ]
                
                search_input = None
                for selector in search_selectors:
                    try:
                        search_input = await page.wait_for_selector(selector, timeout=2000)
                        if search_input:
                            print(f"✓ Found search input: {selector}")
                            break
                    except:
                        continue
                
                if search_input:
                    await search_input.fill(zip_code)
                    await asyncio.sleep(1)
                    await search_input.press('Enter')
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    await asyncio.sleep(3)
                    print("✓ Search completed")
                else:
                    print("⚠ Could not find search input - trying direct URL")
                    # Try direct navigation
                    await page.goto(f"{url}/home?search={zip_code}", wait_until='networkidle')
                    await asyncio.sleep(3)
                    
            except Exception as e:
                print(f"⚠ Search error: {e}")
            
            # Take screenshot
            await page.screenshot(path='gasbuddy_screenshot.png')
            print("\n✓ Screenshot saved: gasbuddy_screenshot.png")
            
            # Extract page structure
            print("\n3. Analyzing page structure...")
            page_data = await page.evaluate("""() => {
                return {
                    title: document.title,
                    has_react: !!window.React || !!document.querySelector('[data-reactroot]'),
                    has_next: !!window.__NEXT_DATA__,
                    next_data_keys: window.__NEXT_DATA__ ? Object.keys(window.__NEXT_DATA__) : [],
                    meta_tags: Array.from(document.querySelectorAll('meta')).map(m => ({
                        name: m.getAttribute('name'),
                        property: m.getAttribute('property'),
                        content: m.getAttribute('content')
                    })),
                    scripts_count: document.scripts.length,
                    has_station_data: document.body.innerHTML.includes('station') || 
                                      document.body.innerHTML.includes('price')
                }
            }""")
            
            print(f"  Title: {page_data['title']}")
            print(f"  React: {page_data['has_react']}")
            print(f"  Next.js: {page_data['has_next']}")
            if page_data['next_data_keys']:
                print(f"  Next.js Data Keys: {page_data['next_data_keys']}")
            
            # If Next.js, capture the data
            if page_data['has_next']:
                next_data = await page.evaluate("() => window.__NEXT_DATA__")
                with open('next_data.json', 'w') as f:
                    json.dump(next_data, f, indent=2)
                print("  ✓ Next.js data saved to next_data.json")
            
            await browser.close()
    
    def analyze_findings(self):
        """Analyze captured data and provide recommendations"""
        print("\n" + "=" * 60)
        print("ANALYSIS & RECOMMENDATIONS")
        print("=" * 60)
        
        # Analyze API calls
        print(f"\n📡 Total API calls captured: {len(self.api_calls)}")
        
        if self.api_calls:
            print("\nAPI Endpoints discovered:")
            unique_urls = set()
            for call in self.api_calls:
                url_base = call['url'].split('?')[0]
                if url_base not in unique_urls:
                    unique_urls.add(url_base)
                    print(f"  • {call['method']} {url_base}")
            
            # Check for GraphQL
            graphql_calls = [c for c in self.api_calls if 'graphql' in c['url'].lower()]
            if graphql_calls:
                print(f"\n🎯 GraphQL detected! ({len(graphql_calls)} calls)")
                print("   This is good - GraphQL APIs are structured and predictable")
                
                # Extract GraphQL operations
                for call in graphql_calls[:3]:  # Show first 3
                    if call.get('post_data'):
                        try:
                            data = json.loads(call['post_data'])
                            if 'query' in data:
                                # Extract operation name
                                query = data['query']
                                if 'query' in query or 'mutation' in query:
                                    print(f"   Operation: {query.split('{')[0].strip()}")
                        except:
                            pass
            
            # Check for REST APIs
            rest_patterns = ['/api/', '/v1/', '/v2/', '/v3/']
            rest_calls = [c for c in self.api_calls 
                         if any(p in c['url'] for p in rest_patterns)]
            if rest_calls:
                print(f"\n🔗 REST API detected! ({len(rest_calls)} calls)")
        
        else:
            print("\n⚠ No API calls captured - data might be:")
            print("  1. Server-side rendered (SSR)")
            print("  2. Hidden behind initial page load")
            print("  3. Protected/obfuscated")
        
        # Analyze cookies
        print(f"\n🍪 Cookies: {len(self.cookies)}")
        auth_cookies = [c for c in self.cookies 
                       if any(k in c['name'].lower() for k in ['auth', 'token', 'session'])]
        if auth_cookies:
            print(f"   Authentication cookies found: {[c['name'] for c in auth_cookies]}")
            print("   ⚠ May require authentication for full access")
        
        # Save all findings
        report = {
            'timestamp': datetime.now().isoformat(),
            'api_calls': self.api_calls,
            'cookies': self.cookies,
            'local_storage': self.local_storage,
            'summary': {
                'total_api_calls': len(self.api_calls),
                'has_graphql': any('graphql' in c['url'].lower() for c in self.api_calls),
                'has_rest_api': any('/api/' in c['url'] for c in self.api_calls),
                'auth_required': len(auth_cookies) > 0
            }
        }
        
        with open('browser_recon_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n✓ Full report saved to browser_recon_report.json")
        
        return report
    
    async def run(self):
        """Run complete browser reconnaissance"""
        await self.capture_network_traffic("https://www.gasbuddy.com", "90210")
        return self.analyze_findings()


async def main():
    recon = BrowserRecon()
    await recon.run()


if __name__ == "__main__":
    print("=" * 60)
    print("BROWSER-BASED RECONNAISSANCE")
    print("=" * 60)
    asyncio.run(main())

