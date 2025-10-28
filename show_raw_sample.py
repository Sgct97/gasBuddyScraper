#!/usr/bin/env python3
"""
Quick script to show raw data structure from the last test
"""
import json
import random
from curl_cffi import requests

# Oxylabs ISP proxy configuration
PROXY_URLS = [
    "http://gasBuddyScraper_5gUpP:gasBuddyScraper_123@isp.oxylabs.io:8001",
]

print("Fetching one ZIP to show raw data structure...\n")

# Get session
session = requests.Session()
response = session.get(
    "https://www.gasbuddy.com/home?search=77494&fuel=1",
    impersonate="chrome110",
    proxies={"http": PROXY_URLS[0], "https": PROXY_URLS[0]},
    timeout=30
)

# Extract CSRF
import re
csrf_match = re.search(r'window\.CSRF_TOKEN\s*=\s*["\']([^"\']+)["\']', response.text)
csrf_token = csrf_match.group(1)

# GraphQL query for ZIP 77494
graphql_query = """
query LocationBySearchTerm($search: String) {
  locationBySearchTerm(search: $search) {
    stations {
      results {
        id
        name
        fuels
        address {
          line1
          line2
          locality
          region
          postalCode
        }
        prices {
          fuelProduct
          price
          cash {
            price
            postedTime
            nickname
          }
          credit {
            price
            postedTime
            nickname
          }
        }
        amenities {
          amenityId
          name
        }
        badges {
          badgeId
          callToAction
          campaignId
        }
        enterprise
        offers {
          discountValue
        }
        priceUnit
        ratingsCount
        starRating
        trends {
          areaLow
        }
      }
    }
  }
}
"""

response = session.post(
    "https://www.gasbuddy.com/graphql",
    json={
        "operationName": "LocationBySearchTerm",
        "variables": {"search": "77494", "fuel": 1, "maxAge": 0, "cursor": "0"},
        "query": graphql_query
    },
    headers={
        "content-type": "application/json",
        "gbcsrf": csrf_token,
        "origin": "https://www.gasbuddy.com",
        "referer": "https://www.gasbuddy.com/home?search=77494&fuel=1",
    },
    impersonate="chrome110",
    proxies={"http": PROXY_URLS[0], "https": PROXY_URLS[0]},
    timeout=30
)

data = response.json()
stations = data['data']['locationBySearchTerm']['stations']['results']

# Pick a random station
sample = random.choice(stations)

print("="*70)
print("RAW STATION DATA (exactly as received from GraphQL)")
print("="*70)
print(json.dumps(sample, indent=2))
print("="*70)
print(f"\nThis is 1 of {len(stations)} stations in this response")
print("Each station includes:")
print("  • Full address object")
print("  • Prices array with cash/credit breakdown")
print("  • Amenities, badges, ratings, trends")
print("  • All metadata needed for your app")

