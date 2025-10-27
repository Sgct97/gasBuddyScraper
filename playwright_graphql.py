#!/usr/bin/env python3
"""
Use Playwright to make GraphQL request after page load
"""
from playwright.sync_api import sync_playwright
import json

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

with sync_playwright() as p:
    print("Launching browser...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    
    # Step 1: Load page
    print("\n1. Loading HTML page...")
    page.goto("https://www.gasbuddy.com/home?search=77494", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)  # Wait a bit for any JS to run
    print("   ✅ Page loaded")
    
    # Step 2: Make GraphQL request using page.evaluate
    print("\n2. Making GraphQL request from browser context...")
    
    result = page.evaluate(f"""
        async () => {{
            const response = await fetch('https://www.gasbuddy.com/graphql', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify({{
                    operationName: 'LocationBySearchTerm',
                    variables: {{
                        fuel: 1,
                        lang: 'en',
                        search: '77494',
                        cursor: '20'
                    }},
                    query: {json.dumps(GRAPHQL_QUERY)}
                }})
            }});
            
            return {{
                status: response.status,
                statusText: response.statusText,
                data: response.ok ? await response.json() : await response.text()
            }};
        }}
    """)
    
    print(f"   Status: {result['status']} {result['statusText']}")
    
    if result['status'] == 200:
        data = result['data']
        if 'data' in data:
            stations = data['data']['locationBySearchTerm']['stations']['results']
            print(f"   ✅✅✅ SUCCESS! Got {len(stations)} stations")
            print(f"   First station: {stations[0]['name']}")
            print(f"   Cursor: {data['data']['locationBySearchTerm']['stations']['cursor']}")
        else:
            print(f"   Response: {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"   ❌ Failed: {result['data'][:300]}")
    
    browser.close()

