#!/usr/bin/env python3
"""
Test what's actually needed for GraphQL API to work
"""
import requests
import json

GRAPHQL_QUERY = open('full_graphql_query.txt').read()

def test_graphql(test_name, headers, use_session=False):
    """Test a GraphQL request with specific headers"""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    
    url = "https://www.gasbuddy.com/graphql"
    payload = {
        "operationName": "LocationBySearchTerm",
        "variables": {
            "fuel": 1,
            "lang": "en",
            "search": "77494",
            "cursor": "20"
        },
        "query": GRAPHQL_QUERY
    }
    
    if use_session:
        # Load HTML page first to establish session
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        print("Loading HTML page first...")
        html_response = session.get("https://www.gasbuddy.com/home?search=77494", timeout=10)
        print(f"  HTML response: {html_response.status_code}")
        print(f"  Cookies: {dict(session.cookies)}")
        
        # Now try GraphQL with session
        response = session.post(url, json=payload, headers=headers, timeout=10)
    else:
        # Direct GraphQL without session
        response = requests.post(url, json=payload, headers=headers, timeout=10)
    
    print(f"\nGraphQL Status: {response.status_code}")
    print(f"Headers sent: {headers}")
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data:
            stations = data['data']['locationBySearchTerm']['stations']['results']
            print(f"✅ SUCCESS: Got {len(stations)} stations")
            return True
        else:
            print(f"❌ Got 200 but no data: {data}")
            return False
    else:
        print(f"❌ FAILED: {response.text[:200]}")
        return False


# Test 1: Bare minimum (what I tried before)
test_graphql(
    "Test 1: Basic headers (NO session, NO csrf)",
    {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    },
    use_session=False
)

# Test 2: With apollo-require-preflight
test_graphql(
    "Test 2: With apollo-require-preflight (NO session, NO csrf)",
    {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "apollo-require-preflight": "true"
    },
    use_session=False
)

# Test 3: After loading HTML (session established)
test_graphql(
    "Test 3: After HTML load (session, NO special headers)",
    {
        "Content-Type": "application/json",
    },
    use_session=True
)

# Test 4: After HTML + apollo header
test_graphql(
    "Test 4: After HTML load + apollo-require-preflight",
    {
        "Content-Type": "application/json",
        "apollo-require-preflight": "true"
    },
    use_session=True
)

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("Check which test passed to see what's actually required")

