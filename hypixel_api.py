import requests
import math
import scrapper
import re
import traceback
from config import API_KEY

BASE_URL = "https://api.hypixel.net/v2"
PLAYER_URL = f"{BASE_URL}/player"
UUID_URL = "https://api.mojang.com/users/profiles/minecraft/"

def get_bedwars_level(exp: int):
    if not isinstance(exp, int) or exp < 0:
        return 0.0
    level = 100 * (exp // 487000)
    exp = exp % 487000
    if exp < 500: return level + exp / 500
    level += 1
    if exp < 1500: return level + (exp - 500) / 1000
    level += 1
    if exp < 3500: return level + (exp - 3500) / 2000
    level += 1
    if exp < 7000: return level + (exp - 3500) / 3500
    level += 1
    exp -= 7000
    return level + exp / 5000

def get_player_uuid_by_current_name(username: str):
    """
    Attempts to get UUID by current name using Mojang API first, then Hypixel API.
    Returns UUID if found and the name matches the current name, otherwise None.
    """
    try:
        response_mojang = requests.get(f"{UUID_URL}{username}", timeout=5)
        if response_mojang.status_code == 200:
            data_mojang = response_mojang.json()
            if data_mojang and 'id' in data_mojang and data_mojang.get('name', '').lower() == username.lower():
                 print(f"UUID found via Mojang for {username}")
                 return data_mojang.get("id")
        elif response_mojang.status_code == 204 or response_mojang.status_code == 404:
             print(f"Mojang API did not find user {username} or name history.")
             pass
        else:
            print(f"Mojang API returned unexpected status code {response_mojang.status_code} for {username}.")

    except requests.exceptions.RequestException as e:
        print(f"Mojang API request error for {username}: {e}. Trying Hypixel.")
    except Exception as e:
        print(f"Error processing Mojang response for {username}: {e}. Trying Hypixel.")

    try:
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params, timeout=10)
        response_hypixel.raise_for_status()
        data_hypixel = response_hypixel.json()

        if data_hypixel.get("success"):
            player_data = data_hypixel.get("player")
            if player_data:
                 if player_data.get("displayname", "").lower() == username.lower():
                     print(f"UUID found via Hypixel for {username}")
                     return player_data.get("uuid")
                 else:
                     print(f"Hypixel API found UUID but displayname '{player_data.get('displayname')}' does not match '{username}'.")
                     return None
            else:
                 print(f"Hypixel API found no player data for name {username}.")
                 return None
        else:
             cause = data_hypixel.get("cause", "Unknown reason")
             print(f"Hypixel API success=false for name {username}. Cause: {cause}")
             return None
    except requests.exceptions.RequestException as e:
        print(f"Hypixel API name lookup error for {username}: {e}")
        return None
    except Exception as e:
        print(f"Error processing Hypixel name lookup for {username}: {e}")
        return None

def get_uuid_by_historical_name(username: str):
    """
    Attempts to find a UUID for a historical name using Hypixel API.
    Returns UUID and current name if a player is found but their name has changed,
    otherwise None, None.
    """
    try:
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params, timeout=10)
        response_hypixel.raise_for_status()
        data_hypixel = response_hypixel.json()
        if data_hypixel.get("success") and data_hypixel.get("player"):
            uuid = data_hypixel["player"].get("uuid")
            current_name = data_hypixel["player"].get("displayname", "")
            if uuid and current_name and current_name.lower() != username.lower():
                print(f"Hypixel API found historical name '{username}', current name is '{current_name}'.")
                return uuid, current_name
            else:
                 print(f"Hypixel API found player for historical lookup, but name does not seem changed for '{username}'.")
                 return None, None
        else:
             print(f"Hypixel API found no player for historical name lookup '{username}'.")
             return None, None
    except requests.exceptions.RequestException as e:
        print(f"Hypixel API historical lookup request error for {username}: {e}")
        return None, None
    except Exception as e:
        print(f"Error processing Hypixel historical lookup response for {username}: {e}")
        return None, None

