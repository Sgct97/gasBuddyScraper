#!/usr/bin/env python3
"""
GasBuddy Scraper - Proof of Concept
Tests pagination, rate limits, and determines if proxies are needed
"""

import requests
import json
import time
from datetime import datetime
from typing import Set, Dict, List, Optional
import random

class GasBuddyScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Tracking
        self.stats = {
            'requests_made': 0,
            'requests_succeeded': 0,
            'requests_failed': 0,
            'rate_limit_hits': 0,
            'cloudflare_blocks': 0,
            'stations_found': 0,
            'zips_with_pagination': 0,
        }
    
    def extract_apollo_state(self, html: str) -> dict:
        """Extract Apollo GraphQL state from HTML"""
        start = html.find('window.__APOLLO_STATE__')
        if start == -1:
            return {}
        
        eq_pos = html.find('=', start)
        json_start = eq_pos + 1
        
        brace_count = 0
        in_string = False
        escape = False
        
        for i in range(json_start, len(html)):
            char = html[i]
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            json_str = html[json_start:i+1].strip()
                            return json.loads(json_str)
                        except Exception as e:
                            print(f"    JSON parse error: {e}")
                            return {}
        return {}
    
    def scrape_zip_with_pagination(self, zip_code: str) -> Dict:
        """
        Scrape all stations from a ZIP code, handling pagination
        Returns: {
            'zip': str,
            'total_stations': int,
            'stations': [station_data],
            'pages_needed': int,
            'success': bool
        }
        """
        result = {
            'zip': zip_code,
            'total_stations': 0,
            'stations': [],
            'pages_needed': 0,
            'success': False,
            'error': None
        }
        
        cursor = None
        page = 1
        all_station_ids = set()
        
        while True:
            # Build URL with cursor if needed
            if cursor:
                url = f"https://www.gasbuddy.com/home?search={zip_code}&cursor={cursor}"
            else:
                url = f"https://www.gasbuddy.com/home?search={zip_code}"
            
            print(f"  Page {page}: Fetching...")
            self.stats['requests_made'] += 1
            
            try:
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 403:
                    self.stats['cloudflare_blocks'] += 1
                    result['error'] = 'Cloudflare block (403)'
                    print(f"    ✗ Blocked by Cloudflare")
                    return result
                
                elif response.status_code == 429:
                    self.stats['rate_limit_hits'] += 1
                    result['error'] = 'Rate limited (429)'
                    print(f"    ✗ Rate limited")
                    return result
                
                elif response.status_code != 200:
                    self.stats['requests_failed'] += 1
                    result['error'] = f'HTTP {response.status_code}'
                    print(f"    ✗ Status {response.status_code}")
                    return result
                
                # Parse Apollo state
                data = self.extract_apollo_state(response.text)
                
                if not data:
                    result['error'] = 'No Apollo state found'
                    print(f"    ✗ No data found")
                    return result
                
                # Find location data
                found_stations = False
                for key, value in data.items():
                    if key.startswith('Location:'):
                        for loc_key, loc_value in value.items():
                            if 'stations' in loc_key and isinstance(loc_value, dict):
                                found_stations = True
                                
                                total = loc_value.get('count', 0)
                                results = loc_value.get('results', [])
                                cursor_data = loc_value.get('cursor', {})
                                next_cursor = cursor_data.get('next')
                                
                                # Extract station IDs and details
                                for ref in results:
                                    if '__ref' in ref:
                                        station_id = ref['__ref'].split(':')[1]
                                        if station_id not in all_station_ids:
                                            all_station_ids.add(station_id)
                                            
                                            # Get station details from Apollo state
                                            station_key = f"Station:{station_id}"
                                            if station_key in data:
                                                station = data[station_key]
                                                result['stations'].append({
                                                    'id': station_id,
                                                    'name': station.get('name', 'Unknown'),
                                                    'address': station.get('address', {}).get('line1', 'Unknown'),
                                                    'city': station.get('address', {}).get('locality', 'Unknown'),
                                                    'prices': self._extract_prices(station)
                                                })
                                
                                result['total_stations'] = total
                                result['pages_needed'] = page
                                
                                print(f"    ✓ Found {len(results)} stations (Total: {total}, Got: {len(all_station_ids)})")
                                
                                # Check if we need to paginate
                                if next_cursor and len(all_station_ids) < total:
                                    cursor = next_cursor
                                    page += 1
                                    self.stats['zips_with_pagination'] += 1
                                    time.sleep(random.uniform(1.0, 2.0))  # Polite delay
                                    break
                                else:
                                    # Done!
                                    result['success'] = True
                                    self.stats['requests_succeeded'] += 1
                                    self.stats['stations_found'] += len(all_station_ids)
                                    return result
                
                if not found_stations:
                    result['error'] = 'No stations in response'
                    print(f"    ✗ No stations found")
                    return result
                    
            except requests.Timeout:
                result['error'] = 'Timeout'
                self.stats['requests_failed'] += 1
                print(f"    ✗ Timeout")
                return result
                
            except Exception as e:
                result['error'] = str(e)
                self.stats['requests_failed'] += 1
                print(f"    ✗ Error: {e}")
                return result
        
        return result
    
    def _extract_prices(self, station: dict) -> List[dict]:
        """Extract price data from station"""
        prices = []
        for price_report in station.get('prices', []):
            fuel = price_report.get('fuelProduct', 'unknown')
            credit_info = price_report.get('credit')
            if credit_info:
                prices.append({
                    'fuel_type': fuel,
                    'price': credit_info.get('price'),
                    'posted_time': credit_info.get('postedTime'),
                    'reporter': credit_info.get('nickname', 'anonymous')
                })
        return prices
    
    def run_test(self, test_zips: List[str], delay_between_zips: float = 2.0):
        """Run test scrape on sample ZIPs"""
        print("\n" + "="*70)
        print("GASBUDDY SCRAPER - PROOF OF CONCEPT TEST")
        print("="*70)
        print(f"Testing {len(test_zips)} ZIP codes")
        print(f"Delay between ZIPs: {delay_between_zips}s")
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        results = []
        start_time = time.time()
        
        for i, zip_code in enumerate(test_zips, 1):
            print(f"[{i}/{len(test_zips)}] Scraping ZIP: {zip_code}")
            
            result = self.scrape_zip_with_pagination(zip_code)
            results.append(result)
            
            if result['success']:
                print(f"  ✅ Success: {len(result['stations'])} stations, {result['pages_needed']} page(s)")
            else:
                print(f"  ❌ Failed: {result['error']}")
            
            # Delay between requests (except last one)
            if i < len(test_zips):
                time.sleep(delay_between_zips)
            print()
        
        elapsed = time.time() - start_time
        
        # Print summary
        self._print_summary(results, elapsed)
        
        # Save results
        self._save_results(results)
        
        return results
    
    def _print_summary(self, results: List[dict], elapsed: float):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        print(f"\nZIPs tested: {len(results)}")
        print(f"Successful: {successful} ({successful/len(results)*100:.1f}%)")
        print(f"Failed: {failed} ({failed/len(results)*100:.1f}%)")
        
        print(f"\nTotal requests made: {self.stats['requests_made']}")
        print(f"Requests succeeded: {self.stats['requests_succeeded']}")
        print(f"Requests failed: {self.stats['requests_failed']}")
        print(f"Rate limits hit: {self.stats['rate_limit_hits']}")
        print(f"Cloudflare blocks: {self.stats['cloudflare_blocks']}")
        
        print(f"\nStations found: {self.stats['stations_found']}")
        print(f"ZIPs requiring pagination: {self.stats['zips_with_pagination']}")
        
        print(f"\nTime elapsed: {elapsed:.1f}s")
        print(f"Average per ZIP: {elapsed/len(results):.1f}s")
        print(f"Requests per second: {self.stats['requests_made']/elapsed:.2f}")
        
        # Proxy recommendation
        print("\n" + "-"*70)
        print("PROXY RECOMMENDATION:")
        print("-"*70)
        
        if self.stats['cloudflare_blocks'] > 0:
            print("🚨 Cloudflare blocks detected - PROXIES REQUIRED")
        elif self.stats['rate_limit_hits'] > 0:
            print("⚠️  Rate limiting detected - Proxies recommended for scale")
        elif self.stats['requests_failed'] / self.stats['requests_made'] > 0.1:
            print("⚠️  High failure rate - Consider proxies")
        else:
            print("✅ No major issues - May work without proxies at low volume")
            print("   For 42K ZIPs: Proxies recommended to avoid rate limits")
        
        print("="*70)
    
    def _save_results(self, results: List[dict]):
        """Save results to JSON"""
        filename = f"poc_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output = {
            'test_date': datetime.now().isoformat(),
            'stats': self.stats,
            'results': results
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✅ Results saved to: {filename}")


if __name__ == "__main__":
    # Test ZIPs - mix of sizes
    test_zips = [
        # Small (control)
        "33773",   # 7 stations
        "90210",   # 1 station
        
        # Medium
        "92101",   # ~8 stations
        "33139",   # ~5 stations
        
        # Large (pagination needed)
        "77494",   # 34 stations
        "30318",   # 33 stations
        
        # Additional samples
        "60614",   # Chicago
        "98101",   # Seattle
        "02108",   # Boston
        "33301",   # Fort Lauderdale
    ]
    
    scraper = GasBuddyScraper()
    results = scraper.run_test(test_zips, delay_between_zips=2.0)

