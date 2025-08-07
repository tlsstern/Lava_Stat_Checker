# Lava_Stat_Checker/scrapper.py
import requests
from bs4 import BeautifulSoup
import re
import logging
import datetime
import json
import os
from concurrent.futures import ThreadPoolExecutor
import time
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CACHE_DIR = "./cache"
CACHE_DURATION = 900  # 15 minutes

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

# Create a session for connection pooling
session = requests.Session()
session.headers.update({
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
})

def get_cache_path():
    today_str = datetime.datetime.now().strftime("%d_%m_%Y")
    return os.path.join(CACHE_DIR, f"cache_{today_str}.json")

def fetch_page(username, retry_count=5):
    """Fetch page using requests with retries and different user agents"""
    url = f"https://bwstats.shivam.pro/user/{username}"
    
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
    ]
    
    for attempt in range(retry_count):
        try:
            # Use session with rotating user agents
            headers = {'User-Agent': random.choice(user_agents)}
            
            response = session.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                logger.info(f"Successfully fetched page for {username}")
                return response.text
            elif response.status_code == 404:
                logger.warning(f"Player not found (404): {username}")
                return None
            elif response.status_code == 429:
                # Rate limited - use longer exponential backoff
                wait_time = (3 ** attempt) * 2 + random.uniform(0, 2)
                logger.warning(f"Rate limited (429) for {username}. Waiting {wait_time:.1f}s before retry {attempt + 1}/{retry_count}")
                if attempt < retry_count - 1:
                    time.sleep(wait_time)
            else:
                logger.warning(f"Attempt {attempt + 1} failed with status {response.status_code} for {username}")
                if attempt < retry_count - 1:
                    time.sleep(3 + random.uniform(0, 2))
                    
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1} for {username}")
            if attempt < retry_count - 1:
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1} for {username}: {e}")
            if attempt < retry_count - 1:
                time.sleep(5)
    
    logger.error(f"All {retry_count} attempts failed for {username}")
    return None

def parse_stats_from_html(html_content, username):
    """Parse stats from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Check for player not found
    if "Player not found" in html_content:
        logger.warning(f"Player not found: {username}")
        return {"error": "Player not found"}
    
    data = {'username': username, 'modes': {}}
    
    # Find the stats table
    table = soup.find('table')
    if not table:
        # Try to find table with specific class or id if direct search fails
        table = soup.find('table', class_='stats-table') or soup.find('div', class_='stats').find('table') if soup.find('div', class_='stats') else None
        
    if not table:
        logger.error(f"Stats table not found for {username}")
        return {"error": "Stats table not found"}
    
    rows = table.find_all('tr')
    if not rows:
        return {"error": "Table has no rows"}
    
    # Parse header to get game modes
    header_cells = rows[0].find_all(['th', 'td'])
    modes_list = [cell.get_text(strip=True) for cell in header_cells[1:]] 
    
    mode_key_map = {
        'Overall': 'overall', 
        'Solo': 'solos', 
        'Doubles': 'doubles', 
        '3v3v3v3': 'threes', 
        '4v4v4v4': 'fours', 
        '4v4': '4v4'
    }
    
    # Initialize mode dictionaries
    for mode_name in modes_list:
        mode_key = mode_key_map.get(mode_name)
        if mode_key:
            data['modes'][mode_key] = {}
    
    # Map stat names to keys
    stat_key_map = {
        'Games Played': 'games_played',
        'Wins': 'wins',
        'Losses': 'losses',
        'Win/Loss Ratio': 'wlr',
        'Kills': 'kills',
        'Deaths': 'deaths',
        'K/D Ratio (KDR)': 'kdr',
        'Final Kills': 'final_kills',
        'Final Deaths': 'final_deaths',
        'Final K/D Ratio (FKDR)': 'fkdr',
        'Beds Broken': 'beds_broken',
        'Beds Lost': 'beds_lost',
        'Beds B/L Ratio (BBLR)': 'bblr',
        'Winstreak': 'winstreak',
        'Items Purchased': 'items_purchased'
    }
    
    # Parse stats rows
    for row in rows[1:]:
        cells = row.find_all('td')
        if not cells:
            continue
        
        stat_name_raw = cells[0].get_text(strip=True)
        stat_key = stat_key_map.get(stat_name_raw)
        
        if stat_key:
            for i, value_cell in enumerate(cells[1:]):
                if i < len(modes_list):
                    mode_name = modes_list[i]
                    mode_key = mode_key_map.get(mode_name)
                    if mode_key and mode_key in data['modes']:
                        value = value_cell.get_text(strip=True)
                        data['modes'][mode_key][stat_key] = value
    
    # Try to extract star level from title
    title_elem = soup.find('title')
    if title_elem:
        title_text = title_elem.text
        # Look for star level in title (e.g., "100✫ username - BedWars Stats")
        match = re.search(r'\b(\d+)[✫⭐]\b|\b(\d+)\s*star', title_text, re.I)
        if match:
            star_value = match.group(1) or match.group(2)
            data["star"] = int(star_value)
        else:
            # Try to find star level elsewhere in the page
            star_elem = soup.find(text=re.compile(r'\d+[✫⭐]'))
            if star_elem:
                match = re.search(r'(\d+)[✫⭐]', star_elem)
                if match:
                    data["star"] = int(match.group(1))
    
    data['last_updated'] = datetime.datetime.utcnow().isoformat()
    data['fetched_by'] = 'scrapper'
    
    return data

def scrape_bwstats(username):
    """Main function to scrape stats for a single user"""
    cache_path = get_cache_path()
    all_cached_data = {}

    # Load existing cache
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                all_cached_data = json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Error reading cache file: {e}. Starting with empty cache.")
            all_cached_data = {}

    # Check cache for user
    user_cached_data = all_cached_data.get(username.lower())
    if user_cached_data:
        last_updated_str = user_cached_data.get('last_updated')
        if last_updated_str:
            try:
                last_updated_dt = datetime.datetime.fromisoformat(last_updated_str)
                if (datetime.datetime.utcnow() - last_updated_dt).total_seconds() < CACHE_DURATION:
                    logger.info(f"Returning cached data for {username}")
                    return user_cached_data
                else:
                    logger.info(f"Cached data for {username} is stale. Re-scraping.")
            except ValueError:
                logger.warning(f"Invalid timestamp for {username}. Re-scraping.")

    # Fetch fresh data
    logger.info(f"Fetching stats for {username}")
    html_content = fetch_page(username)
    
    if not html_content:
        logger.error(f"Failed to fetch page for {username}")
        return {"error": "Failed to fetch player stats"}
    
    # Parse the HTML
    result = parse_stats_from_html(html_content, username)
    
    # Save to cache if successful
    if "error" not in result:
        all_cached_data[username.lower()] = result
        try:
            with open(cache_path, 'w') as f:
                json.dump(all_cached_data, f, indent=4)
            logger.info(f"Saved data to cache for {username}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    return result

def scrape_multiple_bwstats(usernames):
    """Scrape multiple users concurrently with rate limiting"""
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Add small delay between submissions to avoid rate limiting
        results = []
        futures = []
        for username in usernames:
            future = executor.submit(scrape_bwstats, username)
            futures.append(future)
            time.sleep(0.5)  # Small delay between requests
        
        results = [future.result() for future in futures]
    return dict(zip(usernames, results))

# Compatibility functions for cleanup (no-op since we don't use drivers)
def cleanup_drivers():
    """No cleanup needed - keeping for compatibility"""
    pass

def return_driver_to_pool(driver):
    """No-op - keeping for compatibility"""
    pass