def calculate_ratio(numerator, denominator):
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
    wlr = calculate_ratio(wins, losses)
    fkdr = calculate_ratio(final_kills, final_deaths)
    bblr = calculate_ratio(beds_broken, beds_lost)
    kdr = calculate_ratio(kills, deaths)

    win_rate = round((wins / games_played) * 100, 2) if games_played > 0 else 0.0
    finals_per_game = round(final_kills / games_played, 2) if games_played > 0 else 0.0

    return {
        "wins": wins, "losses": losses, "wlr": wlr, "win_rate": win_rate, "games_played": games_played,
        "final_kills": final_kills, "final_deaths": final_deaths, "fkdr": fkdr, "finals_per_game": finals_per_game,
        "beds_broken": beds_broken, "beds_lost": beds_lost, "bblr": bblr,
        "kills": kills, "deaths": deaths, "kdr": kdr,
    }

def _get_rank_info(player_data):
    prefix = player_data.get("prefix")
    if prefix:
        clean_prefix = re.sub(r'§[0-9a-fk-or]', '', prefix).strip()
        return {"display_rank": clean_prefix}

    rank = player_data.get("rank")
    if rank and rank != "NORMAL":
        return {"display_rank": rank}

    monthly_package_rank = player_data.get("monthlyPackageRank")
    if monthly_package_rank and monthly_package_rank != "NONE":
        return {"display_rank": "MVP++"}

    new_package_rank = player_data.get("newPackageRank")
    if new_package_rank and new_package_rank != "NONE":
        display_rank = new_package_rank.replace("_PLUS", "+")
        return {"display_rank": display_rank}

    package_rank = player_data.get("packageRank")
    if package_rank and package_rank != "NONE":
        display_rank = package_rank.replace("_PLUS", "+")
        return {"display_rank": display_rank}

    return {"display_rank": "Non"}

