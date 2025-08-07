# Scraping API integration for bypassing rate limits on Render
import os
import requests
import logging
from typing import Optional
import json
from urllib.parse import quote

logger = logging.getLogger(__name__)

class ScrapingAPI:
    """
    Generic scraping API integration that works with various services:
    - ScraperAPI
    - Scrapfly
    - ScrapingBee
    - Brightdata
    """
    
    def __init__(self):
        # Try to detect which service based on environment variables
        self.api_key = os.getenv('SCRAPING_API_KEY', '')
        self.api_url = os.getenv('SCRAPING_API_URL', '')
        self.api_type = os.getenv('SCRAPING_API_TYPE', 'scraperapi')  # scraperapi, scrapfly, scrapingbee
        
        if not self.api_key:
            logger.warning("No scraping API key found. Set SCRAPING_API_KEY environment variable.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Scraping API configured: {self.api_type}")
            
            # Set default URLs based on API type
            if not self.api_url:
                if self.api_type == 'scraperapi':
                    self.api_url = 'http://api.scraperapi.com'
                elif self.api_type == 'scrapfly':
                    self.api_url = 'https://api.scrapfly.io/scrape'
                elif self.api_type == 'scrapingbee':
                    self.api_url = 'https://app.scrapingbee.com/api/v1'
                elif self.api_type == 'brightdata':
                    self.api_url = 'https://api.brightdata.com'
                else:
                    self.api_url = 'http://api.scraperapi.com'  # Default
    
    def fetch(self, url: str, **kwargs) -> Optional[str]:
        """Fetch URL using the configured scraping API"""
        if not self.enabled:
            return None
        
        try:
            if self.api_type == 'scraperapi':
                return self._fetch_scraperapi(url, **kwargs)
            elif self.api_type == 'scrapfly':
                return self._fetch_scrapfly(url, **kwargs)
            elif self.api_type == 'scrapingbee':
                return self._fetch_scrapingbee(url, **kwargs)
            else:
                return self._fetch_generic(url, **kwargs)
        except Exception as e:
            logger.error(f"Scraping API error: {e}")
            return None
    
    def _fetch_scraperapi(self, url: str, **kwargs) -> Optional[str]:
        """Fetch using ScraperAPI format"""
        params = {
            'api_key': self.api_key,
            'url': url,
            'render': 'false',  # We don't need JS rendering
            'country_code': kwargs.get('country', 'us'),
        }
        
        try:
            response = requests.get(
                self.api_url,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully fetched via ScraperAPI")
                return response.text
            else:
                logger.error(f"ScraperAPI returned status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"ScraperAPI request failed: {e}")
            return None
    
    def _fetch_scrapfly(self, url: str, **kwargs) -> Optional[str]:
        """Fetch using Scrapfly format"""
        params = {
            'key': self.api_key,
            'url': url,
            'asp': 'true',  # Anti-scraping protection
            'country': kwargs.get('country', 'us'),
            'render_js': 'false',
        }
        
        try:
            response = requests.get(
                self.api_url,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                # Scrapfly returns JSON with the HTML in 'result.content'
                data = response.json()
                html_content = data.get('result', {}).get('content', '')
                if html_content:
                    logger.info(f"Successfully fetched via Scrapfly")
                    return html_content
                return None
            else:
                logger.error(f"Scrapfly returned status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Scrapfly request failed: {e}")
            return None
    
    def _fetch_scrapingbee(self, url: str, **kwargs) -> Optional[str]:
        """Fetch using ScrapingBee format"""
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'false',
            'country_code': kwargs.get('country', 'us'),
        }
        
        try:
            response = requests.get(
                self.api_url,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully fetched via ScrapingBee")
                return response.text
            else:
                logger.error(f"ScrapingBee returned status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"ScrapingBee request failed: {e}")
            return None
    
    def _fetch_generic(self, url: str, **kwargs) -> Optional[str]:
        """Generic API format - customize based on your service"""
        # This is a generic format that might work with custom or unknown APIs
        params = {
            'apikey': self.api_key,
            'url': url,
        }
        
        # Add any additional parameters from kwargs
        params.update(kwargs)
        
        try:
            response = requests.get(
                self.api_url,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully fetched via generic API")
                return response.text
            else:
                logger.error(f"API returned status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Generic API request failed: {e}")
            return None

# Global instance
scraping_api = ScrapingAPI()

def fetch_with_api(url: str) -> Optional[str]:
    """Helper function to fetch URL using scraping API"""
    return scraping_api.fetch(url)