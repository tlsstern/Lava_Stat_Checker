import requests
import datetime
import json
import time
import math
import os
import pytz

print("Starting data retrieval script...")

# Load Hypixel API key from key.txt
def load_api_key():
    print("Attempting to load API key from key.txt...")
    try:
        with open("key.txt", "r") as f:
            api_key = f.read().strip()
            if not api_key:
                raise ValueError("key.txt is empty")
            print("API key loaded successfully.")
            return api_key
    except FileNotFoundError:
        print("Error: key.txt not found in the current directory.")
        raise
    except Exception as e:
        print(f"Error reading key.txt: {e}")
        raise

# Load player names from player_names.txt
def load_player_names():
    print("Attempting to load player names from player_names.txt...")
    try:
        with open("player_names.txt", "r") as f:
            # Read the entire file content as a single line
            content = f.read().strip()
            # Check if the content is in the expected format (e.g., "(name1, name2, ...)")
            if not content.startswith("(") or not content.endswith(")"):
                raise ValueError("player_names.txt must be in the format (name1, name2, ...)")
            # Remove parentheses and split by comma
            names = content[1:-1].split(",")
            # Strip whitespace from each name and filter out empty strings
            names = [name.strip() for name in names if name.strip()]
            if not names:
                raise ValueError("No valid player names found in player_names.txt")
            print(f"Loaded player names: {names}")
            return names
    except FileNotFoundError:
        print("Error: player_names.txt not found in the current directory.")
        raise
    except Exception as e:
        print(f"Error reading player_names.txt: {e}")
        raise

HYPIXEL_API_KEY = load_api_key()
PLAYER_NAMES = load_player_names()

CHEST_TZ = pytz.timezone("Europe/Paris")

