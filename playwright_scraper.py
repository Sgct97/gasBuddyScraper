#!/usr/bin/env python3
"""
GasBuddy Playwright Scraper
Uses real browser to click "more" buttons and capture all stations
"""
from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime
from typing import List, Dict


class PlaywrightGasBuddyScraper:
    def __init__(self):
        self.stats = {
            'zips_scraped': 0,
            'button_clicks': 0,
            'stations_found': 0,
            'errors': 0
        }
    
    def _extract_stations_from_apollo(self, apollo_state: Dict, zip_code: str) -> List[Dict]:
        """
        Extract station list from Apollo state
        NOTE: Apollo state has nested references that need to be resolved
        """
        stations = []
        
        for key, value in apollo_state.items():
            if key.startswith('Station:') and isinstance(value, dict):
                station_id = key.replace('Station:', '')
                
                # Get address - handle both direct data and references
                address_info = value.get('address', {})
                if isinstance(address_info, dict):
                    if '__ref' in address_info:
                        # It's a reference, resolve it
                        address_data = apollo_state.get(address_info['__ref'], {})
                    else:
                        # Direct data
                        address_data = address_info
                else:
                    address_data = {}
                
                # Get prices
                prices = []
                price_refs = value.get('prices', [])
                for price_ref in price_refs:
                    if isinstance(price_ref, dict):
                        if '__ref' in price_ref:
                            # It's a reference, resolve it
                            price_data = apollo_state.get(price_ref['__ref'], {})
                        else:
                            # Direct data
                            price_data = price_ref
                        
                        # Get both cash and credit info - PREFER CASH
                        cash_info = price_data.get('cash', {})
                        credit_info = price_data.get('credit', {})
                        
                        # Resolve references for cash
                        if isinstance(cash_info, dict):
                            if '__ref' in cash_info:
                                cash_data = apollo_state.get(cash_info['__ref'], {})
                            else:
                                cash_data = cash_info
                        else:
                            cash_data = {}
                        
                        # Resolve references for credit
                        if isinstance(credit_info, dict):
                            if '__ref' in credit_info:
                                credit_data = apollo_state.get(credit_info['__ref'], {})
                            else:
                                credit_data = credit_info
                        else:
                            credit_data = {}
                        
                        # Prefer cash over credit (cash is cheaper!)
                        price_to_use = cash_data if (cash_data and cash_data.get('price')) else credit_data
                        
                        if price_to_use and price_to_use.get('price') is not None:
                            prices.append({
                                'fuel_type': price_data.get('fuelProduct'),
                                'price': price_to_use.get('price'),
                                'posted_time': price_to_use.get('postedTime'),
                                'reporter': price_to_use.get('nickname'),
                                'price_type': 'cash' if price_to_use == cash_data else 'credit'
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
        
        return stations
    
    def scrape_zip_complete(self, zip_code: str, page) -> Dict:
        """
        Scrape all stations for a ZIP using Playwright
        Clicks "more" buttons until all stations loaded
        """
        result = {
            'zip': zip_code,
            'success': False,
            'total_expected': 0,
            'total_found': 0,
            'stations': [],
            'button_clicks': 0,
            'error': None
        }
        
        try:
            # Load page
            print(f"  📄 Loading page...")
            page.goto(f"https://www.gasbuddy.com/home?search={zip_code}", 
                     wait_until="domcontentloaded", timeout=60000)
            
            # Wait for Cloudflare to pass
            print(f"    Waiting for Cloudflare...")
            time.sleep(10)  # Give Cloudflare time to pass
            
            # Debug: check what's on page
            title = page.title()
            print(f"    Page title: {title[:50]}")
            
            # Extract initial stations BEFORE clicking
            print(f"  📊 Extracting initial stations...")
            apollo_initial = page.evaluate('() => window.__APOLLO_STATE__')
            all_stations = []
            all_station_ids = set()
            
            if apollo_initial:
                initial_stations = self._extract_stations_from_apollo(apollo_initial, zip_code)
                all_stations.extend(initial_stations)
                all_station_ids.update(s['id'] for s in initial_stations)
                print(f"    Initial batch: {len(initial_stations)} stations")
            
            # Keep clicking "more" link until it disappears
            print(f"  🔍 Looking for 'more' button...")
            clicks = 0
            max_clicks = 10  # Safety limit
            
            while clicks < max_clicks:
                # Look for "More ... Gas Prices" link (it's an <a> tag, not a button!)
                more_link = page.locator('a:has-text("More"), a:has-text("more")').first
                
                if not more_link.count():
                    print(f"    No 'more' link found (clicks: {clicks})")
                    break
                
                # Scroll to the link
                more_link.scroll_into_view_if_needed()
                time.sleep(1)
                
                # Click and wait for GraphQL response
                print(f"  🖱️  Clicking 'more' link (click #{clicks+1})...")
                
                # Wait for the GraphQL response after clicking
                with page.expect_response(lambda response: 'graphql' in response.url) as response_info:
                    more_link.click()
                
                response = response_info.value
                print(f"    ✅ Got GraphQL response!")
                
                # Extract stations directly from the GraphQL response
                try:
                    response_data = response.json()
                    if 'data' in response_data:
                        stations_data = response_data['data']['locationBySearchTerm']['stations']
                        response_stations = stations_data['results']
                        print(f"    📦 Response contains {len(response_stations)} stations")
                        
                        # Add stations from response
                        added = 0
                        for station in response_stations:
                            station_id = station['id']
                            if station_id not in all_station_ids:
                                # Extract price data - PREFER CASH over CREDIT (cash is cheaper!)
                                prices = []
                                for price_report in station.get('prices', []):
                                    cash_info = price_report.get('cash', {})
                                    credit_info = price_report.get('credit', {})
                                    
                                    # Use cash price if available, otherwise credit
                                    price_to_use = cash_info if (cash_info and cash_info.get('price')) else credit_info
                                    
                                    if price_to_use and price_to_use.get('price'):
                                        prices.append({
                                            'fuel_type': price_report['fuelProduct'],
                                            'price': price_to_use.get('price'),
                                            'posted_time': price_to_use.get('postedTime'),
                                            'reporter': price_to_use.get('nickname'),
                                            'price_type': 'cash' if price_to_use == cash_info else 'credit'
                                        })
                                
                                all_stations.append({
                                    'id': station_id,
                                    'name': station['name'],
                                    'address': station['address']['line1'],
                                    'city': station['address']['locality'],
                                    'state': station['address']['region'],
                                    'zip': station['address']['postalCode'],
                                    'prices': prices
                                })
                                all_station_ids.add(station_id)
                                added += 1
                        
                        print(f"    Added {added} new stations (total: {len(all_stations)})")
                except Exception as e:
                    print(f"    ⚠️  Error parsing response: {e}")
                
                clicks += 1
                result['button_clicks'] = clicks
                self.stats['button_clicks'] += 1
                
                time.sleep(1)
                
                
                # Check if there are more links
                if not page.locator('a:has-text("More"), a:has-text("more")').count():
                    print(f"    No more links after {clicks} click(s)")
                    break
            
            # Get final total count from Location object
            print(f"  ✅ Extraction complete!")
            apollo_final = page.evaluate('() => window.__APOLLO_STATE__')
            total_count = None
            
            if apollo_final:
                for key, value in apollo_final.items():
                    if key.startswith('Location:') and isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            if 'stations' in subkey and isinstance(subvalue, dict):
                                total_count = subvalue.get('count')
                                break
                        if total_count:
                            break
            
            result['stations'] = all_stations
            result['total_found'] = len(all_stations)
            result['total_expected'] = total_count or len(all_stations)
            result['success'] = result['total_found'] >= result['total_expected']
            
            if result['success']:
                self.stats['stations_found'] += result['total_found']
                self.stats['zips_scraped'] += 1
            
            print(f"    FINAL TOTAL: {result['total_found']}/{result['total_expected']} stations")
            
        except Exception as e:
            result['error'] = str(e)
            self.stats['errors'] += 1
        
        return result
    
    def test_multiple_zips(self, zip_codes: List[str], delay: float = 5.0):
        """Test scraping multiple ZIPs"""
        print("\n" + "="*70)
        print("GASBUDDY PLAYWRIGHT SCRAPER TEST")
        print("="*70)
        print(f"Testing {len(zip_codes)} ZIP codes")
        print(f"Delay between ZIPs: {delay}s")
        print("="*70 + "\n")
        
        results = []
        start_time = time.time()
        
        with sync_playwright() as p:
            # Launch browser once for all tests
            # headless=True for production, False for debugging
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            for i, zip_code in enumerate(zip_codes, 1):
                print(f"[{i}/{len(zip_codes)}] ZIP {zip_code}:")
                
                result = self.scrape_zip_complete(zip_code, page)
                results.append(result)
                
                if result['success']:
                    print(f"  ✅ Complete: {result['total_found']}/{result['total_expected']} stations ({result['button_clicks']} clicks)\n")
                else:
                    print(f"  ⚠️  Error: {result['error']}\n")
                
                # Delay between ZIPs
                if i < len(zip_codes):
                    print(f"  ⏳ Waiting {delay}s...")
                    time.sleep(delay)
            
            browser.close()
        
        elapsed = time.time() - start_time
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        successful = sum(1 for r in results if r['success'])
        total_clicks = sum(r['button_clicks'] for r in results)
        
        print(f"\nZIPs scraped successfully: {successful}/{len(zip_codes)}")
        print(f"Total button clicks: {total_clicks}")
        print(f"Stations found: {self.stats['stations_found']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"\nTime elapsed: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        print(f"Average per ZIP: {elapsed/len(zip_codes):.1f}s")
        
        # Save results
        filename = f"playwright_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
    test_zips = [
        "77494",   # 34 stations - PROVEN to work with manual click
    ]
    
    scraper = PlaywrightGasBuddyScraper()
    results = scraper.test_multiple_zips(test_zips, delay=0)  # Only 1 ZIP, no delay needed
    
    # Verify ZIP 77494
    zip_77494 = [r for r in results if r['zip'] == '77494'][0]
    print(f"\n🎯 ZIP 77494 VERIFICATION:")
    print(f"   Expected: 34 stations")
    print(f"   Got: {zip_77494['total_found']} stations")
    print(f"   Button clicks: {zip_77494['button_clicks']}")
    
    if zip_77494['total_found'] == 34:
        print(f"   ✅✅✅ PERFECT MATCH!")
    else:
        print(f"   ⚠️  Difference: {34 - zip_77494['total_found']} stations")

