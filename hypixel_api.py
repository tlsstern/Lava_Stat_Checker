# hypixel_api.py
import requests
import math
from config import API_KEY
import time

BASE_URL = "https://api.hypixel.net/v2"
PLAYER_URL = f"{BASE_URL}/player"
UUID_URL = "https://api.mojang.com/users/profiles/minecraft/"

# --- Helper Functions (get_bedwars_level, get_player_uuid_by_current_name, get_uuid_by_historical_name - unchanged) ---

def get_bedwars_level(exp: int):
    # (Keep existing get_bedwars_level function - unchanged)
    if not isinstance(exp, int) or exp < 0:
        return 0.0
    level = 100 * (exp // 487000)
    exp = exp % 487000
    if exp < 500: return level + exp / 500
    level += 1
    if exp < 1500: return level + (exp - 500) / 1000
    level += 1
    if exp < 3500: return level + (exp - 1500) / 2000
    level += 1
    if exp < 7000: return level + (exp - 3500) / 3500
    level += 1
    exp -= 7000
    return level + exp / 5000

def get_player_uuid_by_current_name(username: str):
    # (Keep existing get_player_uuid_by_current_name function - unchanged)
    try:
        response_mojang = requests.get(f"{UUID_URL}{username}", timeout=5) # Added timeout
        if response_mojang.status_code == 200:
            data_mojang = response_mojang.json()
            if data_mojang and 'id' in data_mojang:
                if data_mojang.get('name', '').lower() == username.lower():
                     return data_mojang.get("id")
        elif response_mojang.status_code == 204 or response_mojang.status_code == 404:
             pass # Player not found via Mojang current name, proceed to Hypixel
        # No else needed here, just proceed if Mojang didn't find it or errored

    except requests.exceptions.RequestException as e:
        # Use logging instead of print in a real app
        print(f"Mojang API request error for {username}: {e}. Trying Hypixel.")
    except Exception as e:
        print(f"Error processing Mojang response for {username}: {e}. Trying Hypixel.")

    try:
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params, timeout=10) # Added timeout
        response_hypixel.raise_for_status() # Raise HTTPError for bad responses (4XX, 5XX)
        data_hypixel = response_hypixel.json()

        if data_hypixel.get("success"):
            player_data = data_hypixel.get("player")
            if player_data:
                 # Check if the display name matches the searched name (case-insensitive)
                 if player_data.get("displayname", "").lower() == username.lower():
                     return player_data.get("uuid")
                 else:
                    # Name doesn't match current display name, but maybe historical? Let get_uuid_by_historical_name handle it.
                    return None
            else:
                 # Success true, but no player object - likely means player doesn't exist by this name NOW
                 return None
        else:
             # Success false
             cause = data_hypixel.get("cause", "Unknown reason")
             print(f"Hypixel API success=false for name {username}. Cause: {cause}")
             return None # Indicate failure clearly
    except requests.exceptions.RequestException as e:
        print(f"Hypixel API name lookup error for {username}: {e}")
        return None
    except Exception as e:
        print(f"Error processing Hypixel name lookup for {username}: {e}")
        return None

def get_uuid_by_historical_name(username: str):
    # (Keep existing get_uuid_by_historical_name function - unchanged, but add timeout)
    try:
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params, timeout=10) # Added timeout
        response_hypixel.raise_for_status()
        data_hypixel = response_hypixel.json()
        if data_hypixel.get("success") and data_hypixel.get("player"):
            uuid = data_hypixel["player"].get("uuid")
            current_name = data_hypixel["player"].get("displayname", "")
            # Ensure a historical lookup actually involves a different current name
            if current_name and current_name.lower() != username.lower():
                return uuid, current_name
            else:
                # Found a player, but the name matches the current search - this case shouldn't be historical
                # Or current_name is missing for some reason
                return None, None
        else:
             # Player not found even historically by this name, or API error
             return None, None
    except requests.exceptions.RequestException as e:
        print(f"Hypixel API historical lookup error for {username}: {e}")
        return None, None
    except Exception as e:
        print(f"Error processing Hypixel historical lookup for {username}: {e}")
        return None, None


# --- Calculation Functions ---

def calculate_ratio(numerator, denominator):
    """ Calculates ratio, returns numerator if denominator is 0, else numerator/denominator """
    if denominator == 0:
        return float(numerator) if numerator != 0 else 0.0
    return round(numerator / denominator, 2)

