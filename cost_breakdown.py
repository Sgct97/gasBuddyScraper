#!/usr/bin/env python3
"""
CLEAR cost breakdown - bandwidth vs proxy costs
"""

print("="*70)
print("COST BREAKDOWN: curl_cffi Scraping")
print("="*70)

# Measured data
bandwidth_per_zip_kb = 442.21
estimated_zips = 30000
scrapes_per_day = 2
days_per_month = 30

# Calculate bandwidth
bandwidth_per_scrape_gb = (bandwidth_per_zip_kb * estimated_zips) / (1024 * 1024)
bandwidth_per_day_gb = bandwidth_per_scrape_gb * scrapes_per_day
bandwidth_per_month_gb = bandwidth_per_scrape_gb * scrapes_per_day * days_per_month

print(f"\nBANDWIDTH USAGE:")
print(f"  Per ZIP: {bandwidth_per_zip_kb:.2f} KB")
print(f"  Per scrape (30K ZIPs): {bandwidth_per_scrape_gb:.2f} GB")
print(f"  Per day (2 scrapes): {bandwidth_per_day_gb:.2f} GB")
print(f"  Per month (60 scrapes): {bandwidth_per_month_gb:.2f} GB")

print("\n" + "="*70)
print("SCENARIO 1: WITHOUT PROXIES (Direct scraping)")
print("="*70)

# VPS bandwidth costs (most include 1-5TB free)
print("\nVPS Bandwidth Cost:")
print("  • Most VPS include 1-5 TB/month FREE")
print(f"  • We need: {bandwidth_per_month_gb:.0f} GB/month")
print("  • Within free tier? YES! ✅")
print("\n  If bandwidth charged separately:")
print(f"    @ $0.01/GB: ${bandwidth_per_month_gb * 0.01:.2f}/month")
print(f"    @ $0.02/GB: ${bandwidth_per_month_gb * 0.02:.2f}/month")

print("\n" + "="*70)
print("SCENARIO 2: WITH RESIDENTIAL PROXIES")
print("="*70)

print("\n⚠️  PROXIES charge per GB because they're providing RESIDENTIAL IPs")
print("   (Not because of bandwidth - they upcharge for IP rotation)")

proxy_costs = {
    "Budget residential": 3,
    "Standard residential": 10,
    "Premium residential": 15
}

print("\nMonthly Proxy Cost:")
for name, cost_per_gb in proxy_costs.items():
    monthly = bandwidth_per_month_gb * cost_per_gb
    print(f"  {name} @ ${cost_per_gb}/GB: ${monthly:,.2f}/month")

print("\n" + "="*70)
print("THE KEY QUESTION:")
print("="*70)
print("\n❓ Do we NEED proxies?")
print("\n  We've been testing WITHOUT proxies successfully!")
print("  • Cloudflare lets us through")
print("  • No rate limiting yet")
print("  • Could add delays/rotation if needed")
print("\n  If we DON'T need proxies:")
print(f"    Cost = VPS only = ~$28-56/month (from earlier)")
print("\n  If we DO need proxies:")
print(f"    Cost = VPS + $2,277-11,387/month = OUCH 💸")

print("\n" + "="*70)
print("RECOMMENDATION:")
print("="*70)
print("\n1. Build scraper with proxy SUPPORT but don't use by default")
print("2. Start WITHOUT proxies on your home server")
print("3. Monitor for rate limits/blocks")
print("4. Add proxies ONLY if needed")
print("\n💡 Let's prove we DON'T need proxies before spending $2K+/month!")
print("="*70)