def get_bedwars_level(exp: int):
    level = 100 * (exp // 487000)
    exp = exp % 487000
    if exp < 500:
        precise_level = level + exp / 500
        return precise_level
    level += 1
    if exp < 1500:
        precise_level = level + (exp - 500) / 1000
        return precise_level
    level += 1
    if exp < 3500:
        precise_level = level + (exp - 1500) / 2000
        return precise_level
    level += 1
    if exp < 7000:
        precise_level = level + (exp - 3500) / 3500
        return precise_level
    level += 1
    exp -= 7000
    precise_level = level + exp / 5000
    return precise_level

def get_hypixel_stats(uuid):
    print(f"Checking stats for UUID: {uuid}")
    try:
        response = requests.get(f"https://api.hypixel.net/player?key={HYPIXEL_API_KEY}&uuid={uuid}")
        response.raise_for_status()
        data = response.json()
        if data["success"] and data["player"] is not None and data["player"].get("stats", {}).get("Bedwars", {}):
            bedwars_stats = data["player"]["stats"]["Bedwars"]
            wins = bedwars_stats.get("wins_bedwars", 0)
            losses = bedwars_stats.get("losses_bedwars", 0)
            beds_broken = bedwars_stats.get("beds_broken_bedwars", 0)
            beds_lost = bedwars_stats.get("beds_lost_bedwars", 0)
            final_kills = bedwars_stats.get("final_kills_bedwars", 0)
            final_deaths = bedwars_stats.get("final_deaths_bedwars", 0)
            kills = bedwars_stats.get("kills_bedwars", 0)
            deaths = bedwars_stats.get("deaths_bedwars", 0)
            solo_wins = bedwars_stats.get("eight_one_wins_bedwars", 0)
            solo_losses = bedwars_stats.get("eight_one_losses_bedwars", 0)
            doubles_wins = bedwars_stats.get("eight_two_wins_bedwars", 0)
            doubles_losses = bedwars_stats.get("eight_two_losses_bedwars", 0)
            threes_wins = bedwars_stats.get("four_three_wins_bedwars", 0)
            threes_losses = bedwars_stats.get("four_three_losses_bedwars", 0)
            fours_wins = bedwars_stats.get("four_four_wins_bedwars", 0)
            fours_losses = bedwars_stats.get("four_four_losses_bedwars", 0)
            four_v_four_wins = bedwars_stats.get("two_four_wins_bedwars", 0)
            four_v_four_losses = bedwars_stats.get("two_four_losses_bedwars", 0)
            exp = bedwars_stats.get("Experience", 0)
            stars = get_bedwars_level(exp)
            stats = (wins, losses, beds_broken, beds_lost, final_kills, final_deaths, kills, deaths, stars,
                     solo_wins, solo_losses, 0, 0, doubles_wins, doubles_losses, 0, 0,
                     threes_wins, threes_losses, 0, 0, fours_wins, fours_losses, 0, 0,
                     four_v_four_wins, four_v_four_losses, 0, 0, 0, 0)
            print(f"Stats fetched: {stats[:18]}...")
            return stats
        else:
            print(f"No Bedwars stats found for UUID: {uuid}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Hypixel API: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def calculate_period_start(now):
    # Daily period starts at 12:00 PM CET
    daily_start = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if now < daily_start:
        daily_start -= datetime.timedelta(days=1)
    
    # Weekly period starts on Monday at 05:00 AM CET
    weekly_start = now - datetime.timedelta(days=now.weekday())
    weekly_start = weekly_start.replace(hour=5, minute=0, second=0, microsecond=0)
    if now < weekly_start:
        weekly_start -= datetime.timedelta(days=7)
    
    # Monthly period starts on the 1st at 00:00 AM CET
    monthly_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now < monthly_start:
        monthly_start -= datetime.timedelta(days=now.day - 1)
    
    # Yearly period starts on January 1st at 00:00 AM CET
    yearly_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    if now < yearly_start:
        yearly_start -= datetime.timedelta(days=365 if not (now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0)) else 366)
    
    return (daily_start, weekly_start, monthly_start, yearly_start)

def save_period_data(period_data, period_type, start_time):
    if period_type == "daily":
        filename = f"daily_{start_time.strftime('%d-%m-%Y')}_tracker.json"
    elif period_type == "weekly":
        filename = f"weekly_{start_time.strftime('%d-%m-%Y')}_tracker.json"
    elif period_type == "monthly":
        filename = f"monthly_{start_time.strftime('%d-%m-%Y')}_tracker.json"
    elif period_type == "yearly":
        filename = f"yearly_{start_time.strftime('%d-%m-%Y')}_tracker.json"
    else:
        raise ValueError(f"Unknown period type: {period_type}")
    try:
        with open(filename, "w") as f:
            json.dump(period_data, f, indent=4)
        print(f"Saved {period_type} stats to {filename}")
    except Exception as e:
        print(f"Error saving {period_type} data to {filename}: {e}")

def save_period_baseline(now, all_player_data, period_type):
    if period_type == "daily":
        filename = now.strftime("%d.%m.%Y.json")
    elif period_type == "weekly":
        filename = now.strftime("%d.%m.%Y_weekly.json")
    elif period_type == "monthly":
        filename = now.strftime("%d.%m.%Y_monthly.json")
    elif period_type == "yearly":
        filename = now.strftime("%d.%m.%Y_yearly.json")
    else:
        raise ValueError(f"Unknown period type: {period_type}")
    try:
        with open(filename, "w") as f:
            json.dump({"baselines": all_player_data}, f, indent=4)
        print(f"Saved {period_type} baseline to {filename}")
    except Exception as e:
        print(f"Error saving {period_type} baseline to {filename}: {e}")

def retrieve_and_save_data():
    all_player_data = {}
    now = datetime.datetime.now(CHEST_TZ)
    print(f"Current time (CET): {now}")
    
    print("Loading previous data from player_stats.json...")
    try:
        with open("player_stats.json", "r") as f:
            previous_data = json.load(f)
        print("Previous data loaded successfully.")
    except FileNotFoundError:
        print("player_stats.json not found. Creating initial data structure with current periods.")
        current_daily_start, current_weekly_start, current_monthly_start, current_yearly_start = calculate_period_start(now)
        previous_data = {
            "daily": {current_daily_start.isoformat(): {}},
            "weekly": {current_weekly_start.isoformat(): {}},
            "monthly": {current_monthly_start.isoformat(): {}},
            "yearly": {current_yearly_start.isoformat(): {}},
            "baselines": {},
            "initial_baselines": {}
        }
    except Exception as e:
        print(f"Error loading previous data: {e}")
        previous_data = {
            "daily": {},
            "weekly": {},
            "monthly": {},
            "yearly": {},
            "baselines": {},
            "initial_baselines": {}
        }
    
    current_daily_start, current_weekly_start, current_monthly_start, current_yearly_start = calculate_period_start(now)
    print(f"Current periods: Daily={current_daily_start}, Weekly={current_weekly_start}, Monthly={current_monthly_start}, Yearly={current_yearly_start}")
    
    previous_daily_start = datetime.datetime.fromisoformat(list(previous_data.get("daily", {}).keys())[0]).replace(tzinfo=CHEST_TZ) if previous_data.get("daily") else None
    previous_weekly_start = datetime.datetime.fromisoformat(list(previous_data.get("weekly", {}).keys())[0]).replace(tzinfo=CHEST_TZ) if previous_data.get("weekly") else None
    previous_monthly_start = datetime.datetime.fromisoformat(list(previous_data.get("monthly", {}).keys())[0]).replace(tzinfo=CHEST_TZ) if previous_data.get("monthly") else None
    previous_yearly_start = datetime.datetime.fromisoformat(list(previous_data.get("yearly", {}).keys())[0]).replace(tzinfo=CHEST_TZ) if previous_data.get("yearly") else None

    # Check and archive periods
    if previous_daily_start and previous_daily_start.date() != current_daily_start.date():
        print(f"Day has changed. Archiving daily data for {previous_daily_start.date()}...")
        save_period_data(previous_data["daily"], "daily", previous_daily_start)
        save_period_baseline(previous_daily_start, previous_data["baselines"], "daily")
        previous_data["daily"] = {current_daily_start.isoformat(): {}}
    
    if previous_weekly_start and previous_weekly_start.isocalendar()[1] != current_weekly_start.isocalendar()[1]:
        print(f"Week has changed. Archiving weekly data for week starting {previous_weekly_start.date()}...")
        save_period_data(previous_data["weekly"], "weekly", previous_weekly_start)
        save_period_baseline(previous_weekly_start, previous_data["baselines"], "weekly")
        previous_data["weekly"] = {current_weekly_start.isoformat(): {}}
    
    if previous_monthly_start and previous_monthly_start.month != current_monthly_start.month:
        print(f"Month has changed. Archiving monthly data for {previous_monthly_start.strftime('%B %Y')}...")
        save_period_data(previous_data["monthly"], "monthly", previous_monthly_start)
        save_period_baseline(previous_monthly_start, previous_data["baselines"], "monthly")
        previous_data["monthly"] = {current_monthly_start.isoformat(): {}}
    
    if previous_yearly_start and previous_yearly_start.year != current_yearly_start.year:
        print(f"Year has changed. Archiving yearly data for {previous_yearly_start.year}...")
        save_period_data(previous_data["yearly"], "yearly", previous_yearly_start)
        save_period_baseline(previous_yearly_start, previous_data["baselines"], "yearly")
        previous_data["yearly"] = {current_yearly_start.isoformat(): {}}

    # Save daily baseline if previous day exists
    previous_daily_filename = (now - datetime.timedelta(days=1)).strftime("%d.%m.%Y.json")
    if os.path.exists(previous_daily_filename):
        print(f"Previous daily baseline exists ({previous_daily_filename}). Saving new baseline...")
        save_period_baseline(now, all_player_data, "daily")

    print("Fetching stats for players...")
    for player_name in PLAYER_NAMES:
        try:
            print(f"Checking stats for player: {player_name}")
            uuid_response = requests.get(f"https://api.hypixel.net/player?key={HYPIXEL_API_KEY}&name={player_name}")
            uuid_response.raise_for_status()
            uuid_data = uuid_response.json()
            if uuid_data["success"] and uuid_data["player"] is not None:
                uuid = uuid_data["player"]["uuid"]
                current_stats = get_hypixel_stats(uuid)
                if current_stats:
                    baseline_key = f"{uuid}_total"
                    initial_key = f"{uuid}_total"

                    if initial_key not in previous_data["initial_baselines"]:
                        previous_data["initial_baselines"][initial_key] = current_stats
                        print(f"Set initial baseline for {player_name}")

                    if baseline_key not in previous_data["baselines"]:
                        previous_data["baselines"][baseline_key] = current_stats
                    baseline = previous_data["baselines"][baseline_key]
                    delta_stats = tuple(c - b for c, b in zip(current_stats, baseline)) if baseline else current_stats

                    previous_data.setdefault("daily", {}).setdefault(current_daily_start.isoformat(), {})[player_name] = delta_stats
                    previous_data.setdefault("weekly", {}).setdefault(current_weekly_start.isoformat(), {})[player_name] = delta_stats
                    previous_data.setdefault("monthly", {}).setdefault(current_monthly_start.isoformat(), {})[player_name] = delta_stats
                    previous_data.setdefault("yearly", {}).setdefault(current_yearly_start.isoformat(), {})[player_name] = delta_stats

                    previous_data["baselines"][baseline_key] = current_stats
                    all_player_data[player_name] = current_stats
            else:
                print(f"Player not found: {player_name}")
        except requests.exceptions.RequestException as e:
            print(f"Error communicating with Hypixel API: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        time.sleep(5)

    print("Saving updated data to player_stats.json...")
    try:
        with open("player_stats.json", "w") as f:
            json.dump(previous_data, f, indent=4)
        print("Player stats saved to player_stats.json")
    except Exception as e:
        print(f"Error saving data to file: {e}")

if __name__ == "__main__":
    print("Data retrieval loop started...")
    while True:
        retrieve_and_save_data()
        print("Sleeping for 15 minutes...")
        time.sleep(900)