# hypixel_api.py
import requests
import math
from config import API_KEY
import time

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
    if exp < 3500: return level + (exp - 1500) / 2000
    level += 1
    if exp < 7000: return level + (exp - 3500) / 3500
    level += 1
    exp -= 7000
    return level + exp / 5000

def get_player_uuid_by_current_name(username: str):
    try:
        response_mojang = requests.get(f"{UUID_URL}{username}")
        if response_mojang.status_code == 200:
            data_mojang = response_mojang.json()
            if data_mojang and 'id' in data_mojang:
                if data_mojang.get('name', '').lower() == username.lower():
                     return data_mojang.get("id")
        elif response_mojang.status_code == 204 or response_mojang.status_code == 404:
             pass
        else:
             pass
    except requests.exceptions.RequestException as e:
        print(f"Mojang API request error for {username}: {e}. Trying Hypixel.")
    except Exception as e:
         print(f"Error processing Mojang response for {username}: {e}. Trying Hypixel.")

    try:
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params)
        response_hypixel.raise_for_status()
        data_hypixel = response_hypixel.json()
        if data_hypixel.get("success"):
            if data_hypixel.get("player"):
                 if data_hypixel["player"].get("displayname", "").lower() == username.lower():
                     return data_hypixel["player"].get("uuid")
                 else:
                     return None
            else:
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
    try:
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params)
        response_hypixel.raise_for_status()
        data_hypixel = response_hypixel.json()
        if data_hypixel.get("success") and data_hypixel.get("player"):
            uuid = data_hypixel["player"].get("uuid")
            current_name = data_hypixel["player"].get("displayname", "")
            return uuid, current_name
        else:
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"Hypixel API historical lookup error for {username}: {e}")
        return None, None
    except Exception as e:
        print(f"Error processing Hypixel historical lookup for {username}: {e}")
        return None, None

def calculate_mode_stats(bw_stats, prefix):
    """Helper function to calculate stats for a specific mode."""
    wins = bw_stats.get(f"{prefix}wins_bedwars", 0)
    losses = bw_stats.get(f"{prefix}losses_bedwars", 0)
    final_kills = bw_stats.get(f"{prefix}final_kills_bedwars", 0)
    final_deaths = bw_stats.get(f"{prefix}final_deaths_bedwars", 0)
    beds_broken = bw_stats.get(f"{prefix}beds_broken_bedwars", 0)
    beds_lost = bw_stats.get(f"{prefix}beds_lost_bedwars", 0)
    kills = bw_stats.get(f"{prefix}kills_bedwars", 0)
    deaths = bw_stats.get(f"{prefix}deaths_bedwars", 0)

    wlr = round(wins / losses, 2) if losses else 0
    fkdr = round(final_kills / final_deaths, 2) if final_deaths else 0
    bblr = round(beds_broken / beds_lost, 2) if beds_lost else 0
    kdr = round(kills / deaths, 2) if deaths else 0

    return {
        "wins": wins, "losses": losses, "wlr": wlr,
        "final_kills": final_kills, "final_deaths": final_deaths, "fkdr": fkdr,
        "beds_broken": beds_broken, "beds_lost": beds_lost, "bblr": bblr,
        "kills": kills, "deaths": deaths, "kdr": kdr,
    }

def get_player_stats_by_uuid(uuid: str):
    if not uuid:
        return {"error": "Invalid UUID provided."}

    params = {"key": API_KEY, "uuid": uuid}
    try:
        response = requests.get(PLAYER_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("success") or not data.get("player"):
            error_cause = data.get("cause", "Player not found or API error.") if data.get("success") else "API error or player not found."
            return {"error": error_cause, "uuid": uuid}

        player_data = data["player"]
        stats = player_data.get("stats", {})
        bw_stats = stats.get("Bedwars", {})
        exp = bw_stats.get("Experience", 0)

        # Overall stats (already calculated mostly)
        overall_wins = bw_stats.get("wins_bedwars", 0)
        overall_losses = bw_stats.get("losses_bedwars", 0)
        overall_final_kills = bw_stats.get("final_kills_bedwars", 0)
        overall_final_deaths = bw_stats.get("final_deaths_bedwars", 0)
        overall_beds_broken = bw_stats.get("beds_broken_bedwars", 0)
        overall_beds_lost = bw_stats.get("beds_lost_bedwars", 0)
        overall_kills = bw_stats.get("kills_bedwars", 0)
        overall_deaths = bw_stats.get("deaths_bedwars", 0)

        overall_wlr = round(overall_wins / overall_losses, 2) if overall_losses else 0
        overall_fkdr = round(overall_final_kills / overall_final_deaths, 2) if overall_final_deaths else 0
        overall_bblr = round(overall_beds_broken / overall_beds_lost, 2) if overall_beds_lost else 0
        overall_kdr = round(overall_kills / overall_deaths, 2) if overall_deaths else 0

        # Mode specific stats
        modes_data = {
            "solos": calculate_mode_stats(bw_stats, "eight_one_"),
            "doubles": calculate_mode_stats(bw_stats, "eight_two_"),
            "threes": calculate_mode_stats(bw_stats, "four_three_"),
            "fours": calculate_mode_stats(bw_stats, "four_four_"),
            "4v4": calculate_mode_stats(bw_stats, "two_four_") # Assuming 'two_four_' is 4v4
        }

        return {
            "username": player_data.get("displayname", "N/A"),
            "uuid": uuid,
            "level": math.floor(get_bedwars_level(exp)),
            # Overall section
            "overall": {
                "wins": overall_wins, "losses": overall_losses, "wlr": overall_wlr,
                "final_kills": overall_final_kills, "final_deaths": overall_final_deaths, "fkdr": overall_fkdr,
                "beds_broken": overall_beds_broken, "beds_lost": overall_beds_lost, "bblr": overall_bblr,
                "kills": overall_kills, "deaths": overall_deaths, "kdr": overall_kdr,
            },
            # Modes section
            "modes": modes_data,
            "fetched_by": "uuid"
        }
    except requests.exceptions.RequestException as e:
        print(f"API request error fetching stats for UUID {uuid}: {e}")
        return {"error": f"API request error: {e}", "uuid": uuid}
    except Exception as e:
        print(f"Error processing stats for UUID {uuid}: {e}")
        return {"error": "Internal server error processing stats.", "uuid": uuid}


def fetch_player_data(username: str):
    uuid = get_player_uuid_by_current_name(username)
    if uuid:
        stats = get_player_stats_by_uuid(uuid)
        if stats and 'error' not in stats:
             stats['original_search'] = username
             stats['name_match'] = True
             return stats
        else:
             error_payload = stats or {"error": "Error fetching stats by UUID."}
             error_payload['original_search'] = username
             error_payload['uuid'] = uuid
             return error_payload
    else:
        historical_uuid, current_name_from_history = get_uuid_by_historical_name(username)
        if historical_uuid:
            return {
                "error": "name_changed",
                "original_search": username,
                "current_name": current_name_from_history,
                "uuid": historical_uuid
            }
        else:
            return {"error": f"Player '{username}' not found.", "original_search": username}

def fetch_multiple_player_data(usernames: list):
    results = {}
    for username in usernames:
        normalized_username = username.lower()
        results[normalized_username] = fetch_player_data(username)
    return results

