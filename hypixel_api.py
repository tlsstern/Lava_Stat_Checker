import requests
import math
from config import API_KEY
import time # Import time for potential delays

BASE_URL = "https://api.hypixel.net/v2"
PLAYER_URL = f"{BASE_URL}/player"
# Use Mojang API for UUID lookup primarily as it's often more reliable for current name -> UUID
UUID_URL = "https://api.mojang.com/users/profiles/minecraft/"
# Use Hypixel API for historical name -> UUID lookup as a fallback
NAME_HISTORY_URL_PREFIX = "https://api.mojang.com/user/profiles/" # Needs UUID
NAME_HISTORY_URL_SUFFIX = "/names"

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
    """
    Gets the UUID primarily using the Mojang API based on the CURRENT username.
    Falls back to Hypixel name lookup if Mojang fails.
    """
    try:
        response_mojang = requests.get(f"{UUID_URL}{username}")
        # Don't raise for status here, as a 404 (not found) is valid info
        if response_mojang.status_code == 200:
            data_mojang = response_mojang.json()
            if data_mojang and 'id' in data_mojang:
                # Verify the name matches case-insensitively, as Mojang might correct casing
                if data_mojang.get('name', '').lower() == username.lower():
                     print(f"UUID found via Mojang for {username}")
                     return data_mojang.get("id")
                else:
                    # Name casing might differ, or it found a similar name? Treat as not found for exact match.
                    print(f"Mojang found UUID but name casing differs or is inexact for {username}")
                    # Fall through to Hypixel check
            else:
                print(f"Mojang API returned success but no ID for {username}")
                # Fall through to Hypixel check
        elif response_mojang.status_code == 204 or response_mojang.status_code == 404:
             print(f"Mojang API: User {username} not found (Status {response_mojang.status_code}). Trying Hypixel.")
             # Fall through to Hypixel check
        else:
            # Other Mojang error (e.g., rate limit)
             print(f"Mojang API error {response_mojang.status_code} for {username}. Trying Hypixel.")
             # Fall through to Hypixel check

    except requests.exceptions.RequestException as e:
        print(f"Mojang API request error for {username}: {e}. Trying Hypixel.")
        # Fall through to Hypixel check
    except Exception as e:
         print(f"Error processing Mojang response for {username}: {e}. Trying Hypixel.")
         # Fall through to Hypixel check

    # --- Fallback to Hypixel API (less reliable for *current* name check) ---
    try:
        print(f"Trying Hypixel API name lookup for {username}...")
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params)
        response_hypixel.raise_for_status() # Raise for Hypixel errors (e.g., bad key)
        data_hypixel = response_hypixel.json()
        if data_hypixel.get("success"):
            if data_hypixel.get("player"):
                 # Check if the name returned by Hypixel matches the searched name (case-insensitive)
                 # Hypixel's 'displayname' usually holds the correct casing of the current name
                 if data_hypixel["player"].get("displayname", "").lower() == username.lower():
                     print(f"UUID found via Hypixel name lookup for {username}")
                     return data_hypixel["player"].get("uuid")
                 else:
                     # Hypixel found a player, but the name doesn't match the search term exactly.
                     # This could be an old name lookup. Return None for *current* name search.
                     print(f"Hypixel found player for '{username}', but current name is different: {data_hypixel['player'].get('displayname', '')}")
                     return None
            else:
                 # Success was true, but no player field - name likely doesn't exist currently
                 print(f"Hypixel API success=true, but no player data for name {username}")
                 return None
        else:
             # API call failed (e.g., invalid key, though raise_for_status should catch some)
             print(f"Hypixel API success=false for name {username}")
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
    """
    try:
        print(f"Trying Hypixel API historical lookup for name: {username}")
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params)
        response_hypixel.raise_for_status()
        data_hypixel = response_hypixel.json()
        if data_hypixel.get("success") and data_hypixel.get("player"):
            # Found a profile associated with this name (current or historical)
            uuid = data_hypixel["player"].get("uuid")
            current_name = data_hypixel["player"].get("displayname", "")
            print(f"Hypixel historical lookup found UUID {uuid} (current name: {current_name}) for searched name {username}")
            # Return both UUID and the current name found
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
        return None
    params = {"key": API_KEY, "uuid": uuid}
    try:
        response = requests.get(PLAYER_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("success") or not data.get("player"):
            print(f"get_player_stats_by_uuid: API success false or no player for UUID {uuid}")
            # Return specific error if player is null but success is true (e.g., banned?)
            error_cause = data.get("cause", "Spieler nicht gefunden oder API-Fehler.") if data.get("success") else "API-Fehler oder Spieler nicht gefunden."
            return {"error": error_cause, "uuid": uuid} # Include UUID in error dict

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

        return {
            "username": player_data.get("displayname", "N/A"),
            "uuid": uuid,
            "level": math.floor(get_bedwars_level(exp)),
            "wins": wins,
            "losses": losses,
            "wlr": round(wins / losses, 2) if losses else 0,
            "final_kills": final_kills,
            "final_deaths": final_deaths,
            "fkdr": round(final_kills / final_deaths, 2) if final_deaths else 0,
            "beds_broken": beds_broken,
            "beds_lost": beds_lost,
            "bblr": round(beds_broken / beds_lost, 2) if beds_lost else 0,
            "kills": kills,
            "deaths": deaths,
            "kdr": round(kills / deaths, 2) if deaths else 0,
            # Add a flag indicating this was fetched by UUID
            "fetched_by": "uuid"
        }

    except requests.exceptions.RequestException as e:
        print(f"API Fehler beim Abrufen der Stats für UUID {uuid}: {e}")
        return {"error": f"API Fehler: {e}", "uuid": uuid}
    except Exception as e:
        print(f"Fehler beim Verarbeiten der Stats für UUID {uuid}: {e}")
        return {"error": "Interner Serverfehler.", "uuid": uuid}


# --- Combined function for routes ---

def fetch_player_data(username: str):
    """
    Attempts to fetch player data.
    1. Tries to find UUID by current name.
    2. If found, fetches stats by UUID.
    3. If not found by current name, tries historical lookup.
    4. If historical lookup finds a UUID with a *different* current name, returns specific info.
    5. Otherwise returns stats or appropriate error.
    """
    print(f"Fetching data for username: {username}")
    uuid = get_player_uuid_by_current_name(username)

    if uuid:
        # Found UUID matching current name, fetch stats
        print(f"Found current UUID {uuid} for {username}. Fetching stats by UUID.")
        stats = get_player_stats_by_uuid(uuid)
        if stats and 'error' not in stats:
             # Add original search term for clarity, although it matches current name here
             stats['original_search'] = username
             stats['name_match'] = True # Flag indicating search name matches current name
             return stats
        else:
             # Error fetching stats even with valid UUID
             print(f"Error fetching stats for UUID {uuid} (found via current name {username}).")
             # Return the error from get_player_stats_by_uuid
             return stats or {"error": "Fehler beim Abrufen der Stats nach UUID.", "original_search": username, "uuid": uuid}
    else:
        # UUID not found for the *current* name. Check if it's an old name.
        print(f"UUID not found for current name '{username}'. Checking historical names...")
        historical_uuid, current_name_from_history = get_uuid_by_historical_name(username)

        if historical_uuid:
            # Found a UUID associated with the searched name, but it wasn't the current name.
            print(f"Found historical UUID {historical_uuid} for searched name '{username}'. Current name is '{current_name_from_history}'.")
            # Return specific dictionary indicating name mismatch
            return {
                "error": "name_changed",
                "original_search": username,
                "current_name": current_name_from_history,
                "uuid": historical_uuid
            }
        else:
            # Name not found currently, and no history found either.
            print(f"No current or historical UUID found for name '{username}'.")
            return {"error": f"Spieler '{username}' nicht gefunden.", "original_search": username}

def fetch_multiple_player_data(usernames: list):
    """Fetches data for multiple players using the fetch_player_data logic."""
    results = {}
    for username in usernames:
        # Normalize username for key consistency, but pass original for fetching
        normalized_username = username.lower()
        results[normalized_username] = fetch_player_data(username)
        # Ensure original name is stored if needed for display, fetch_player_data now includes it
        # if results[normalized_username] and 'original_search' not in results[normalized_username]:
        #      results[normalized_username]['original_search'] = username
    return results