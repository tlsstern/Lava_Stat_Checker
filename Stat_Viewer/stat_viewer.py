import json
import datetime
import pytz
import requests
import math
import os
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

console = Console()

console.print("Starting stat_viewer.py...", style="bold green")

CHEST_TZ = pytz.timezone("Europe/Paris")

# Load Hypixel API key from key.txt
def load_api_key():
    try:
        with open("key.txt", "r") as f:
            api_key = f.read().strip()
            if not api_key:
                raise ValueError("key.txt is empty")
            return api_key
    except FileNotFoundError:
        console.print("Error: key.txt not found in the current directory.", style="red")
        raise
    except Exception as e:
        console.print(f"Error reading key.txt: {e}", style="red")
        raise

HYPIXEL_API_KEY = load_api_key()

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

def get_available_json_files():
    return [f for f in os.listdir() if f.endswith(".json")]

def load_data(file_name):
    console.print(f"Loading {file_name}...", style="dim")
    try:
        with open(file_name, "r") as f:
            data = json.load(f)
            console.print(f"Successfully loaded {file_name}", style="dim")
            return data
    except FileNotFoundError:
        console.print(f"{file_name} not found.", style="yellow")
        return None
    except Exception as e:
        console.print(f"Error loading data: {e}", style="red")
        return None

def get_hypixel_stats(uuid):
    console.print(f"Fetching stats for UUID: {uuid}", style="dim")
    try:
        response = requests.get(f"https://api.hypixel.net/player?key={HYPIXEL_API_KEY}&uuid={uuid}", timeout=10)
        console.print(f"API response status: {response.status_code}", style="dim")
        response.raise_for_status()
        data = response.json()
        if data["success"] and data["player"] is not None and "Bedwars" in data["player"].get("stats", {}):
            bedwars_stats = data["player"]["stats"]["Bedwars"]
            wins = bedwars_stats.get("wins_bedwars", 0)
            losses = bedwars_stats.get("losses_bedwars", 0)
            beds_broken = bedwars_stats.get("beds_broken_bedwars", 0)
            beds_lost = bedwars_stats.get("beds_lost_bedwars", 0)
            final_kills = bedwars_stats.get("final_kills_bedwars", 0)
            final_deaths = bedwars_stats.get("final_deaths_bedwars", 0)
            kills = bedwars_stats.get("kills_bedwars", 0)
            deaths = bedwars_stats.get("deaths_bedwars", 0)
            exp = bedwars_stats.get("Experience", 0)
            stars = get_bedwars_level(exp)
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
            stats = (wins, losses, beds_broken, beds_lost, final_kills, final_deaths, kills, deaths, stars,
                     solo_wins, solo_losses, 0, 0, doubles_wins, doubles_losses, 0, 0,
                     threes_wins, threes_losses, 0, 0, fours_wins, fours_losses, 0, 0,
                     four_v_four_wins, four_v_four_losses, 0, 0, 0, 0)
            return stats
        else:
            console.print(f"No Bedwars stats found for UUID: {uuid}", style="yellow")
            return None
    except requests.exceptions.RequestException as e:
        console.print(f"API error: {e}", style="red")
        return None

def calculate_stats(stats):
    wins, losses, beds_broken, beds_lost, final_kills, final_deaths, kills, deaths, stars, \
    solo_wins, solo_losses, solo_final_kills, solo_final_deaths, \
    doubles_wins, doubles_losses, doubles_final_kills, doubles_final_deaths, \
    threes_wins, threes_losses, threes_final_kills, threes_final_deaths, \
    fours_wins, fours_losses, fours_final_kills, fours_final_deaths, \
    four_v_four_wins, four_v_four_losses, four_v_four_final_kills, four_v_four_final_deaths, \
    overall_final_kills, overall_final_deaths = stats
    return {
        "Stars": math.floor(stars),
        "Wins": wins,
        "Losses": losses,
        "WLR": round(wins / losses, 2) if losses else "N/A",
        "Beds Broken": beds_broken,
        "Beds Lost": beds_lost,
        "BBLR": round(beds_broken / beds_lost, 2) if beds_lost else "N/A",
        "Final Kills": final_kills,
        "Final Deaths": final_deaths,
        "FKDR": round(final_kills / final_deaths, 2) if final_deaths else "N/A",
        "Kills": kills,
        "Deaths": deaths,
        "KDR": round(kills / deaths, 2) if deaths else "N/A",
        "Solo Wins": solo_wins,
        "Solo Losses": solo_losses,
        "Doubles Wins": doubles_wins,
        "Doubles Losses": doubles_losses,
        "Threes Wins": threes_wins,
        "Threes Losses": threes_losses,
        "Fours Wins": fours_wins,
        "Fours Losses": fours_losses,
        "4v4 Wins": four_v_four_wins,
        "4v4 Losses": four_v_four_losses
    }

