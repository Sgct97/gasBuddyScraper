#!/usr/bin/env python3
"""
Start Scraper - Wrapper to start production scraper with optional test mode
"""
import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description='Start GasBuddy scraper')
    parser.add_argument('--test-zips', type=int, help='Run test with N ZIPs only')
    args = parser.parse_args()
    
    # Build command
    cmd = ['python3', '/opt/gasbuddy/production_scraper.py']
    
    if args.test_zips:
        cmd.extend(['--test-zips', str(args.test_zips)])
    
    # Run scraper
    subprocess.run(cmd)

if __name__ == '__main__':
    main()

