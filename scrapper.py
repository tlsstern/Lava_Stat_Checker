# Lava_Stat_Checker/scrapper.py
import requests
from bs4 import BeautifulSoup
import re
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import datetime
import platform
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CACHE_DIR = "./cache"
CACHE_DURATION = 3600 # Cache for 1 hour (3600 seconds)
driver_pool = []
driver_lock = threading.Lock()
MAX_DRIVERS = 3

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path():
    today_str = datetime.datetime.now().strftime("%d_%m_%Y")
    return os.path.join(CACHE_DIR, f"cache_{today_str}.json")

def get_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.page_load_strategy = 'eager'
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Additional options for containerized environments
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--disable-dev-tools")
    
    if platform.system() == "Windows":
        chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    else:
        # Try multiple possible Chrome locations
        chrome_paths = [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/opt/google/chrome/google-chrome",
            "/usr/local/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/app/.apt/usr/bin/google-chrome-stable",  # Render's apt buildpack location
            "/app/.apt/usr/bin/google-chrome"
        ]
        chrome_found = False
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_options.binary_location = path
                chrome_found = True
                logger.info(f"Chrome found at: {path}")
                break
        
        if not chrome_found:
            logger.warning("Chrome binary not found in standard locations. Will try without explicit path.")
    
    return chrome_options

def get_driver_from_pool():
    with driver_lock:
        if driver_pool:
            return driver_pool.pop()
        elif len(driver_pool) < MAX_DRIVERS:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=get_chrome_options())
            return driver
    return None

def return_driver_to_pool(driver):
    with driver_lock:
        if len(driver_pool) < MAX_DRIVERS:
            driver_pool.append(driver)
        else:
            driver.quit()

def try_requests_first(username):
    """Try to fetch data using requests first (much faster than Selenium)"""
    try:
        url = f"https://bwstats.shivam.pro/user/{username}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if we got the full page with stats
            table = soup.find('table')
            if table:
                logger.info(f"Successfully fetched {username} data with requests (fast mode)")
                return parse_stats_from_soup(soup, username)
        
        return None
    except Exception as e:
        logger.debug(f"Requests method failed for {username}, will use Selenium: {e}")
        return None

def parse_stats_from_soup(soup, username):
    """Parse stats from BeautifulSoup object"""
    data = {'username': username, 'modes': {}}
    
    table = soup.find('table')
    if not table:
        return {"error": "Stats table not found"}
    
    rows = table.find_all('tr')
    if not rows:
        return {"error": "Table has no rows"}
    
    header_cells = rows[0].find_all(['th', 'td'])
    modes_list = [cell.get_text(strip=True) for cell in header_cells[1:]] 
    
    mode_key_map = {
        'Overall': 'overall', 'Solo': 'solos', 'Doubles': 'doubles', 
        '3v3v3v3': 'threes', '4v4v4v4': 'fours', '4v4': '4v4'
    }
    
    for mode_name in modes_list:
        mode_key = mode_key_map.get(mode_name)
        if mode_key:
            data['modes'][mode_key] = {}
    
    stat_key_map = {
        'Games Played': 'games_played', 'Wins': 'wins', 'Losses': 'losses',
        'Win/Loss Ratio': 'wlr', 'Kills': 'kills', 'Deaths': 'deaths',
        'K/D Ratio (KDR)': 'kdr', 'Final Kills': 'final_kills',
        'Final Deaths': 'final_deaths', 'Final K/D Ratio (FKDR)': 'fkdr',
        'Beds Broken': 'beds_broken', 'Beds Lost': 'beds_lost',
        'Beds B/L Ratio (BBLR)': 'bblr', 'Winstreak': 'winstreak',
        'Items Purchased': 'items_purchased'
    }
    
    for row in rows[1:]:
        cells = row.find_all('td')
        if not cells: continue
        
        stat_name_raw = cells[0].get_text(strip=True)
        stat_key = stat_key_map.get(stat_name_raw)
        
        if stat_key:
            for i, value_cell in enumerate(cells[1:]):
                if i < len(modes_list):
                    mode_name = modes_list[i]
                    mode_key = mode_key_map.get(mode_name)
                    if mode_key and mode_key in data['modes']:
                        data['modes'][mode_key][stat_key] = value_cell.get_text(strip=True)
    
    title_elem = soup.find('title')
    if title_elem:
        title_text = title_elem.text
        match = re.search(r'\b(\d+)\b', title_text, re.I)
        if match:
            data["star"] = int(match.group(1))
    
    data['last_updated'] = datetime.datetime.utcnow().isoformat()
    return data

def scrape_bwstats(username):
    cache_path = get_cache_path()
    all_cached_data = {}

    # Load existing cache data if available
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                all_cached_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted daily cache file: {e}. Starting with empty cache.")
            all_cached_data = {} # Start fresh if corrupted
        except Exception as e:
            logger.warning(f"Error reading daily cache file: {e}. Starting with empty cache.")
            all_cached_data = {}

    # Check for specific user's cached data
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
                logger.warning(f"Invalid 'last_updated' timestamp for {username}. Re-scraping.")
        else:
            logger.warning(f"Cached data for {username} missing 'last_updated' timestamp. Re-scraping.")

    # Try fast method first
    result = try_requests_first(username)
    if result and "error" not in result:
        # Save to cache before returning
        cache_path = get_cache_path()
        all_cached_data[username.lower()] = result
        with open(cache_path, 'w') as f:
            json.dump(all_cached_data, f, indent=4)
        logger.info(f"Saved scraped data to cache for {username} (fast mode)")
        return result
    
    # Fallback to Selenium if requests failed
    driver = None
    try:
        driver = get_driver_from_pool()
        if not driver:
            # Create new driver if pool is exhausted
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=get_chrome_options())
        
        url = f"https://bwstats.shivam.pro/user/{username}"
        logger.info(f"Using Selenium for {url} (fallback mode)")
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Check for player not found
        if "Player not found" in driver.page_source:
            logger.warning(f"Player not found on bwstats: {username}")
            return {"error": "Player not found"}
        
        data = parse_stats_from_soup(soup, username)
        if "error" in data:
            return data

        # Save to cache before returning
        data['last_updated'] = datetime.datetime.utcnow().isoformat()
        all_cached_data[username.lower()] = data
        with open(cache_path, 'w') as f:
            json.dump(all_cached_data, f, indent=4)
        logger.info(f"Saved scraped data to cache for {username}")

        return data

    except Exception as e:
        logger.error(f"An error occurred while scraping bwstats for {username}: {e}", exc_info=True)
        return {"error": "Failed to scrape player stats."}
    finally:
        if driver:
            return_driver_to_pool(driver)

def scrape_multiple_bwstats(usernames):
    """Scrape multiple users concurrently for better performance"""
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(scrape_bwstats, usernames))
    return dict(zip(usernames, results))

def cleanup_drivers():
    """Clean up driver pool when done"""
    with driver_lock:
        while driver_pool:
            driver = driver_pool.pop()
            driver.quit()