def calculate_delta(current_stats, initial_stats):
    if not initial_stats:
        console.print("No initial baseline available, assuming starting from zero.", style="yellow")
        return current_stats
    return tuple(c - i for c, i in zip(current_stats, initial_stats))

def get_period_stats(data, player_name, period, file_name):
    now = datetime.datetime.now(CHEST_TZ)
    
    if period == "daily":
        start = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now < start:
            start -= datetime.timedelta(days=1)
        key = start.isoformat()
        return data["daily"].get(key, {}).get(player_name)
    
    elif period == "weekly":
        start = (now - datetime.timedelta(days=now.weekday())).replace(hour=5, minute=0, second=0, microsecond=0)
        key = start.isoformat()
        return data["weekly"].get(key, {}).get(player_name)
    
    elif period == "monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        key = start.isoformat()
        return data["monthly"].get(key, {}).get(player_name)
    
    elif period == "overall":
        uuid_response = requests.get(f"https://api.hypixel.net/player?key={HYPIXEL_API_KEY}&name={player_name}", timeout=10)
        uuid_data = uuid_response.json()
        if uuid_data["success"] and uuid_data["player"] is not None:
            uuid = uuid_data["player"]["uuid"]
            current_stats = get_hypixel_stats(uuid)
            if current_stats:
                initial_stats = data["initial_baselines"].get(f"{uuid}_total", None)
                return calculate_delta(current_stats, initial_stats)
        return None
    
    elif period == "lifetime":
        uuid_response = requests.get(f"https://api.hypixel.net/player?key={HYPIXEL_API_KEY}&name={player_name}", timeout=10)
        uuid_data = uuid_response.json()
        if uuid_data["success"] and uuid_data["player"] is not None:
            uuid = uuid_data["player"]["uuid"]
            return get_hypixel_stats(uuid)
        return None
    
    elif period == "file":
        # For tracker_interpreter-like behavior: read directly from the file
        if "baselines" in data:
            for key, stats in data["baselines"].items():
                if key.startswith(player_name.lower()):
                    return stats
        elif "daily" in data:
            for date, players in data["daily"].items():
                if player_name in players:
                    return players[player_name]
        else:
            for date, players in data.items():
                if player_name in players:
                    return players[player_name]
        return None

def display_stats(player_name, stats, file_name, period):
    calculated_stats = calculate_stats(stats)
    table = Table(title=f"Bedwars Stats for {player_name} ({period}) from {file_name}", style="cyan", title_style="bold")
    table.add_column("Statistic", style="magenta", justify="left")
    table.add_column("Value", style="green", justify="right")
    
    table.add_row("Username", player_name)
    table.add_row("--- General ---", "")
    table.add_row("Stars", str(calculated_stats["Stars"]))
    table.add_row("--- Wins ---", "")
    table.add_row("Wins", str(calculated_stats["Wins"]))
    table.add_row("Losses", str(calculated_stats["Losses"]))
    table.add_row("WLR", str(calculated_stats["WLR"]))
    table.add_row("--- Finals ---", "")
    table.add_row("Final Kills", str(calculated_stats["Final Kills"]))
    table.add_row("Final Deaths", str(calculated_stats["Final Deaths"]))
    table.add_row("FKDR", str(calculated_stats["FKDR"]))
    table.add_row("--- Beds ---", "")
    table.add_row("Beds Broken", str(calculated_stats["Beds Broken"]))
    table.add_row("Beds Lost", str(calculated_stats["Beds Lost"]))
    table.add_row("BBLR", str(calculated_stats["BBLR"]))
    table.add_row("--- Regular ---", "")
    table.add_row("Kills", str(calculated_stats["Kills"]))
    table.add_row("Deaths", str(calculated_stats["Deaths"]))
    table.add_row("KDR", str(calculated_stats["KDR"]))
    table.add_row("--- Solo ---", "")
    table.add_row("Solo Wins", str(calculated_stats["Solo Wins"]))
    table.add_row("Solo Losses", str(calculated_stats["Solo Losses"]))
    table.add_row("--- Doubles ---", "")
    table.add_row("Doubles Wins", str(calculated_stats["Doubles Wins"]))
    table.add_row("Doubles Losses", str(calculated_stats["Doubles Losses"]))
    table.add_row("--- Threes ---", "")
    table.add_row("Threes Wins", str(calculated_stats["Threes Wins"]))
    table.add_row("Threes Losses", str(calculated_stats["Threes Losses"]))
    table.add_row("--- Fours ---", "")
    table.add_row("Fours Wins", str(calculated_stats["Fours Wins"]))
    table.add_row("Fours Losses", str(calculated_stats["Fours Losses"]))
    table.add_row("--- 4v4 ---", "")
    table.add_row("4v4 Wins", str(calculated_stats["4v4 Wins"]))
    table.add_row("4v4 Losses", str(calculated_stats["4v4 Losses"]))
    
    console.print(table)

