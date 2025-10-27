#!/usr/bin/env python3
"""
GasBuddy Scraper - PROVEN Working Approach
Based on actual button click that successfully got all 34 stations for ZIP 77494
"""

import requests
import json
import re
import time
from datetime import datetime
from typing import List, Dict, Optional

# The COMPLETE GraphQL query (140 lines, captured from working request)
GRAPHQL_QUERY = open('full_graphql_query.txt').read()


class GasBuddyScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.csrf_token = None
        self.stats = {
            'zips_scraped': 0,
            'html_requests': 0,
            'graphql_requests': 0,
            'stations_found': 0,
            'errors': 0
        }
    
    def extract_csrf_from_html(self, html: str) -> Optional[str]:
        """Extract CSRF token from HTML (format: 1.XXX)"""
        matches = re.findall(r'csrf["\']?\s*[:=]\s*["\']?([0-9]\.[a-zA-Z0-9._+\-/]+)', html, re.I)
        return matches[0] if matches else None
    
    def extract_apollo_state(self, html: str) -> Optional[Dict]:
        """Extract Apollo state from HTML"""
        match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.+?});', html, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None
    
    def parse_stations_from_apollo(self, apollo_state: Dict) -> tuple[List[Dict], int, Optional[str]]:
        """
        Parse station data from Apollo state
        Returns: (stations_list, total_count, next_cursor)
        """
        stations = []
        total_count = None
        next_cursor = None
        
        # Find Location object which contains count and cursor
        for key, value in apollo_state.items():
            if key.startswith('Location:') and isinstance(value, dict):
                # Look for stations data with fuel parameter
                for subkey, subvalue in value.items():
                    if 'stations' in subkey and isinstance(subvalue, dict):
                        total_count = subvalue.get('count')
                        cursor_data = subvalue.get('cursor', {})
                        if isinstance(cursor_data, dict):
                            next_cursor = cursor_data.get('next')
                        break
                if total_count:
                    break
        
        # Parse stations
        for key, value in apollo_state.items():
            if key.startswith('Station:') and isinstance(value, dict):
                station_id = key.replace('Station:', '')
                
                # Extract address
                address_ref = value.get('address', {}).get('__ref', '')
                address_data = apollo_state.get(address_ref, {})
                
                # Extract prices
                prices = []
                price_refs = value.get('prices', [])
                for price_ref in price_refs:
                    if isinstance(price_ref, dict) and '__ref' in price_ref:
                        price_data = apollo_state.get(price_ref['__ref'], {})
                        credit_ref = price_data.get('credit', {}).get('__ref', '')
                        credit_data = apollo_state.get(credit_ref, {})
                        
                        if credit_data.get('price'):
                            prices.append({
                                'fuel_type': price_data.get('fuelProduct'),
                                'price': credit_data.get('price'),
                                'posted_time': credit_data.get('postedTime'),
                                'reporter': credit_data.get('nickname')
                            })
                
                stations.append({
                    'id': station_id,
                    'name': value.get('name', ''),
                    'address': address_data.get('line1', ''),
                    'city': address_data.get('locality', ''),
                    'state': address_data.get('region', ''),
                    'zip': address_data.get('postalCode', ''),
                    'prices': prices
                })
        
        return stations, total_count, next_cursor
    
    def get_initial_page(self, zip_code: str) -> Dict:
        """Get initial HTML page and extract first batch of stations"""
        url = f"https://www.gasbuddy.com/home?search={zip_code}"
        
        try:
            self.stats['html_requests'] += 1
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                return {'error': f'HTTP {response.status_code}', 'stations': [], 'total': 0, 'cursor': None}
            
            html = response.text
            
            # Extract CSRF token
            self.csrf_token = self.extract_csrf_from_html(html)
            if not self.csrf_token:
                return {'error': 'No CSRF token found', 'stations': [], 'total': 0, 'cursor': None}
            
            # Extract Apollo state
            apollo_state = self.extract_apollo_state(html)
            if not apollo_state:
                return {'error': 'No Apollo state found', 'stations': [], 'total': 0, 'cursor': None}
            
            stations, total_count, next_cursor = self.parse_stations_from_apollo(apollo_state)
            
            return {
                'error': None,
                'stations': stations,
                'total': total_count or len(stations),
                'cursor': next_cursor
            }
            
        except Exception as e:
            return {'error': str(e), 'stations': [], 'total': 0, 'cursor': None}
    
    def get_more_stations(self, zip_code: str, cursor: str) -> Dict:
        """
        Use GraphQL API to get more stations
        Using the PROVEN headers from successful button click
        """
        if not self.csrf_token:
            return {'error': 'No CSRF token', 'stations': [], 'cursor': None}
        
        url = "https://www.gasbuddy.com/graphql"
        
        # PROVEN headers from successful manual click
        headers = {
            "accept": "*/*",
            "apollo-require-preflight": "true",
            "content-type": "application/json",
            "gbcsrf": self.csrf_token,
            "referer": f"https://www.gasbuddy.com/home?search={zip_code}",
            "sec-ch-ua": '"Not=A?Brand";v="24", "Chromium";v="140"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
        }
        
        payload = {
            "operationName": "LocationBySearchTerm",
            "variables": {
                "fuel": 1,
                "lang": "en",
                "search": zip_code,
                "cursor": cursor
            },
            "query": GRAPHQL_QUERY
        }
        
        try:
            self.stats['graphql_requests'] += 1
            response = self.session.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return {'error': f'HTTP {response.status_code}', 'stations': [], 'cursor': None}
            
            data = response.json()
            
            # Parse GraphQL response
            location = data['data']['locationBySearchTerm']
            stations_data = location['stations']
            
            stations = []
            for station in stations_data['results']:
                prices = []
                for price_report in station.get('prices', []):
                    credit_info = price_report.get('credit')
                    if credit_info:
                        prices.append({
                            'fuel_type': price_report['fuelProduct'],
                            'price': credit_info.get('price'),
                            'posted_time': credit_info.get('postedTime'),
                            'reporter': credit_info.get('nickname')
                        })
                
                stations.append({
                    'id': station['id'],
                    'name': station['name'],
                    'address': station['address']['line1'],
                    'city': station['address']['locality'],
                    'state': station['address']['region'],
                    'zip': station['address']['postalCode'],
                    'prices': prices
                })
            
            next_cursor = stations_data['cursor']['next'] if stations_data['cursor'] else None
            
            return {
                'error': None,
                'stations': stations,
                'cursor': next_cursor
            }
            
        except Exception as e:
            return {'error': str(e), 'stations': [], 'cursor': None}
    
    def scrape_zip_complete(self, zip_code: str, delay: float = 2.0) -> Dict:
        """
        Scrape ALL stations for a ZIP code
        Returns complete result with all stations
        """
        result = {
            'zip': zip_code,
            'success': False,
            'total_expected': 0,
            'total_found': 0,
            'stations': [],
            'pages_fetched': 0,
            'error': None
        }
        
        print(f"  📄 Loading HTML page...")
        initial = self.get_initial_page(zip_code)
        
        if initial['error']:
            result['error'] = f"HTML: {initial['error']}"
            self.stats['errors'] += 1
            return result
        
        result['pages_fetched'] = 1
        result['total_expected'] = initial['total']
        result['stations'] = initial['stations']
        all_station_ids = {s['id'] for s in initial['stations']}
        
        print(f"    Got {len(initial['stations'])} stations (total: {initial['total']})")
        print(f"    CSRF: {self.csrf_token[:15]}...")
        print(f"    Next cursor: {initial['cursor']}")
        
        # Paginate if needed
        cursor = initial['cursor']
        
        while cursor and len(all_station_ids) < result['total_expected']:
            print(f"  🔄 Fetching more (cursor={cursor})...")
            time.sleep(delay)  # Polite delay
            
            more = self.get_more_stations(zip_code, cursor)
            
            if more['error']:
                result['error'] = f"GraphQL: {more['error']}"
                self.stats['errors'] += 1
                break
            
            result['pages_fetched'] += 1
            
            new_stations = 0
            for station in more['stations']:
                if station['id'] not in all_station_ids:
                    all_station_ids.add(station['id'])
                    result['stations'].append(station)
                    new_stations += 1
            
            print(f"    +{new_stations} new (total: {len(all_station_ids)}/{result['total_expected']})")
            
            cursor = more['cursor']
            
            # Stop if we have all stations or no more cursor
            if not cursor or len(all_station_ids) >= result['total_expected']:
                break
        
        result['total_found'] = len(all_station_ids)
        result['success'] = result['total_found'] >= result['total_expected']
        
        if result['success']:
            self.stats['stations_found'] += result['total_found']
            self.stats['zips_scraped'] += 1
        
        return result
    
    def test_multiple_zips(self, zip_codes: List[str], delay: float = 3.0):
        """Test scraping multiple ZIPs with delays"""
        print("\n" + "="*70)
        print("GASBUDDY PROVEN SCRAPER TEST")
        print("="*70)
        print(f"Testing {len(zip_codes)} ZIP codes")
        print(f"Delay between ZIPs: {delay}s")
        print("="*70 + "\n")
        
        results = []
        start_time = time.time()
        
        for i, zip_code in enumerate(zip_codes, 1):
            print(f"[{i}/{len(zip_codes)}] ZIP {zip_code}:")
            
            result = self.scrape_zip_complete(zip_code, delay=2.0)
            results.append(result)
            
            if result['success']:
                print(f"  ✅ Complete: {result['total_found']}/{result['total_expected']} stations in {result['pages_fetched']} request(s)\n")
            else:
                print(f"  ⚠️  Partial: {result['total_found']}/{result['total_expected']} stations, error: {result['error']}\n")
            
            # Delay between ZIPs
            if i < len(zip_codes):
                time.sleep(delay)
        
        elapsed = time.time() - start_time
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        successful = sum(1 for r in results if r['success'])
        print(f"\nZIPs scraped successfully: {successful}/{len(zip_codes)}")
        print(f"HTML requests: {self.stats['html_requests']}")
        print(f"GraphQL requests: {self.stats['graphql_requests']}")
        print(f"Total API calls: {self.stats['html_requests'] + self.stats['graphql_requests']}")
        print(f"Stations found: {self.stats['stations_found']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"\nTime elapsed: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        print(f"Average per ZIP: {elapsed/len(zip_codes):.1f}s")
        
        # Save results
        filename = f"proven_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
    # Test ZIPs - including the proven one (77494 with 34 stations)
    test_zips = [
        "33773",   # 7 stations - small
        "77494",   # 34 stations - PROVEN to work with pagination
        "30318",   # 33 stations - large
    ]
    
    scraper = GasBuddyScraper()
    results = scraper.test_multiple_zips(test_zips, delay=5.0)
    
    # Verify ZIP 77494 specifically
    zip_77494 = [r for r in results if r['zip'] == '77494'][0]
    print(f"\n🎯 ZIP 77494 VERIFICATION:")
    print(f"   Expected: 34 stations")
    print(f"   Got: {zip_77494['total_found']} stations")
    print(f"   Pages: {zip_77494['pages_fetched']}")
    
    if zip_77494['total_found'] == 34:
        print(f"   ✅✅✅ PERFECT MATCH - PAGINATION WORKS!")
    else:
        print(f"   ⚠️  Difference: {34 - zip_77494['total_found']} stations")

