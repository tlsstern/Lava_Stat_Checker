# cacher.py
import sys
import time
import itertools
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path to allow imports of other modules like scrapper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import scrapper
import logging

# Configure logging to see output from the imported modules
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PLAYER_LISTS = {
    "priority": list(dict.fromkeys([
        "Legitimate", "lelitzpanda", "Genzio", "P0tCounter", "zNotDiamond", "FrostyCookies", "Tristtann", "Zyckin",
        "thighteen", "holye", "devilmades", "jacks", "juulhoodlum", "stylishducks", "Timness",
        "SnipersDaikirai", "Nebsi", "shwane", "UncleFecu", "louieyay", "oTigerAlt", "frenchifydread", "_GZP",
        "DreadOP"
        
    ])),
    "legit": list(dict.fromkeys([
        "Wlnks", "QtSpoopy", "NoSDaemon", "Jqsie", "RRG_", "wact", "Genzio", "PVP_FAC", "PRAXZZ", "Seifig",
        "zNotDiamond", "Legitimate", "lelitzpanda", "tiltingsson", "Emmily", "recipebook", "Kohvy", "ausm",
        "oTeda", "R0NZI", "zaymie", "K1N00", "kermit80", "Hollowjack40", "hourrr", "aubrdan", "Linkze",
        "Andorite", "zock_zock", "OGlightning", "DUALLISTE", "P0tCounter"
    ])),
    "closet_boosted": list(dict.fromkeys([
        "543231", "lolZiad", "MasterZane1469", "devilmades", "TeddyTNT", "zedrico", "cwc5", "Lolbit", "kalmxd",
        "DreadOP", "exoyay", "louieyay", "F1nalist", "Nebsi", "Eilens", "horable", "SJOD",  "Tuxsy",
        "oTigerAlt", "jcks", "Ke1eum", "holye", "Zooat", "ChickenX7_TV", "Timness", "thwea", "MasterMorro9617",
        "KINGPINGATRO", "Chemby", "kutvo", "bipy", "SMKCB", "Daringss", "shwane", "dercani", "majestic0s",
        "Cozer", "UnkNoWn_B0t_347", "Leshl", "cohata", "goodone_", "PookieBear", "YAYPERF", "blaaau", "pand6ra",
        "stylishducks", "SnipersDaikirai", "Reflets", "CRASHOUTJAY", "vwvwvwwvwv", "DogAgent", "shykitty26",
        "Speedy596", "Pianoism", "UncleFecu", "icyless", "lNASIA", "Elapse", "Vernation", "juulhoodlum",
        "Tawber", "OnionRing_"
    ])),
    "stat_alts": list(dict.fromkeys([
        "AtlasSly", "WINSTREAKDENNIS", "sadbunny23", "FreeDlup", "ChickenX7", "thuggathugga1017", "headuptwin",
        "Samayea", "Seraca", "AliMoussaAlHarbi", "TariqAlHarzi", "PapasitoRax", "relts", "ignbridge", "laszr",
        "frenchifydread", "UnkNoWn_Bot_324", "SophiaArnold2002", "DictateurMidas", "AbuHafsAlHashimi",
        "Jerkifi", "airbus1234", "xxxIslaxxx", "shykitty27", "Zehqa", "t7ny", "blackairbus", "icehaha",
        "femboysedating", "edatingfemboys", "beddefgrape", "evolebn", "GlossyMan", "JaxonJazzyPants"
    ])),
    "inactive": list(dict.fromkeys([
        "B0MBIES", "LujanCarrion", "Disused", "vcmpi", "volisy", "lvlasap", "Mujadara", "kalmx_x", "COCFKDR",
        "revilty", "icex_x", "Reyadh", "joltierxd", "lolRax", "ibzilol", "Panguinson", "initializes",
        "loveisntreal", "AkirEra", "meowBalu", "bbukk", "nya1208", "MasterKai5369", "Dlup", "UhAsmo",
        "SUPERSTARMIDAS", "COOK1eBear", "xZiad", "PotCounter", "yay18", "GloriousCatWS", "xXGloriousCatXx"
    ]))
}

def fetch_and_cache(username):
    """Wrapper function to fetch player data using the scrapper."""
    logger.info(f"Requesting data for {username} via scrapper...")
    result = scrapper.scrape_bwstats(username)
    if result and not result.get('error'):
        # The scrapper implicitly caches the data, so we just log success.
        logger.info(f"Successfully processed and cached {username} via scrapper.")
        return f"Success: {username} (scrapper)"
    elif result and result.get('error'):
        error_msg = result.get('error')
        logger.error(f"Failed to process {username}. Error: {error_msg}")
        return f"Failed: {username} ({error_msg})"
    else:
        logger.error(f"Failed to process {username}. Unknown error from scrapper.")
        return f"Failed: {username} (Unknown)"

def main():
    """Main function to run the caching process."""
    start_time = time.time()

    # Combine all lists and get unique usernames
    all_usernames = list(itertools.chain.from_iterable(PLAYER_LISTS.values()))
    unique_usernames = sorted(list(dict.fromkeys(all_usernames)), key=str.lower)
    
    total_users = len(unique_usernames)
    logger.info(f"Starting cache process for {total_users} unique users.")

    # Use ThreadPoolExecutor for concurrent fetching
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_user = {executor.submit(fetch_and_cache, user): user for user in unique_usernames}
        
        processed_count = 0
        for future in as_completed(future_to_user):
            user = future_to_user[future]
            try:
                result_message = future.result()
                print(result_message)
            except Exception as exc:
                print(f"{user} generated an exception: {exc}")
            
            processed_count += 1
            print(f"Progress: {processed_count}/{total_users}", end='\r')

    end_time = time.time()
    logger.info(f"\nCaching process finished in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()