def main():
    console.print("[bold]Stat Viewer Script Started[/bold]", style="green")
    try:
        console.print("\n[italic]Welcome to the Bedwars Stat Viewer![/italic]", style="cyan")
        
        # Step 1: Select JSON file
        json_files = get_available_json_files()
        if not json_files:
            console.print("No .json files found in the current directory.", style="red")
            return
        
        console.print("\nAvailable .json files:")
        for i, file_name in enumerate(json_files, 1):
            console.print(f"{i}. {file_name}")
        file_choice = Prompt.ask("[bold yellow]Enter the number of the .json file to read[/bold yellow]", default="1")
        file_choice = int(file_choice) - 1
        if file_choice < 0 or file_choice >= len(json_files):
            console.print("Invalid selection.", style="red")
            return
        file_name = json_files[file_choice]
        console.print(f"Selected file: [cyan]{file_name}[/cyan]")
        
        # Step 2: Load data and select player
        data = load_data(file_name)
        if not data:
            return
        
        # Extract available players
        players = set()
        if "daily" in data:
            for date, player_data in data["daily"].items():
                players.update(player_data.keys())
        elif "baselines" in data:
            for key in data["baselines"]:
                player_name = key.split("_")[0]
                players.add(player_name)
        else:
            for date, player_data in data.items():
                players.update(player_data.keys())
        
        if not players:
            console.print("No players found in the selected file.", style="red")
            return
        
        console.print("\nAvailable usernames in this file:")
        player_list = sorted(list(players))
        for i, player in enumerate(player_list, 1):
            console.print(f"{i}. {player}")
        player_choice = Prompt.ask("[bold yellow]Enter the number of the username to view[/bold yellow]", default="1")
        player_choice = int(player_choice) - 1
        if player_choice < 0 or player_choice >= len(player_list):
            console.print("Invalid selection.", style="red")
            return
        player_name = player_list[player_choice]
        console.print(f"Selected username: [cyan]{player_name}[/cyan]")
        
        # Step 3: Select period
        if file_name == "player_stats.json":
            valid_periods = ["daily", "weekly", "monthly", "overall", "lifetime"]
            console.print("\nValid periods: [italic]daily, weekly, monthly, overall, lifetime[/italic]", style="dim")
            period = Prompt.ask("[bold yellow]Enter period[/bold yellow]").lower()
            if period not in valid_periods:
                console.print("Invalid period.", style="red")
                return
        else:
            period = "file"  # For non-player_stats.json files, use the file directly
        
        # Step 4: Display stats
        stats = get_period_stats(data, player_name, period, file_name)
        if stats:
            display_stats(player_name, stats, file_name, period)
        else:
            console.print(f"No stats found for [bold cyan]{player_name}[/bold cyan] in [bold magenta]{period}[/bold magenta] period", style="red")
    
    except KeyboardInterrupt:
        console.print("\nScript terminated by user", style="yellow")
    except Exception as e:
        console.print(f"Unexpected error: {e}", style="red")

if __name__ == "__main__":
    main()