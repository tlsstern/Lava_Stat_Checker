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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_bwstats(username):
    driver = None
    try:
        driver = get_driver()
        url = f"https://bwstats.shivam.pro/user/{username}"
        logger.info(f"Scraping {url} for {username}")
        driver.get(url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find the main stats table
        table = soup.find('table')
        if not table:
             if "Player not found" in driver.page_source:
                 logger.warning(f"Player not found on bwstats: {username}")
                 return {"error": "Player not found"}
             raise ValueError("Stats table not found")

        data = {'username': username, 'modes': {}}
        
        # --- Parse the detailed table ---
        rows = table.find_all('tr')
        if not rows:
            raise ValueError("Table has no rows")
            
        # First row is the header with mode names
        header_cells = rows[0].find_all(['th', 'td'])
        modes_list = [cell.get_text(strip=True) for cell in header_cells[1:]] 
        
        mode_key_map = {
            'Overall': 'overall', 'Solo': 'solos', 'Doubles': 'doubles', 
            '3v3v3v3': 'threes', '4v4v4v4': 'fours', '4v4': '4v4'
        }

        # Initialize the nested dictionary for each mode found in the header
        for mode_name in modes_list:
            mode_key = mode_key_map.get(mode_name)
            if mode_key:
                data['modes'][mode_key] = {}

        # Iterate over the rest of the rows for stats
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
                # Get values for each mode in that row
                for i, value_cell in enumerate(cells[1:]):
                    if i < len(modes_list): # Ensure we don't go out of bounds
                        mode_name = modes_list[i]
                        mode_key = mode_key_map.get(mode_name)
                        if mode_key and mode_key in data['modes']:
                            data['modes'][mode_key][stat_key] = value_cell.get_text(strip=True)
        
        # Extract star from title, as it's not in the table
        title_elem = soup.find('title')
        if title_elem:
            title_text = title_elem.text
            match = re.search(r'\b(\d+)\b', title_text, re.I)
            if match:
                data["star"] = int(match.group(1))

        logger.info(f"Successfully scraped detailed stats for {username}")
        return data

    except Exception as e:
        logger.error(f"An error occurred while scraping bwstats for {username}: {e}", exc_info=True)
        return {"error": "Failed to scrape player stats."}
    finally:
        if driver:
            driver.quit()