def calculate_mode_stats(bw_stats, prefix):
    wins = bw_stats.get(f"{prefix}wins_bedwars", 0)
    losses = bw_stats.get(f"{prefix}losses_bedwars", 0)
    final_kills = bw_stats.get(f"{prefix}final_kills_bedwars", 0)
    final_deaths = bw_stats.get(f"{prefix}final_deaths_bedwars", 0)
    beds_broken = bw_stats.get(f"{prefix}beds_broken_bedwars", 0)
    beds_lost = bw_stats.get(f"{prefix}beds_lost_bedwars", 0)
    kills = bw_stats.get(f"{prefix}kills_bedwars", 0)
    deaths = bw_stats.get(f"{prefix}deaths_bedwars", 0)

    games_played = wins + losses
    # *** FKDR Calculation Fix ***
    wlr = calculate_ratio(wins, losses)
    fkdr = calculate_ratio(final_kills, final_deaths) # Use helper function
    bblr = calculate_ratio(beds_broken, beds_lost)
    kdr = calculate_ratio(kills, deaths)
    # **************************

    win_rate = round((wins / games_played) * 100, 2) if games_played > 0 else 0
    finals_per_game = round(final_kills / games_played, 2) if games_played > 0 else 0

    return {
        "wins": wins, "losses": losses, "wlr": wlr, "win_rate": win_rate, "games_played": games_played,
        "final_kills": final_kills, "final_deaths": final_deaths, "fkdr": fkdr, "finals_per_game": finals_per_game,
        "beds_broken": beds_broken, "beds_lost": beds_lost, "bblr": bblr,
        "kills": kills, "deaths": deaths, "kdr": kdr,
    }

def get_player_stats_by_uuid(uuid: str):
    if not uuid:
        return {"error": "Invalid UUID provided."}

    params = {"key": API_KEY, "uuid": uuid}
    try:
        response = requests.get(PLAYER_URL, params=params, timeout=10) # Added timeout
        response.raise_for_status()
        data = response.json()

        if not data.get("success") or not data.get("player"):
            # Improved error message checking
            error_cause = "Player not found." if not data.get("player") else data.get("cause", "API error.")
            return {"error": error_cause, "uuid": uuid}

        player_data = data["player"]
        stats = player_data.get("stats", {})
        bw_stats = stats.get("Bedwars", {})
        achievements = player_data.get("achievements", {})

        exp = bw_stats.get("Experience", 0)
        level = math.floor(get_bedwars_level(exp))

        # Overall Stats Raw Data
        overall_wins = bw_stats.get("wins_bedwars", 0)
        overall_losses = bw_stats.get("losses_bedwars", 0)
        overall_final_kills = bw_stats.get("final_kills_bedwars", 0)
        overall_final_deaths = bw_stats.get("final_deaths_bedwars", 0)
        overall_beds_broken = bw_stats.get("beds_broken_bedwars", 0)
        overall_beds_lost = bw_stats.get("beds_lost_bedwars", 0)
        overall_kills = bw_stats.get("kills_bedwars", 0)
        overall_deaths = bw_stats.get("deaths_bedwars", 0)
        coins = bw_stats.get("coins", 0)
        slumber_tickets = achievements.get("bedwars_slumber_ticket_master") # Can be None

        # Overall Calculated Stats
        overall_games_played = overall_wins + overall_losses
        # *** FKDR Calculation Fix ***
        overall_wlr = calculate_ratio(overall_wins, overall_losses)
        overall_fkdr = calculate_ratio(overall_final_kills, overall_final_deaths) # Use helper function
        overall_bblr = calculate_ratio(overall_beds_broken, overall_beds_lost)
        overall_kdr = calculate_ratio(overall_kills, overall_deaths)
        # **************************

        overall_win_rate = round((overall_wins / overall_games_played) * 100, 2) if overall_games_played > 0 else 0
        overall_finals_per_star = round(overall_final_kills / level, 2) if level > 0 else float(overall_final_kills) # Handle level 0 case
        overall_finals_per_game = round(overall_final_kills / overall_games_played, 2) if overall_games_played > 0 else float(overall_final_kills) # Handle games_played 0 case

        # Mode Stats
        modes_data = {
            "solos": calculate_mode_stats(bw_stats, "eight_one_"),
            "doubles": calculate_mode_stats(bw_stats, "eight_two_"),
            "threes": calculate_mode_stats(bw_stats, "four_three_"),
            "fours": calculate_mode_stats(bw_stats, "four_four_"),
            "4v4": calculate_mode_stats(bw_stats, "two_four_")
        }

        # Core Mode Stats Calculation (unchanged logic, relies on corrected calculate_mode_stats)
        core_modes = ["solos", "doubles", "threes", "fours"]
        core_stats_agg = {
            "wins": 0, "losses": 0, "final_kills": 0, "final_deaths": 0,
            "beds_broken": 0, "beds_lost": 0, "kills": 0, "deaths": 0
        }
        for mode in core_modes:
            if mode_data := modes_data.get(mode):
                 for key in core_stats_agg:
                    core_stats_agg[key] += mode_data.get(key, 0) # Safely add, defaulting to 0 if key missing (shouldn't happen)

        core_games_played = core_stats_agg["wins"] + core_stats_agg["losses"]
        core_wlr = calculate_ratio(core_stats_agg["wins"], core_stats_agg["losses"])
        core_fkdr = calculate_ratio(core_stats_agg["final_kills"], core_stats_agg["final_deaths"])
        core_bblr = calculate_ratio(core_stats_agg["beds_broken"], core_stats_agg["beds_lost"])
        core_kdr = calculate_ratio(core_stats_agg["kills"], core_stats_agg["deaths"])
        core_win_rate = round((core_stats_agg["wins"] / core_games_played) * 100, 2) if core_games_played > 0 else 0
        core_finals_per_game = round(core_stats_agg["final_kills"] / core_games_played, 2) if core_games_played > 0 else float(core_stats_agg["final_kills"])

        modes_data['core'] = {
            "wins": core_stats_agg["wins"], "losses": core_stats_agg["losses"], "wlr": core_wlr,
            "win_rate": core_win_rate, "games_played": core_games_played,
            "final_kills": core_stats_agg["final_kills"], "final_deaths": core_stats_agg["final_deaths"],
            "fkdr": core_fkdr, "finals_per_game": core_finals_per_game,
            "beds_broken": core_stats_agg["beds_broken"], "beds_lost": core_stats_agg["beds_lost"], "bblr": core_bblr,
            "kills": core_stats_agg["kills"], "deaths": core_stats_agg["deaths"], "kdr": core_kdr,
        }

        # Most Played Gamemode (unchanged)
        most_played_gamemode = "N/A"
        max_games = -1
        all_mode_titles = {'solos': 'Solos', 'doubles': 'Doubles', 'threes': 'Threes', 'fours': 'Fours', '4v4': '4v4'}
        for mode_key, mode_title in all_mode_titles.items():
             # Ensure mode exists and has games_played key before comparing
            if mode_data := modes_data.get(mode_key):
                if games := mode_data.get("games_played", 0): # Default to 0 if missing
                    if games > max_games:
                        max_games = games
                        most_played_gamemode = mode_title


        # Return final structure
        return {
            "username": player_data.get("displayname", "N/A"),
            "uuid": uuid,
            "level": level,
            "most_played_gamemode": most_played_gamemode if max_games > 0 else "N/A", # Only show if games > 0
            "overall": {
                "wins": overall_wins, "losses": overall_losses, "wlr": overall_wlr,
                "final_kills": overall_final_kills, "final_deaths": overall_final_deaths, "fkdr": overall_fkdr,
                "beds_broken": overall_beds_broken, "beds_lost": overall_beds_lost, "bblr": overall_bblr,
                "kills": overall_kills, "deaths": overall_deaths, "kdr": overall_kdr,
                "coins": coins,
                "bedwars_slumber_ticket_master": slumber_tickets, # Keep original key from API
                "games_played": overall_games_played,
                "win_rate": overall_win_rate,
                "finals_per_star": overall_finals_per_star,
                "finals_per_game": overall_finals_per_game,
            },
            "modes": modes_data,
            "fetched_by": "uuid"
        }
    except requests.exceptions.RequestException as e:
        # Log the actual error e
        print(f"API request error fetching stats for UUID {uuid}: {e}")
        return {"error": f"API request error.", "uuid": uuid} # Don't expose detailed error to frontend
    except Exception as e:
        # Log the actual error e
        print(f"Error processing stats for UUID {uuid}: {e}")
        # Consider logging the traceback here: import traceback; traceback.print_exc()
        return {"error": "Internal server error processing stats.", "uuid": uuid}


