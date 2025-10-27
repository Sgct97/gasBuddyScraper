#!/usr/bin/env python3
"""
GasBuddy Reconnaissance Probe
Analyzes the website structure, API endpoints, and anti-scraping measures
"""

import requests
import json
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Any
import time

class GasBuddyRecon:
    """Reconnaissance tool for GasBuddy"""
    
    def __init__(self):
        self.base_url = "https://www.gasbuddy.com"
        self.findings = {
            "endpoints": [],
            "headers": {},
            "protection": [],
            "url_patterns": [],
            "data_structure": {}
        }
        
    def test_basic_access(self):
        """Test basic HTTP access and identify protection"""
        print("\n=== TESTING BASIC ACCESS ===")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        try:
            response = requests.get(self.base_url, headers=headers, timeout=10)
            print(f"✓ Status Code: {response.status_code}")
            print(f"✓ Response Time: {response.elapsed.total_seconds():.2f}s")
            
            # Check for protection services
            protection_indicators = {
                "Cloudflare": ["cf-ray", "__cf_bm", "cloudflare"],
                "DataDome": ["datadome", "dd_cookie"],
                "PerimeterX": ["_px", "perimeterx"],
                "Akamai": ["akamai", "_abck"]
            }
            
            for service, indicators in protection_indicators.items():
                for indicator in indicators:
                    if indicator.lower() in str(response.headers).lower() or \
                       indicator.lower() in response.text.lower()[:5000]:
                        print(f"⚠ Detected: {service}")
                        self.findings["protection"].append(service)
                        break
            
            # Check response headers
            print("\nKey Headers:")
            important_headers = ['server', 'x-powered-by', 'content-type', 'cache-control']
            for header in important_headers:
                if header in response.headers:
                    print(f"  {header}: {response.headers[header]}")
                    self.findings["headers"][header] = response.headers[header]
            
            return response
            
        except Exception as e:
            print(f"✗ Error: {e}")
            return None
    
    def test_search_functionality(self, zip_code="90210"):
        """Test how search works"""
        print(f"\n=== TESTING SEARCH: ZIP {zip_code} ===")
        
        # Try different search URL patterns
        patterns = [
            f"{self.base_url}/home?search={zip_code}",
            f"{self.base_url}/search?q={zip_code}",
            f"{self.base_url}/station?search={zip_code}",
            f"{self.base_url}/gaspricemap?zip={zip_code}",
        ]
        
        for pattern in patterns:
            try:
                response = requests.get(pattern, timeout=10)
                if response.status_code == 200:
                    print(f"✓ Working pattern: {pattern}")
                    self.findings["url_patterns"].append({
                        "type": "search",
                        "pattern": pattern,
                        "status": 200
                    })
            except Exception as e:
                print(f"✗ Failed: {pattern} - {e}")
    
    def analyze_page_rendering(self):
        """Determine if content is server-rendered or client-rendered"""
        print("\n=== ANALYZING PAGE RENDERING ===")
        
        try:
            response = requests.get(self.base_url, timeout=10)
            html = response.text
            
            # Check for common JS framework markers
            frameworks = {
                "React": ["react", "__NEXT_DATA__", "_app.js"],
                "Vue": ["vue", "v-app"],
                "Angular": ["ng-app", "angular"],
                "Next.js": ["__NEXT_DATA__", "_next/"],
                "Gatsby": ["gatsby", "___gatsby"]
            }
            
            detected = []
            for framework, markers in frameworks.items():
                if any(marker in html.lower() for marker in markers):
                    detected.append(framework)
                    print(f"✓ Detected framework: {framework}")
            
            self.findings["frameworks"] = detected
            
            # Check if prices are in HTML or need JS
            if "price" in html.lower() or "$" in html[:10000]:
                print("✓ Some data appears in initial HTML")
            else:
                print("⚠ Data likely loaded via JavaScript")
                
        except Exception as e:
            print(f"✗ Error: {e}")
    
    def test_api_patterns(self):
        """Try to identify API endpoints"""
        print("\n=== TESTING API PATTERNS ===")
        
        # Common API patterns
        api_paths = [
            "/api/stations",
            "/api/search",
            "/api/prices",
            "/graphql",
            "/v1/stations",
            "/v2/stations",
            "/api/v1/stations",
        ]
        
        for path in api_paths:
            url = f"{self.base_url}{path}"
            try:
                response = requests.get(url, timeout=5)
                if response.status_code != 404:
                    print(f"✓ Potential endpoint: {path} (Status: {response.status_code})")
                    self.findings["endpoints"].append({
                        "path": path,
                        "status": response.status_code,
                        "content_type": response.headers.get("content-type", "")
                    })
            except Exception:
                pass
    
    def test_mobile_api(self):
        """Test if mobile app API is accessible"""
        print("\n=== TESTING MOBILE API ===")
        
        # Mobile apps often use different APIs
        mobile_headers = {
            "User-Agent": "GasBuddy/6.0 (iOS; iPhone)",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(self.base_url, headers=mobile_headers, timeout=10)
            print(f"Mobile UA Status: {response.status_code}")
            
            # Check if response differs from web
            if "application/json" in response.headers.get("content-type", ""):
                print("✓ Server returns JSON for mobile!")
                self.findings["mobile_api"] = True
                
        except Exception as e:
            print(f"✗ Error: {e}")
    
    def test_rate_limiting(self):
        """Test rate limiting thresholds"""
        print("\n=== TESTING RATE LIMITS ===")
        print("Making 10 rapid requests...")
        
        results = []
        for i in range(10):
            try:
                start = time.time()
                response = requests.get(self.base_url, timeout=10)
                elapsed = time.time() - start
                results.append({
                    "request": i+1,
                    "status": response.status_code,
                    "time": elapsed
                })
                print(f"  Request {i+1}: {response.status_code} ({elapsed:.2f}s)")
                
            except Exception as e:
                print(f"  Request {i+1}: FAILED - {e}")
                results.append({"request": i+1, "status": "error", "error": str(e)})
        
        # Analyze results
        statuses = [r["status"] for r in results if isinstance(r["status"], int)]
        if 429 in statuses:
            print("⚠ RATE LIMITING DETECTED (429)")
        elif 403 in statuses:
            print("⚠ BLOCKING DETECTED (403)")
        else:
            print("✓ No immediate rate limiting observed")
    
    def check_robots_txt(self):
        """Check robots.txt for crawling rules"""
        print("\n=== CHECKING ROBOTS.TXT ===")
        
        try:
            response = requests.get(f"{self.base_url}/robots.txt", timeout=10)
            if response.status_code == 200:
                print("✓ robots.txt found:")
                print(response.text[:500])
                self.findings["robots_txt"] = response.text
            else:
                print("✗ No robots.txt found")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    def check_sitemap(self):
        """Check for sitemap"""
        print("\n=== CHECKING SITEMAP ===")
        
        sitemap_urls = [
            f"{self.base_url}/sitemap.xml",
            f"{self.base_url}/sitemap_index.xml",
            f"{self.base_url}/sitemap/sitemap.xml",
        ]
        
        for url in sitemap_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    print(f"✓ Sitemap found: {url}")
                    print(f"  Size: {len(response.text)} bytes")
                    self.findings["sitemap"] = url
                    return
            except Exception:
                pass
        
        print("✗ No sitemap found")
    
    def run_full_recon(self):
        """Run complete reconnaissance"""
        print("=" * 60)
        print("GASBUDDY RECONNAISSANCE PROBE")
        print("=" * 60)
        
        self.test_basic_access()
        self.check_robots_txt()
        self.check_sitemap()
        self.analyze_page_rendering()
        self.test_search_functionality()
        self.test_api_patterns()
        self.test_mobile_api()
        self.test_rate_limiting()
        
        print("\n" + "=" * 60)
        print("RECONNAISSANCE COMPLETE")
        print("=" * 60)
        
        # Save findings
        with open("recon_findings.json", "w") as f:
            json.dump(self.findings, f, indent=2)
        print("\n✓ Findings saved to recon_findings.json")
        
        return self.findings


if __name__ == "__main__":
    recon = GasBuddyRecon()
    findings = recon.run_full_recon()
    
    print("\n=== SUMMARY ===")
    print(f"Protection detected: {', '.join(findings['protection']) or 'None identified'}")
    print(f"Frameworks: {', '.join(findings.get('frameworks', [])) or 'Unknown'}")
    print(f"API endpoints found: {len(findings['endpoints'])}")
    print(f"URL patterns found: {len(findings['url_patterns'])}")

