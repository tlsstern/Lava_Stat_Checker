import requests
import math
from config import API_KEY
import time

BASE_URL = "https://api.hypixel.net/v2"
PLAYER_URL = f"{BASE_URL}/player"
UUID_URL = "https://api.mojang.com/users/profiles/minecraft/"

def get_bedwars_level(exp: int):
    """Calculates the Bedwars level based on experience."""
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
    """
    Gets the UUID primarily using the Mojang API based on the CURRENT username.
    Falls back to Hypixel name lookup if Mojang fails or doesn't find an exact match.
    Returns the UUID if found and the current name matches, otherwise None.
    """
    try:
        print(f"Attempting Mojang API lookup for current name: {username}")
        response_mojang = requests.get(f"{UUID_URL}{username}")
        if response_mojang.status_code == 200:
            data_mojang = response_mojang.json()
            if data_mojang and 'id' in data_mojang:
                if data_mojang.get('name', '').lower() == username.lower():
                     print(f"UUID found via Mojang for {username}")
                     return data_mojang.get("id")
                else:
                    print(f"Mojang found UUID but name casing differs or is inexact for {username}. Treating as not found for exact match.")
            else:
                print(f"Mojang API returned success but no ID for {username}. Trying Hypixel.")
        elif response_mojang.status_code == 204 or response_mojang.status_code == 404:
             print(f"Mojang API: User {username} not found (Status {response_mojang.status_code}). Trying Hypixel.")
        else:
             print(f"Mojang API error {response_mojang.status_code} for {username}. Trying Hypixel.")

    except requests.exceptions.RequestException as e:
        print(f"Mojang API request error for {username}: {e}. Trying Hypixel.")
    except Exception as e:
         print(f"Error processing Mojang response for {username}: {e}. Trying Hypixel.")
    try:
        print(f"Trying Hypixel API name lookup for {username}...")
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params)
        response_hypixel.raise_for_status()
        data_hypixel = response_hypixel.json()
        if data_hypixel.get("success"):
            if data_hypixel.get("player"):
                 if data_hypixel["player"].get("displayname", "").lower() == username.lower():
                     print(f"UUID found via Hypixel name lookup for {username}")
                     return data_hypixel["player"].get("uuid")
                 else:
                     print(f"Hypixel found player for '{username}', but current name is different: {data_hypixel['player'].get('displayname', '')}. Treating as not found for current name match.")
                     return None
            else:
                 print(f"Hypixel API success=true, but no player data for name {username}")
                 return None
        else:
             print(f"Hypixel API success=false for name {username}")
             cause = data_hypixel.get("cause", "Unknown reason")
             print(f"Cause: {cause}")
             return None
    except requests.exceptions.RequestException as e:
        print(f"Hypixel API name lookup error for {username}: {e}")
        return None
    except Exception as e:
        print(f"Error processing Hypixel name lookup for {username}: {e}")
        return None

def get_uuid_by_historical_name(username: str):
    """
    Tries to find a UUID associated with a potentially old username using Hypixel's player endpoint.
    This endpoint might return the profile even if the name is old.
    Returns (uuid, current_name) if found, otherwise (None, None).
    """
    try:
        print(f"Trying Hypixel API historical lookup for name: {username}")
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params)
        response_hypixel.raise_for_status()
        data_hypixel = response_hypixel.json()
        if data_hypixel.get("success") and data_hypixel.get("player"):
            uuid = data_hypixel["player"].get("uuid")
            current_name = data_hypixel["player"].get("displayname", "")
            print(f"Hypixel historical lookup found UUID {uuid} (current name: {current_name}) for searched name {username}")
            return uuid, current_name
        else:
            print(f"Hypixel historical lookup failed or no player found for name {username}")
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"Hypixel API historical lookup error for {username}: {e}")
        return None, None
    except Exception as e:
        print(f"Error processing Hypixel historical lookup for {username}: {e}")
        return None, None


