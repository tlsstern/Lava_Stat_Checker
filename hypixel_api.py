import requests
import math
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
    if exp < 3500: return level + (exp - 1500) / 2000
    level += 1
    if exp < 7000: return level + (exp - 3500) / 3500
    level += 1
    exp -= 7000
    return level + exp / 5000

def get_player_uuid(username: str):
    try:
        response = requests.get(f"{UUID_URL}{username}")
        response.raise_for_status()
        if response.status_code == 200:
             # Check if response is not empty and contains 'id'
             data = response.json()
             if data and 'id' in data:
                 return data.get("id")
             else: # Fallback if Mojang API returns empty success or no id
                 print(f"Mojang API lieferte keine UUID für {username}, versuche Hypixel API...")
        else:
             print(f"Mojang API Status {response.status_code} für {username}, versuche Hypixel API...")

        # Fallback auf Hypixel API
        params = {"key": API_KEY, "name": username}
        response_hypixel = requests.get(PLAYER_URL, params=params)
        response_hypixel.raise_for_status()
        data_hypixel = response_hypixel.json()
        if data_hypixel.get("success") and data_hypixel.get("player"):
            return data_hypixel["player"].get("uuid")
        return None
    except requests.exceptions.RequestException as e:
        print(f"API Fehler beim Abrufen der UUID für {username}: {e}")
        return None
    except Exception as e:
        print(f"Fehler beim Abrufen der UUID für {username}: {e}")
        return None


def get_player_stats(uuid: str):
    if not uuid:
        return None
    params = {"key": API_KEY, "uuid": uuid}
    try:
        response = requests.get(PLAYER_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("success") or not data.get("player"):
            return {"error": "Spieler nicht gefunden oder API-Fehler."}

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
        }

    except requests.exceptions.RequestException as e:
        print(f"API Fehler beim Abrufen der Stats für UUID {uuid}: {e}")
        return {"error": f"API Fehler: {e}"}
    except Exception as e:
        print(f"Fehler beim Verarbeiten der Stats für UUID {uuid}: {e}")
        return {"error": "Interner Serverfehler."}

def get_multiple_player_stats(usernames: list):
    results = {}
    for username in usernames:
        # Normalize username for comparison later
        normalized_username = username.lower()
        uuid = get_player_uuid(username)
        if uuid:
            stats = get_player_stats(uuid)
            if stats and "error" not in stats:
                 # Use normalized username as key
                 results[normalized_username] = stats
                 # Ensure the original casing is preserved in the stats dict if needed elsewhere
                 results[normalized_username]['original_username'] = username
            else:
                 results[normalized_username] = {"error": stats.get("error", "Konnte keine Stats finden."), "username": username}
        else:
            results[normalized_username] = {"error": "UUID nicht gefunden.", "username": username}
    return results