# --- Fetching Logic (fetch_player_data, fetch_multiple_player_data - unchanged) ---

def fetch_player_data(username: str):
    # (Keep existing fetch_player_data function - unchanged)
    uuid = get_player_uuid_by_current_name(username)
    if uuid:
        stats = get_player_stats_by_uuid(uuid)
        if stats and 'error' not in stats:
             stats['original_search'] = username
             stats['name_match'] = True # Indicates the found name matches the search term
             return stats
        else:
             # Propagate error, include original search term and potentially the UUID if found
             error_payload = stats or {"error": "Error fetching stats by UUID."}
             error_payload['original_search'] = username
             if uuid: error_payload['uuid'] = uuid # Include UUID if we got that far
             return error_payload
    else:
        # UUID not found by current name, try historical
        historical_uuid, current_name_from_history = get_uuid_by_historical_name(username)
        if historical_uuid and current_name_from_history:
            # Found via historical name - return specific error type
            return {
                "error": "name_changed",
                "original_search": username,
                "current_name": current_name_from_history,
                "uuid": historical_uuid # Include UUID for potential direct lookup link
            }
        else:
            # Not found by current name or historical name
            return {"error": f"Player '{username}' not found.", "original_search": username}


def fetch_multiple_player_data(usernames: list):
    # (Keep existing fetch_multiple_player_data function - unchanged)
    results = {}
    # Consider using threading or asyncio for concurrent requests here if performance becomes an issue
    for username in usernames:
        # Normalize keys in the result dict to lowercase for easier lookup
        normalized_username = username.lower()
        results[normalized_username] = fetch_player_data(username)
        # Optional: Add a small delay between API requests if needed
        # time.sleep(0.1)
    return results