def get_player_stats_by_uuid(uuid: str):
    """
    Fetches player stats using Hypixel API by UUID.
    Returns a dictionary of stats or an error dictionary.
    """
    if not uuid:
        return {"error": "Invalid UUID provided."}

    params = {"key": API_KEY, "uuid": uuid}
    try:
        response = requests.get(PLAYER_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("success") or not data.get("player"):
            error_cause = "Player not found." if not data.get("player") else data.get("cause", "API error.")
            print(f"Hypixel API success=false or no player data for UUID {uuid}. Cause: {error_cause}")
            return {"error": error_cause, "uuid": uuid}

        player_data = data["player"]
        rank_info = _get_rank_info(player_data)

        stats = player_data.get("stats", {})
        bw_stats = stats.get("Bedwars", {})
        achievements = player_data.get("achievements", {})

        exp = bw_stats.get("Experience", 0)
        level = math.floor(get_bedwars_level(exp))

        overall_wins = bw_stats.get("wins_bedwars", 0)
        overall_losses = bw_stats.get("losses_bedwars", 0)
        overall_final_kills = bw_stats.get("final_kills_bedwars", 0)
        overall_final_deaths = bw_stats.get("final_deaths_bedwars", 0)
        overall_beds_broken = bw_stats.get("beds_broken_bedwars", 0)
        overall_beds_lost = bw_stats.get("beds_lost_bedwars", 0)
        overall_kills = bw_stats.get("kills_bedwars", 0)
        overall_deaths = bw_stats.get("deaths_bedwars", 0)
        coins = bw_stats.get("coins", 0)
        slumber_tickets = achievements.get("bedwars_slumber_ticket_master") # Example achievement

        overall_games_played = overall_wins + overall_losses

        overall_wlr = calculate_ratio(overall_wins, overall_losses)
        overall_fkdr = calculate_ratio(overall_final_kills, overall_final_deaths)
        overall_bblr = calculate_ratio(overall_beds_broken, overall_beds_lost)
        overall_kdr = calculate_ratio(overall_kills, overall_deaths)

        overall_win_rate = round((overall_wins / overall_games_played) * 100, 2) if overall_games_played > 0 else 0.0
        overall_finals_per_star = round(overall_final_kills / level, 2) if level > 0 else float(overall_final_kills) if overall_final_kills > 0 else 0.0
        overall_finals_per_game = round(overall_final_kills / overall_games_played, 2) if overall_games_played > 0 else float(overall_final_kills) if overall_final_kills > 0 else 0.0


        modes_data = {
            "solos": calculate_mode_stats(bw_stats, "eight_one_"),
            "doubles": calculate_mode_stats(bw_stats, "eight_two_"),
            "threes": calculate_mode_stats(bw_stats, "four_three_"),
            "fours": calculate_mode_stats(bw_stats, "four_four_"),
            "4v4": calculate_mode_stats(bw_stats, "two_four_")
        }

        core_modes = ["solos", "doubles", "threes", "fours"]
        core_stats_agg = {
            "wins": 0, "losses": 0, "final_kills": 0, "final_deaths": 0,
            "beds_broken": 0, "beds_lost": 0, "kills": 0, "deaths": 0,
            "games_played": 0
        }
        for mode in core_modes:
            if mode_data := modes_data.get(mode):
                 for key in core_stats_agg:
                    core_stats_agg[key] += mode_data.get(key, 0)

        core_wlr = calculate_ratio(core_stats_agg["wins"], core_stats_agg["losses"])
        core_fkdr = calculate_ratio(core_stats_agg["final_kills"], core_stats_agg["final_deaths"])
        core_bblr = calculate_ratio(core_stats_agg["beds_broken"], core_stats_agg["beds_lost"])
        core_kdr = calculate_ratio(core_stats_agg["kills"], core_stats_agg["deaths"])
        core_win_rate = round((core_stats_agg["wins"] / core_stats_agg["games_played"]) * 100, 2) if core_stats_agg["games_played"] > 0 else 0.0
        core_finals_per_game = round(core_stats_agg["final_kills"] / core_stats_agg["games_played"], 2) if core_stats_agg["games_played"] > 0 else float(core_stats_agg["final_kills"]) if core_stats_agg["final_kills"] > 0 else 0.0

        modes_data['core'] = {
            "wins": core_stats_agg["wins"], "losses": core_stats_agg["losses"], "wlr": core_wlr,
            "win_rate": core_win_rate, "games_played": core_stats_agg["games_played"],
            "final_kills": core_stats_agg["final_kills"], "final_deaths": core_stats_agg["final_deaths"],
            "fkdr": core_fkdr, "finals_per_game": core_finals_per_game,
            "beds_broken": core_stats_agg["beds_broken"], "beds_lost": core_stats_agg["beds_lost"], "bblr": core_bblr,
            "kills": core_stats_agg["kills"], "deaths": core_stats_agg["deaths"], "kdr": core_kdr,
        }

        most_played_gamemode = "N/A"
        max_games = -1
        all_mode_titles = {'solos': 'Solos', 'doubles': 'Doubles', 'threes': 'Threes', 'fours': 'Fours', '4v4': '4v4'}
        for mode_key, mode_title in all_mode_titles.items():
            if mode_data := modes_data.get(mode_key):
                if games := mode_data.get("games_played", 0):
                    if games > max_games:
                        max_games = games
                        most_played_gamemode = mode_title

        return {
            "username": player_data.get("displayname", "N/A"),
            "uuid": uuid,
            "rank_info": rank_info,
            "level": level,
            "most_played_gamemode": most_played_gamemode if max_games > 0 else "N/A",
            "overall": {
                "wins": overall_wins, "losses": overall_losses, "wlr": overall_wlr,
                "final_kills": overall_final_kills, "final_deaths": overall_final_deaths, "fkdr": overall_fkdr,
                "beds_broken": overall_beds_broken, "beds_lost": overall_beds_lost, "bblr": overall_bblr,
                "kills": overall_kills, "deaths": overall_deaths, "kdr": overall_kdr,
                "coins": coins,
                "bedwars_slumber_ticket_master": slumber_tickets,
                "games_played": overall_games_played,
                "win_rate": overall_win_rate,
                "finals_per_star": overall_finals_per_star,
                "finals_per_game": overall_finals_per_game,
            },
            "modes": modes_data,
            "fetched_by": "api"
        }

    except requests.exceptions.RequestException as e:
        print(f"API request error fetching stats for UUID {uuid}: {e}")
        return {"error": f"API request error: {e}", "uuid": uuid, "fetched_by": "api_error"}
    except Exception as e:
        print(f"Error processing stats for UUID {uuid}: {e}")
        traceback.print_exc()
        return {"error": f"Internal server error processing API stats: {e}", "uuid": uuid, "fetched_by": "api_error"}


def fetch_player_data(username: str):
    """
    Fetches player data, attempting API first, then falling back to scrapper.
    """
    print(f"Attempting to fetch data for {username}...")
    uuid = get_player_uuid_by_current_name(username)

    if uuid:
        print(f"UUID found for {username}: {uuid}. Attempting API fetch by UUID.")
        try:
            stats = get_player_stats_by_uuid(uuid)
            if stats and stats.get('fetched_by') == 'api' and 'error' not in stats:
                 stats['original_search'] = username
                 stats['name_match'] = True
                 print(f"Successfully fetched API data for {username} ({uuid}).")
                 return stats
            else:
                 print(f"API fetch by UUID failed for {username} ({uuid}). Details: {stats.get('error')}. Falling back to scrapper.")
                 scraped_data = scrapper.scrape_bwstats(username)
                 scraped_data['original_search'] = username
                 scraped_data['fetched_by'] = 'scrapper'
                 if stats and stats.get('fetched_by') == 'api_error':
                     scraped_data['api_error_details'] = stats.get('error')
                 print(f"Returning scrapper data for {username}.")
                 return scraped_data

        except Exception as e:
            print(f"An unexpected error occurred during API fetch for {username} ({uuid}): {e}. Falling back to scrapper.")
            traceback.print_exc()
            scraped_data = scrapper.scrape_bwstats(username)
            scraped_data['original_search'] = username
            scraped_data['fetched_by'] = 'scrapper'
            scraped_data['api_error_details'] = str(e) 
            print(f"Returning scrapper data for {username} after API exception.")
            return scraped_data

    else:
        print(f"UUID not found for current name '{username}'. Checking for historical name...")
        historical_uuid, current_name_from_history = get_uuid_by_historical_name(username)

        if historical_uuid and current_name_from_history:
            print(f"Identified '{username}' as a historical name for '{current_name_from_history}' (UUID: {historical_uuid}).")
            return {
                "error": "name_changed",
                "original_search": username,
                "current_name": current_name_from_history,
                "uuid": historical_uuid,
                "fetched_by": "api_name_history"
            }
        else:
            print(f"Player '{username}' not found via API (current or historical lookup). Falling back to scrapper.")
            scraped_data = scrapper.scrape_bwstats(username)
            scraped_data['original_search'] = username
            scraped_data['fetched_by'] = 'scrapper'
            if 'error' not in scraped_data:
                 scraped_data['api_error_details'] = f"Player '{username}' not found via Hypixel API lookup."
            print(f"Returning scrapper data for {username} after API lookup failure.")
            return scraped_data

def fetch_multiple_player_data(usernames: list):
    """
    Fetches data for multiple players, handling potential API/scrapper fallbacks for each.
    """
    results = {}
    for username in usernames:
        normalized_username = username.lower()
        results[normalized_username] = fetch_player_data(username)
    return results

# Note for app.py: The data structure returned by fetch_player_data can now be
# either the API format (if successful), a specific 'name_changed' error structure,
# or the raw data structure from the scrapper.
# You will need to update app.py (specifically player_stats_page and compare_stats_page)
# to check the 'fetched_by' key and adapt how the data is processed and displayed
# based on whether it came from the API or the scrapper.
# The 'format_stat_section' function in app.py is currently designed for the API
# structure; it may need modifications or conditional logic to work with scrapper data.