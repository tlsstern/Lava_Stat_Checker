import json
import requests
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
import math

# Powered by Google-Switzerland Workforce
console = Console()

console.print("Starting lifetime_stat_checker.py...", style="bold green")

# Load Hypixel API key from key.txt
def load_api_key():
    """Load the Hypixel API key from key.txt."""
    try:
        with open("key.txt", "r") as f:
            api_key = f.read().strip()  # Read and remove any whitespace/newlines
            if not api_key:
                raise ValueError("key.txt is empty")
            return api_key
    except FileNotFoundError:
        console.print("Error: key.txt not found in the current directory.", style="red")
        raise
    except Exception as e:
        console.print(f"Error reading key.txt: {e}", style="red")
        raise

HYPIXEL_API_KEY = load_api_key()  # Load the API key

def get_bedwars_level(exp: int):
    """
    Detirms Star by Experience.
    """
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
    # Fetches Stats from hypixel <3
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

            stats = (wins, losses, beds_broken, beds_lost, final_kills, final_deaths, kills, deaths, stars)
            console.print(f"Stats fetched: {stats[:9]}...", style="dim")
            return stats
        else:
            console.print(f"No Bedwars stats found for UUID: {uuid}", style="yellow")
            return None
    except requests.exceptions.RequestException as e:
        console.print(f"API error: {e}", style="red")
        return None

def calculate_stats(stats):
    """
    Calculate WLR, FKDR, BBLR, KDR and round to .00
    """
    wins, losses, beds_broken, beds_lost, final_kills, final_deaths, kills, deaths, stars = stats
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
        "KDR": round(kills / deaths, 2) if deaths else "N/A"
    }

def display_stats(player_name):
    """
    Returns the Stats in a nice Format (Thanks Gemini for the layout <3)
    """
    console.print(f"\nDisplaying lifetime stats for [bold cyan]{player_name}[/bold cyan]")
    uuid_response = requests.get(f"https://api.hypixel.net/player?key={HYPIXEL_API_KEY}&name={player_name}", timeout=10)
    console.print(f"UUID fetch status for {player_name}: {uuid_response.status_code}", style="dim")
    uuid_data = uuid_response.json()
    if uuid_data["success"] and uuid_data["player"] is not None:
        uuid = uuid_data["player"]["uuid"]
        stats = get_hypixel_stats(uuid)

        if stats:
            calculated_stats = calculate_stats(stats)
            table = Table(title=f"Bedwars Lifetime Stats for {player_name}", style="cyan", title_style="bold")
            table.add_column("Statistic", style="magenta", justify="left")
            table.add_column("Value", style="green", justify="right")

            # Username
            table.add_row("Username", player_name)
            table.add_row("--- General ---", "")  # Separator

            # General Stats (Stars only)
            table.add_row("Stars", str(calculated_stats["Stars"]))

            # Wins Section
            table.add_row("--- Wins ---", "")  # Separator
            table.add_row("Wins", str(calculated_stats["Wins"]))
            table.add_row("Losses", str(calculated_stats["Losses"]))
            table.add_row("WLR", str(calculated_stats["WLR"]))

            # Finals Section
            table.add_row("--- Finals ---", "")  # Separator
            table.add_row("Final Kills", str(calculated_stats["Final Kills"]))
            table.add_row("Final Deaths", str(calculated_stats["Final Deaths"]))
            table.add_row("FKDR", str(calculated_stats["FKDR"]))

            # Beds Section (New)
            table.add_row("--- Beds ---", "")  # Separator
            table.add_row("Beds Broken", str(calculated_stats["Beds Broken"]))
            table.add_row("Beds Lost", str(calculated_stats["Beds Lost"]))
            table.add_row("BBLR", str(calculated_stats["BBLR"]))

            # Regular Section
            table.add_row("--- Regular ---", "")  # Separator
            table.add_row("Kills", str(calculated_stats["Kills"]))
            table.add_row("Deaths", str(calculated_stats["Deaths"]))
            table.add_row("KDR", str(calculated_stats["KDR"]))

            console.print(table)
        else:
            console.print(f"No stats found for [bold cyan]{player_name}[/bold cyan]", style="red")
    else:
        console.print(f"Failed to fetch UUID for {player_name}", style="yellow")

if __name__ == "__main__":
    console.print("[bold]Lifetime Stat Checker Script Started[/bold]", style="green")
    try:
        console.print("\n[italic]Welcome to the Bedwars Lifetime Stat Checker![/italic]", style="cyan")
        player_name = Prompt.ask("[bold yellow]Enter player name[/bold yellow]")
        console.print(f"Player name entered: [cyan]{player_name}[/cyan]")

        display_stats(player_name)
    except KeyboardInterrupt:
        console.print("\nScript terminated by user", style="yellow")
    except Exception as e:
        console.print(f"Unexpected error: {e}", style="red")