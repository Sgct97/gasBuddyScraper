# What We've ACTUALLY Proven

## ✅ Confirmed Facts:

### 1. Data Location
- Station data is in `window.__APOLLO_STATE__` in HTML
- First page shows ~20 stations (no pagination needed for small ZIPs)

### 2. "More" Button Behavior  
- Clicking "more" makes POST to `/graphql`
- Uses `operationName: "LocationBySearchTerm"`
- Passes `cursor: "20"` for next page
- Returns more stations in JSON

### 3. Rate Limiting
- HTML requests get 403/429 after ~15-20 requests
- Even Playwright (real browser) gets rate limited
- **This proves proxies ARE needed for production scale**

### 4. Headers in Working Request
Browser sends these when clicking "more":
```
gbcsrf: 1.Z0y9kkk939pT+lfE  (CSRF token from HTML)
apollo-require-preflight: true
content-type: application/json
referer: https://www.gasbuddy.com/home?search=77494
```

## ❌ What We HAVEN'T Proven:

### Can we replicate the GraphQL call ourselves?
- Direct GraphQL calls: **400 Bad Request** (even with all headers + session + csrf)
- Playwright fetch(): **403 Forbidden** (rate limited before we could test)
- **Status: UNKNOWN** - need to wait for rate limit to clear

### Does pagination work end-to-end?
- We saw cursor="20" work in browser
- We DON'T know if cursor="40" works, or how many pages needed for ZIP 77494 (34 stations)
- **Status: NEEDS TESTING**

## 🤔 Open Questions:

1. **Why do our GraphQL calls get 400?**
   - Missing some header/cookie?
   - Need to click button vs call API?
   - Browser fingerprinting?

2. **What's the best scraping approach?**
   - Option A: HTML-only with cursor parameter (`?search=77494&cursor=20`)
   - Option B: HTML + GraphQL API (if we can make it work)
   - Option C: Full Playwright automation (click buttons for real)

3. **How many requests per full scrape?**
   - ~42,000 US ZIP codes
   - Average X requests per ZIP (depends on pagination)
   - Need to test sample of ZIPs to estimate

## 🎯 Next Steps:

1. **Wait for rate limit to clear** (maybe 1-2 hours?)
2. **Test if actual button click works** (vs programmatic fetch)
3. **If button click works**: Full Playwright scraper
4. **If button click fails**: Back to HTML-only approach
5. **Small-scale test**: 10-20 ZIPs to prove it works
6. **Then**: Full production scraper with proxies

## 💰 Token Conservation:

- Stop making assumptions
- Test ONE thing at a time
- Wait for rate limits instead of burning tokens on 400 errors
- Document what we KNOW vs what we THINK