def get_player_stats_by_uuid(uuid: str):
    """Gets player stats using the UUID."""
    if not uuid:
        print("get_player_stats_by_uuid called with no UUID.")
        return {"error": "Invalid UUID provided."}

    params = {"key": API_KEY, "uuid": uuid}
    try:
        print(f"Fetching stats by UUID: {uuid}")
        response = requests.get(PLAYER_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("success") or not data.get("player"):
            print(f"get_player_stats_by_uuid: API success false or no player for UUID {uuid}")
            error_cause = data.get("cause", "Player not found or API error.") if data.get("success") else "API error or player not found."
            return {"error": error_cause, "uuid": uuid} 

        # Extract player data
        player_data = data["player"]
        stats = player_data.get("stats", {})
        bw_stats = stats.get("Bedwars", {})

        wins = bw_stats.get("wins_bedwars", 0)
        losses = bw_stats.get("losses_bedwars", 0)
        final_kills = bw_stats.get("final_kills_bedwars", 0)
        final_deaths = bw_stats.get("final_deaths_bedwars", 0)
        beds_broken = bw_stats.get("beds_broken_bedwars", 0)
        beds_lost = bw_stats.get("beds_lost_bedwars", 0)
        kills = bw_stats.get("kills_bedwars", 0)
        deaths = bw_stats.get("deaths_bedwars", 0)
        exp = bw_stats.get("Experience", 0)

        wlr = round(wins / losses, 2) if losses else 0
        fkdr = round(final_kills / final_deaths, 2) if final_deaths else 0
        bblr = round(beds_broken / beds_lost, 2) if beds_lost else 0
        kdr = round(kills / deaths, 2) if deaths else 0

        return {
            "username": player_data.get("displayname", "N/A"),
            "uuid": uuid,
            "level": math.floor(get_bedwars_level(exp)),
            "wins": wins,
            "losses": losses,
            "wlr": wlr,
            "final_kills": final_kills,
            "final_deaths": final_deaths,
            "fkdr": fkdr,
            "beds_broken": beds_broken,
            "beds_lost": beds_lost,
            "bblr": bblr,
            "kills": kills,
            "deaths": deaths,
            "kdr": kdr,
            "fetched_by": "uuid"
        }

    except requests.exceptions.RequestException as e:
        print(f"API request error fetching stats for UUID {uuid}: {e}")
        return {"error": f"API request error: {e}", "uuid": uuid}
    except Exception as e:
        print(f"Error processing stats for UUID {uuid}: {e}")
        return {"error": "Internal server error processing stats.", "uuid": uuid}

def fetch_player_data(username: str):
    """
    Attempts to fetch player data, handling current and historical names.
    1. Tries to find UUID by current name (case-insensitive).
    2. If found, fetches stats by UUID.
    3. If not found by current name, tries historical lookup via Hypixel API.
    4. If historical lookup finds a UUID with a *different* current name, returns specific info.
    5. Otherwise returns stats or appropriate error message.
    """
    print(f"Fetching data for username: {username}")
    uuid = get_player_uuid_by_current_name(username)

    if uuid:
        print(f"Found current UUID {uuid} for {username}. Fetching stats by UUID.")
        stats = get_player_stats_by_uuid(uuid)
        if stats and 'error' not in stats:
             stats['original_search'] = username
             stats['name_match'] = True
             print(f"Successfully fetched stats for {username} (UUID: {uuid})")
             return stats
        else:
             print(f"Error fetching stats for UUID {uuid} (found via current name {username}).")
             error_payload = stats or {"error": "Error fetching stats by UUID."}
             error_payload['original_search'] = username
             error_payload['uuid'] = uuid
             return error_payload
    else:
        print(f"UUID not found for current name '{username}'. Checking historical names via Hypixel...")
        historical_uuid, current_name_from_history = get_uuid_by_historical_name(username)

        if historical_uuid:
            print(f"Found historical UUID {historical_uuid} for searched name '{username}'. Current name is '{current_name_from_history}'.")
            return {
                "error": "name_changed",
                "original_search": username,
                "current_name": current_name_from_history,
                "uuid": historical_uuid
            }
        else:
            print(f"No current or historical UUID found for name '{username}'.")
            return {"error": f"Player '{username}' not found.", "original_search": username}

def fetch_multiple_player_data(usernames: list):
    """Fetches data for multiple players using the fetch_player_data logic."""
    results = {}
    print(f"Fetching data for multiple players: {usernames}")
    for username in usernames:
        normalized_username = username.lower()
        results[normalized_username] = fetch_player_data(username)
        print(f"Result for {username}: {results[normalized_username].get('error', 'Success')}")
    return results

