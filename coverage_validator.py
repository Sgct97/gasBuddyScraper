#!/usr/bin/env python3
"""
GasBuddy Coverage Validator
Ensures we capture 100% of stations using multiple methods
"""

import requests
import json
import re
import time
from collections import defaultdict
from typing import Set, Dict, List

class GasBuddyCoverageValidator:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        self.station_ids_by_method = {
            'zip_search': set(),
            'city_search': set(),
            'sequential_scan': set(),
            'state_pages': set()
        }
        self.station_details = {}  # Store metadata for validation
        
    def extract_apollo_state(self, html: str) -> dict:
        """Extract Apollo state from HTML"""
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
                        json_end = i + 1
                        break
        
        try:
            json_str = html[json_start:json_end].strip()
            return json.loads(json_str)
        except:
            return {}
    
    def search_by_zip(self, zip_code: str) -> Set[str]:
        """Method 1: Search by ZIP code"""
        url = f"https://www.gasbuddy.com/home?search={zip_code}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                print(f"  ✗ ZIP {zip_code}: Status {response.status_code}")
                return set()
            
            data = self.extract_apollo_state(response.text)
            station_ids = set()
            
            # Find location data
            for key, value in data.items():
                if key.startswith('Location:'):
                    for loc_key, loc_value in value.items():
                        if 'stations' in loc_key and isinstance(loc_value, dict):
                            results = loc_value.get('results', [])
                            count = loc_value.get('count', 0)
                            
                            for ref in results:
                                if '__ref' in ref:
                                    station_id = ref['__ref'].split(':')[1]
                                    station_ids.add(station_id)
                            
                            print(f"  ✓ ZIP {zip_code}: {len(station_ids)}/{count} stations")
                            
                            # Store for validation
                            for sid in station_ids:
                                if sid in data:
                                    station = data[sid]
                                    self.station_details[sid] = {
                                        'name': station.get('name'),
                                        'zip': zip_code,
                                        'address': station.get('address', {}).get('line1')
                                    }
            
            self.station_ids_by_method['zip_search'].update(station_ids)
            return station_ids
            
        except Exception as e:
            print(f"  ✗ ZIP {zip_code}: {e}")
            return set()
    
    def search_by_city(self, city: str, state: str) -> Set[str]:
        """Method 2: Search by city name"""
        search_term = f"{city}, {state}"
        url = f"https://www.gasbuddy.com/home?search={search_term.replace(' ', '+')}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            data = self.extract_apollo_state(response.text)
            
            station_ids = set()
            for key, value in data.items():
                if key.startswith('Location:'):
                    for loc_key, loc_value in value.items():
                        if 'stations' in loc_key and isinstance(loc_value, dict):
                            results = loc_value.get('results', [])
                            for ref in results:
                                if '__ref' in ref:
                                    station_id = ref['__ref'].split(':')[1]
                                    station_ids.add(station_id)
            
            print(f"  ✓ City {search_term}: {len(station_ids)} stations")
            self.station_ids_by_method['city_search'].update(station_ids)
            return station_ids
            
        except Exception as e:
            print(f"  ✗ City {search_term}: {e}")
            return set()
    
    def scan_id_range(self, start_id: int, end_id: int, sample_rate: int = 100) -> Set[str]:
        """Method 3: Sequential ID scanning"""
        print(f"\n  Testing ID range {start_id} to {end_id} (sampling every {sample_rate})")
        
        valid_ids = set()
        for test_id in range(start_id, end_id, sample_rate):
            url = f"https://www.gasbuddy.com/station/{test_id}"
            try:
                response = requests.head(url, headers=self.headers, timeout=5)
                if response.status_code == 200:
                    valid_ids.add(str(test_id))
                    print(f"    ✓ ID {test_id} exists")
                time.sleep(0.5)
            except:
                pass
        
        self.station_ids_by_method['sequential_scan'].update(valid_ids)
        return valid_ids
    
    def validate_coverage(self) -> Dict:
        """Compare results from all methods and identify gaps"""
        print("\n" + "="*60)
        print("COVERAGE VALIDATION REPORT")
        print("="*60)
        
        results = {}
        
        # Count by method
        for method, ids in self.station_ids_by_method.items():
            results[method] = len(ids)
            print(f"\n{method.upper()}: {len(ids)} stations")
        
        # Find the superset (union of all methods)
        all_stations = set()
        for ids in self.station_ids_by_method.values():
            all_stations.update(ids)
        
        results['total_unique'] = len(all_stations)
        print(f"\nTOTAL UNIQUE STATIONS: {len(all_stations)}")
        
        # Find stations only in one method (potential gaps)
        print("\n" + "-"*60)
        print("COVERAGE ANALYSIS")
        print("-"*60)
        
        for method, ids in self.station_ids_by_method.items():
            only_in_this = ids - set().union(*[s for m, s in self.station_ids_by_method.items() if m != method])
            if only_in_this:
                results[f'{method}_exclusive'] = len(only_in_this)
                print(f"\n{method} ONLY ({len(only_in_this)} stations):")
                for sid in list(only_in_this)[:5]:
                    details = self.station_details.get(sid, {})
                    print(f"  - {sid}: {details.get('name', 'Unknown')}")
        
        # Overlap analysis
        zip_and_city = self.station_ids_by_method['zip_search'] & self.station_ids_by_method['city_search']
        results['zip_city_overlap'] = len(zip_and_city)
        print(f"\nZIP ∩ CITY overlap: {len(zip_and_city)} stations")
        
        # Coverage percentage
        if len(all_stations) > 0:
            for method, ids in self.station_ids_by_method.items():
                coverage = (len(ids) / len(all_stations)) * 100
                results[f'{method}_coverage_pct'] = coverage
                print(f"{method} coverage: {coverage:.1f}%")
        
        return results
    
    def export_station_list(self, filename: str = "all_stations.json"):
        """Export complete station list for client proof"""
        all_stations = set()
        for ids in self.station_ids_by_method.values():
            all_stations.update(ids)
        
        export_data = {
            'total_stations': len(all_stations),
            'collection_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'methods_used': list(self.station_ids_by_method.keys()),
            'stations': []
        }
        
        for sid in sorted(all_stations, key=int):
            station_info = {
                'id': sid,
                'found_by_methods': []
            }
            
            for method, ids in self.station_ids_by_method.items():
                if sid in ids:
                    station_info['found_by_methods'].append(method)
            
            if sid in self.station_details:
                station_info.update(self.station_details[sid])
            
            export_data['stations'].append(station_info)
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\n✓ Exported {len(all_stations)} stations to {filename}")
        return export_data


# Test with a small sample
if __name__ == "__main__":
    validator = GasBuddyCoverageValidator()
    
    print("="*60)
    print("GASBUDDY COVERAGE VALIDATION TEST")
    print("="*60)
    
    # Test a few ZIP codes
    print("\n=== METHOD 1: ZIP CODE SEARCH ===")
    test_zips = ['33773', '90210', '10001', '60601', '75201']
    for zip_code in test_zips:
        validator.search_by_zip(zip_code)
        time.sleep(1)
    
    # Test cities
    print("\n=== METHOD 2: CITY SEARCH ===")
    test_cities = [
        ('Largo', 'FL'),
        ('Beverly Hills', 'CA'),
        ('New York', 'NY')
    ]
    for city, state in test_cities:
        validator.search_by_city(city, state)
        time.sleep(1)
    
    # Validate
    results = validator.validate_coverage()
    
    # Export
    validator.export_station_list('validation_test.json')
    
    print("\n" + "="*60)
    print("✓ VALIDATION COMPLETE")
    print("="*60)

