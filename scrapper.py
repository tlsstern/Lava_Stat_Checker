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
from typing import Optional, Dict, Any

# Try to use cloudscraper if available, fallback to requests
try:
    import cloudscraper
    scraper = cloudscraper.create_scraper()
    logger_msg = "Using cloudscraper for requests"
except ImportError:
    scraper = requests.Session()
    scraper.headers.update({
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
    logger_msg = "Using requests.Session"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info(logger_msg)

# Import Supabase handler for caching
try:
    from supabase_handler import SupabaseHandler
    supabase = SupabaseHandler()
    logger.info("Supabase handler initialized for caching")
except Exception as e:
    logger.warning(f"Could not initialize Supabase handler: {e}")
    supabase = None

# Keep old cache settings for fallback
CACHE_DIR = "./cache"
CACHE_DURATION = 900  # 15 minutes in seconds
USE_SUPABASE_CACHE = supabase is not None and supabase.client is not None

# Ensure cache directory exists (fallback)
if not USE_SUPABASE_CACHE:
    os.makedirs(CACHE_DIR, exist_ok=True)
    logger.info("Using local file cache (Supabase not available)")
else:
    logger.info("Using Supabase for caching")

# Keep session for backwards compatibility
session = scraper

def get_cache_path():
    """Get local cache file path (fallback only)"""
    today_str = datetime.datetime.now().strftime("%d_%m_%Y")
    return os.path.join(CACHE_DIR, f"cache_{today_str}.json")

def fetch_page(username, retry_count=3):
    """Fetch page using scraper with retries"""
    url = f"https://bwstats.shivam.pro/user/{username}"
    
    for attempt in range(retry_count):
        try:
            # cloudscraper handles user agents and anti-bot measures automatically
            response = scraper.get(url, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Successfully fetched page for {username}")
                return response.text
            elif response.status_code == 404:
                logger.warning(f"Player not found (404): {username}")
                return None
            elif response.status_code == 429:
                # Rate limited - use exponential backoff
                wait_time = (2 ** attempt) * 3 + random.uniform(1, 3)
                logger.warning(f"Rate limited (429) for {username}. Waiting {wait_time:.1f}s before retry {attempt + 1}/{retry_count}")
                if attempt < retry_count - 1:
                    time.sleep(wait_time)
            else:
                logger.warning(f"Attempt {attempt + 1} failed with status {response.status_code} for {username}")
                if attempt < retry_count - 1:
                    time.sleep(2 + random.uniform(0, 1))
                    
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1} for {username}")
            if attempt < retry_count - 1:
                time.sleep(3)
        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1} for {username}: {e}")
            if attempt < retry_count - 1:
                time.sleep(3)
    
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

def check_supabase_cache(username: str) -> Optional[Dict[str, Any]]:
    """Check Supabase for cached stats"""
    if not USE_SUPABASE_CACHE:
        return None
    
    try:
        # Check Supabase cache (15 minutes = 0.25 hours)
        cached_stats = supabase.get_cached_stats(username, max_age_hours=0.25)
        if cached_stats:
            logger.info(f"Found cached stats in Supabase for {username}")
            # Convert Supabase format back to scraper format
            return convert_supabase_to_scraper_format(cached_stats)
        return None
    except Exception as e:
        logger.error(f"Error checking Supabase cache: {e}")
        return None

def save_to_supabase(username: str, stats_data: Dict[str, Any]):
    """Save scraped stats to Supabase"""
    if not USE_SUPABASE_CACHE or 'error' in stats_data:
        return
    
    try:
        supabase.save_stats(username, stats_data, fetched_from="scraper")
        logger.info(f"Saved stats to Supabase for {username}")
    except Exception as e:
        logger.error(f"Error saving to Supabase: {e}")

def convert_supabase_to_scraper_format(supabase_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Supabase stats format back to scraper format"""
    try:
        # Parse detailed_stats if it's a JSON string
        detailed_stats = supabase_stats.get('detailed_stats', {})
        if isinstance(detailed_stats, str):
            detailed_stats = json.loads(detailed_stats)
        
        # If detailed stats has the full scraper format, return it
        if 'modes' in detailed_stats:
            return detailed_stats
        
        # Otherwise, reconstruct from basic stats
        return {
            'username': supabase_stats.get('player_name', ''),
            'star': supabase_stats.get('level', 0),
            'modes': {
                'overall': {
                    'wins': str(supabase_stats.get('wins', 0)),
                    'losses': str(supabase_stats.get('losses', 0)),
                    'wlr': str(supabase_stats.get('wlr', 0)),
                    'final_kills': str(supabase_stats.get('finals', 0)),
                    'final_deaths': str(supabase_stats.get('final_deaths', 0)),
                    'fkdr': str(supabase_stats.get('fkdr', 0)),
                    'beds_broken': str(supabase_stats.get('beds_broken', 0)),
                    'beds_lost': str(supabase_stats.get('beds_lost', 0)),
                    'bblr': str(supabase_stats.get('bblr', 0)),
                    'kills': str(supabase_stats.get('kills', 0)),
                    'deaths': str(supabase_stats.get('deaths', 0)),
                    'kdr': str(supabase_stats.get('kdr', 0))
                }
            },
            'last_updated': supabase_stats.get('updated_at', datetime.datetime.utcnow().isoformat()),
            'fetched_by': 'scrapper'
        }
    except Exception as e:
        logger.error(f"Error converting Supabase format: {e}")
        return None

def check_local_cache(username: str) -> Optional[Dict[str, Any]]:
    """Check local file cache (fallback when Supabase not available)"""
    cache_path = get_cache_path()
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, 'r') as f:
            all_cached_data = json.load(f)
        
        user_cached_data = all_cached_data.get(username.lower())
        if user_cached_data:
            last_updated_str = user_cached_data.get('last_updated')
            if last_updated_str:
                try:
                    last_updated_dt = datetime.datetime.fromisoformat(last_updated_str)
                    if (datetime.datetime.utcnow() - last_updated_dt).total_seconds() < CACHE_DURATION:
                        logger.info(f"Returning cached data from file for {username}")
                        return user_cached_data
                except ValueError:
                    pass
    except Exception as e:
        logger.error(f"Error reading local cache: {e}")
    
    return None

def save_to_local_cache(username: str, stats_data: Dict[str, Any]):
    """Save to local file cache (fallback)"""
    if 'error' in stats_data:
        return
    
    cache_path = get_cache_path()
    all_cached_data = {}
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                all_cached_data = json.load(f)
        except:
            pass
    
    all_cached_data[username.lower()] = stats_data
    
    try:
        with open(cache_path, 'w') as f:
            json.dump(all_cached_data, f, indent=4)
        logger.info(f"Saved to local cache for {username}")
    except Exception as e:
        logger.error(f"Failed to save local cache: {e}")

def scrape_bwstats(username):
    """Main function to scrape stats for a single user"""
    
    # Check Supabase cache first
    if USE_SUPABASE_CACHE:
        cached_data = check_supabase_cache(username)
        if cached_data:
            return cached_data
    else:
        # Fallback to local cache if Supabase not available
        cached_data = check_local_cache(username)
        if cached_data:
            return cached_data
    
    # Fetch fresh data
    logger.info(f"Fetching fresh stats for {username}")
    html_content = fetch_page(username)
    
    if not html_content:
        logger.error(f"Failed to fetch page for {username}")
        return {"error": "Failed to fetch player stats"}
    
    # Parse the HTML
    result = parse_stats_from_html(html_content, username)
    
    # Save to appropriate cache
    if "error" not in result:
        if USE_SUPABASE_CACHE:
            save_to_supabase(username, result)
        else:
            save_to_local_cache(username, result)
    
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