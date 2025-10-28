"""
Configuration for Droplet 1 (Primary)
Handles ZIPs 00501-48818 (first half)
"""

# Droplet Identity
DROPLET_ID = 1
DROPLET_NAME = "Gas-Buddy-Scraper-1"

# ZIP Code Assignment
ZIP_FILE = "droplet1_zips.txt"

# Output Files
CSV_OUTPUT_PREFIX = "gasbuddy_droplet1"
PROGRESS_FILE = "progress_droplet1.txt"
COMPLETED_FILE = "completed_zips_droplet1.txt"
FAILED_FILE = "failed_zips_droplet1.txt"

# Proxy Configuration (Oxylabs ISP Proxies 8001-8010)
PROXY_USERNAME = "gasBuddyScraper_5gUpP"
PROXY_PASSWORD = "gasBuddyScraper_123"
PROXY_HOST = "isp.oxylabs.io"
PROXY_PORTS = [8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010]

# Scraping Configuration
NUM_WORKERS = 10
SESSION_REFRESH_MINUTES = 30
MAX_RETRIES = 3
DELAY_MIN = 1.5  # seconds
DELAY_MAX = 3.5  # seconds

# CSV Configuration
CSV_WRITE_INTERVAL = 500  # Write to CSV every N ZIPs

# Monitoring
LOG_FILE = "logs/scraper_droplet1.log"
MONITOR_PORT = 8080

print(f"✅ Loaded config for {DROPLET_NAME}")
print(f"   ZIPs: {ZIP_FILE}")
print(f"   Proxies: {PROXY_HOST}:{PROXY_PORTS[0]}-{PROXY_PORTS[-1]}")
print(f"   Workers: {NUM_WORKERS}")

