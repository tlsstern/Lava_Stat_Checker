# Scraping API Setup Guide

Due to Render's IP addresses being rate-limited by bwstats.shivam.pro, you can use a scraping API service to bypass this limitation.

## Supported Services

The app supports multiple scraping API services:

1. **ScraperAPI** (Recommended)
2. **Scrapfly**
3. **ScrapingBee**
4. **Brightdata**
5. **Custom/Generic APIs**

## Setup Instructions

### Step 1: Choose a Service

Pick one of these services (they all offer free trials):

- [ScraperAPI](https://www.scraperapi.com/) - 5,000 free requests/month
- [Scrapfly](https://scrapfly.io/) - 1,000 free requests/month
- [ScrapingBee](https://www.scrapingbee.com/) - 1,000 free requests/month

### Step 2: Get an API Key

1. Sign up for your chosen service
2. Get your API key from the dashboard
3. Note the service name

### Step 3: Configure on Render

Add these environment variables to your Render service:

```bash
# Required
SCRAPING_API_KEY=your_api_key_here

# API Type (choose one)
SCRAPING_API_TYPE=scraperapi  # or 'scrapfly', 'scrapingbee', etc.

# Optional - Custom API URL (if using a different service)
SCRAPING_API_URL=https://api.yourservice.com

# Optional - Force API usage even locally
USE_SCRAPING_API=true
```

### Step 4: Deploy

Once configured, the app will automatically:
1. Use the scraping API when running on Render
2. Fall back to direct requests if API fails
3. Use Supabase cache when available

## Example Configurations

### ScraperAPI
```env
SCRAPING_API_KEY=abc123xyz
SCRAPING_API_TYPE=scraperapi
```

### Scrapfly
```env
SCRAPING_API_KEY=scp-live-abc123xyz
SCRAPING_API_TYPE=scrapfly
```

### ScrapingBee
```env
SCRAPING_API_KEY=ABC123XYZ
SCRAPING_API_TYPE=scrapingbee
```

### Custom API
```env
SCRAPING_API_KEY=your_key
SCRAPING_API_TYPE=custom
SCRAPING_API_URL=https://your-api.com/scrape
```

## Testing

To test if your API is working:

1. Set the environment variables
2. Deploy to Render
3. Try searching for a player
4. Check the logs for "Successfully fetched via Scraping API"

## Cost Considerations

- Most services offer 1,000-5,000 free requests per month
- Each player search = 1 API request (if not cached)
- Cached data doesn't use API requests
- Consider implementing request limits if needed

## Troubleshooting

If the API isn't working:

1. Check your API key is correct
2. Verify you have remaining credits
3. Check the Render logs for error messages
4. Ensure the SCRAPING_API_TYPE matches your service
5. Try setting USE_SCRAPING_API=true to force API usage

## Alternative Solutions

If you don't want to use a scraping API:

1. **Deploy elsewhere**: Try Vercel, Railway, or Fly.io
2. **Use a VPS**: Deploy on a clean IP (DigitalOcean, Linode, etc.)
3. **Proxy server**: Set up your own proxy on a different server
4. **Cache-only mode**: Rely entirely on Supabase cache