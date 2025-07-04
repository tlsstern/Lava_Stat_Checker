# Lava_Stat_Checker/scrapper.py
import requests
from bs4 import BeautifulSoup
import re
import json
import logging
import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

MAX_RETRIES = 3
RETRY_DELAY = 5

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

def scrape_bedwars_stats(username):
    driver = None
    try:
        driver = get_driver()
        url = f"https://bwstats.shivam.pro/user/{username}"
        retries = 0
        while retries < MAX_RETRIES:
            try:
                logger.info(f"Attempt {retries + 1}/{MAX_RETRIES} for {username} using Selenium")
                driver.get(url)

                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                if "Player not found" in driver.page_source:
                    logger.warning(f"Player not found: {username}")
                    return {"username": username, "error": "Player not found"}

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                stats = {
                    "username": username,
                    "star": None,
                    "most_played": None
                }
                
                title_elem = soup.find('title')
                if title_elem:
                    title_text = title_elem.text
                    match = re.search(r'\b(\d+)\b', title_text, re.I)
                    if match:
                        stats["star"] = int(match.group(1))
                
                summary_section = soup.find(string=re.compile(r'preferred mode is', re.I))
                if summary_section:
                    most_played_match = re.search(r'preferred mode is\s*(\w+)', summary_section, re.I)
                    if most_played_match:
                        stats["most_played"] = most_played_match.group(1)

                table = soup.find('table')
                if not table:
                    raise ValueError("Main stats table not found in HTML")
                
                table_data = {}
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        label = cells[0].text.strip()
                        value = cells[1].text.strip()
                        table_data[label] = value

                stats.update(table_data)
                
                logger.info(f"Successfully scraped stats for {username}")
                return stats

            except Exception as e:
                logger.warning(f"Error for {username}: {e}")
                retries += 1
                if retries < MAX_RETRIES:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Max retries reached for {username}. Skipping.")
                    return {"username": username, "error": f"Failed after {MAX_RETRIES} attempts: {e}"}

    finally:
        if driver:
            driver.quit()

def scrape_bwstats(username):
    return scrape_bedwars_stats(username)