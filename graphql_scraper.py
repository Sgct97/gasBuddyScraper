#!/usr/bin/env python3
"""
GasBuddy GraphQL Scraper
Uses the actual GraphQL API instead of HTML scraping
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional

# The complete GraphQL query from the captured request
GRAPHQL_QUERY = """
query LocationBySearchTerm($brandId: Int, $cursor: String, $fuel: Int, $lang: String, $lat: Float, $lng: Float, $maxAge: Int, $search: String) {
  locationBySearchTerm(
    lat: $lat
    lng: $lng
    search: $search
    priority: "locality"
  ) {
    countryCode
    displayName
    latitude
    longitude
    regionCode
    stations(
      brandId: $brandId
      cursor: $cursor
      fuel: $fuel
      lat: $lat
      lng: $lng
      maxAge: $maxAge
      priority: "locality"
    ) {
      count
      cursor {
        next
        __typename
      }
      results {
        address {
          country
          line1
          line2
          locality
          postalCode
          region
          __typename
        }
        brands {
          brandId
          brandingType
          imageUrl
          name
          __typename
        }
        id
        name
        prices {
          cash {
            nickname
            postedTime
            price
            __typename
          }
          credit {
            nickname
            postedTime
            price
            __typename
          }
          discount
          fuelProduct
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}
"""

class GasBuddyGraphQLScraper:
    def __init__(self):
        self.api_url = "https://www.gasbuddy.com/graphql"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Origin": "https://www.gasbuddy.com",
            "Referer": "https://www.gasbuddy.com/",
        }
        self.stats = {
            'zips_scraped': 0,
            'api_calls': 0,
            'stations_found': 0,
            'errors': 0
        }
    
    def scrape_zip_complete(self, zip_code: str) -> Dict:
        """
        Scrape ALL stations for a ZIP using GraphQL API with pagination
        """
        result = {
            'zip': zip_code,
            'success': False,
            'total_stations': 0,
            'stations': [],
            'pages_fetched': 0,
            'error': None
        }
        
        cursor = None
        all_station_ids = set()
        
        while True:
            # Build GraphQL variables
            variables = {
                "fuel": 1,  # Regular gas
                "lang": "en",
                "search": zip_code,
            }
            
            if cursor:
                variables["cursor"] = cursor
            
            # Make API request
            payload = {
                "operationName": "LocationBySearchTerm",
                "variables": variables,
                "query": GRAPHQL_QUERY
            }
            
            try:
                self.stats['api_calls'] += 1
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=15
                )
                
                if response.status_code != 200:
                    result['error'] = f"HTTP {response.status_code}"
                    self.stats['errors'] += 1
                    return result
                
                data = response.json()
                result['pages_fetched'] += 1
                
                # Parse response
                location = data['data']['locationBySearchTerm']
                stations_data = location['stations']
                
                total_count = stations_data['count']
                results = stations_data['results']
                next_cursor = stations_data['cursor']['next'] if stations_data['cursor'] else None
                
                result['total_stations'] = total_count
                
                # Extract stations
                new_stations = 0
                for station in results:
                    station_id = station['id']
                    if station_id not in all_station_ids:
                        all_station_ids.add(station_id)
                        new_stations += 1
                        
                        # Extract price data
                        prices = []
                        for price_report in station.get('prices', []):
                            fuel_type = price_report['fuelProduct']
                            credit_info = price_report.get('credit')
                            if credit_info:
                                prices.append({
                                    'fuel_type': fuel_type,
                                    'price': credit_info.get('price'),
                                    'posted_time': credit_info.get('postedTime'),
                                    'reporter': credit_info.get('nickname')
                                })
                        
                        result['stations'].append({
                            'id': station_id,
                            'name': station['name'],
                            'address': station['address']['line1'],
                            'city': station['address']['locality'],
                            'state': station['address']['region'],
                            'zip': station['address']['postalCode'],
                            'brands': [b['name'] for b in station.get('brands', [])],
                            'prices': prices
                        })
                
                print(f"    Page {result['pages_fetched']}: +{new_stations} new (total: {len(all_station_ids)}/{total_count})")
                
                # Check if done
                if not next_cursor or len(all_station_ids) >= total_count:
                    result['success'] = True
                    self.stats['stations_found'] += len(all_station_ids)
                    break
                
                cursor = next_cursor
                time.sleep(1)  # Polite delay
                
            except requests.Timeout:
                result['error'] = "Timeout"
                self.stats['errors'] += 1
                return result
            except Exception as e:
                result['error'] = str(e)
                self.stats['errors'] += 1
                return result
        
        self.stats['zips_scraped'] += 1
        return result
    
    def test_multiple_zips(self, zip_codes: List[str], delay: float = 2.0):
        """Test scraping multiple ZIPs"""
        print("\n" + "="*70)
        print("GASBUDDY GRAPHQL SCRAPER TEST")
        print("="*70)
        print(f"Testing {len(zip_codes)} ZIP codes")
        print(f"Using GraphQL API: {self.api_url}")
        print("="*70 + "\n")
        
        results = []
        start_time = time.time()
        
        for i, zip_code in enumerate(zip_codes, 1):
            print(f"[{i}/{len(zip_codes)}] ZIP {zip_code}:")
            
            result = self.scrape_zip_complete(zip_code)
            results.append(result)
            
            if result['success']:
                print(f"  ✅ Complete: {len(result['stations'])} stations in {result['pages_fetched']} API call(s)")
            else:
                print(f"  ❌ Failed: {result['error']}")
            
            if i < len(zip_codes):
                time.sleep(delay)
            print()
        
        elapsed = time.time() - start_time
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        successful = sum(1 for r in results if r['success'])
        print(f"\nZIPs scraped: {successful}/{len(zip_codes)}")
        print(f"API calls made: {self.stats['api_calls']}")
        print(f"Stations found: {self.stats['stations_found']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"\nTime elapsed: {elapsed:.1f}s")
        print(f"Average per ZIP: {elapsed/len(zip_codes):.1f}s")
        print(f"API calls per second: {self.stats['api_calls']/elapsed:.2f}")
        
        # Save results
        filename = f"graphql_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump({
                'test_date': datetime.now().isoformat(),
                'stats': self.stats,
                'results': results
            }, f, indent=2)
        
        print(f"\n✅ Results saved to: {filename}")
        print("="*70)
        
        return results


if __name__ == "__main__":
    # Test ZIPs - same ones as before
    test_zips = [
        "33773",   # 7 stations - control
        "77494",   # 34 stations - pagination needed
        "30318",   # 33 stations - pagination needed
        "92101",   # 8 stations
        "33139",   # 5 stations
    ]
    
    scraper = GasBuddyGraphQLScraper()
    results = scraper.test_multiple_zips(test_zips, delay=2.0)
    
    # Verify the 77494 result
    zip_77494 = [r for r in results if r['zip'] == '77494'][0]
    if zip_77494['success']:
        print(f"\n🎯 ZIP 77494 VERIFICATION:")
        print(f"   Expected: 34 stations")
        print(f"   Got: {len(zip_77494['stations'])} stations")
        if len(zip_77494['stations']) == 34:
            print(f"   ✅✅✅ PAGINATION WORKS PERFECTLY!")
        else:
            print(f"   ⚠️  Missing {34 - len(zip_77494['stations'])} stations")

