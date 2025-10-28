"""
Configuration for Droplet 2 (Secondary)
Handles ZIPs 48819-99950 (second half)
"""

# Droplet Identity
DROPLET_ID = 2
DROPLET_NAME = "Gas-Buddy-Scraper-2"

# ZIP Code Assignment
ZIP_FILE = "droplet2_zips.txt"

# Output Files
CSV_OUTPUT_PREFIX = "gasbuddy_droplet2"
PROGRESS_FILE = "progress_droplet2.txt"
COMPLETED_FILE = "completed_zips_droplet2.txt"
FAILED_FILE = "failed_zips_droplet2.txt"

# Proxy Configuration (Oxylabs ISP Proxies 8011-8020 - USER WILL PROVIDE)
PROXY_USERNAME = "gasBuddyScraper_5gUpP"  # Same username
PROXY_PASSWORD = "gasBuddyScraper_123"     # Same password
PROXY_HOST = "isp.oxylabs.io"
PROXY_PORTS = [8011, 8012, 8013, 8014, 8015, 8016, 8017, 8018, 8019, 8020]

# Scraping Configuration
NUM_WORKERS = 10
SESSION_REFRESH_MINUTES = 30
MAX_RETRIES = 3
DELAY_MIN = 1.5  # seconds
DELAY_MAX = 3.5  # seconds

# CSV Configuration
CSV_WRITE_INTERVAL = 500  # Write to CSV every N ZIPs

# Monitoring
LOG_FILE = "logs/scraper_droplet2.log"
MONITOR_PORT = 8081  # Different port from droplet 1

print(f"✅ Loaded config for {DROPLET_NAME}")
print(f"   ZIPs: {ZIP_FILE}")
print(f"   Proxies: {PROXY_HOST}:{PROXY_PORTS[0]}-{PROXY_PORTS[-1]}")
print(f"   Workers: {NUM_WORKERS}")

