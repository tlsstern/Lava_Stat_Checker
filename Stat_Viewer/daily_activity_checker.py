import json
import os
import datetime
import pytz
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

# Initialize rich console for pretty output
console = Console()

console.print("Starting daily_activity_checker.py...", style="bold green")

def get_available_json_files():
    """Return a list of all .json files in the current directory."""
    json_files = [f for f in os.listdir(".") if f.endswith(".json")]
    return json_files

def check_daily_activity(file_data, target_date):
    """
    Check which players have non-zero daily stats for the target date.
    Returns a list of active usernames.
    """
    active_players = []
    chest_tz = pytz.timezone("Europe/Paris")  # Match the timezone used in retrieval script
    if "daily" in file_data:
        for timestamp, players in file_data["daily"].items():
            # Convert timestamp to datetime with CET/CEST timezone
            file_date = datetime.datetime.fromisoformat(timestamp).astimezone(chest_tz).date()
            if file_date == target_date:
                for username, stats in players.items():
                    # Check if any stat is non-zero (indicating activity)
                    if any(stat != 0 for stat in stats):
                        active_players.append(username)
                break  # Assume one daily entry per file, take the first match
    elif "baselines" in file_data:
        console.print("Baseline files don't contain delta stats. Please use a tracker file or player_stats.json with daily data.", style="yellow")
    return active_players

def main():
    console.print("[bold]Daily Activity Checker Script Started[/bold]", style="green")
    try:
        console.print("\n[italic]Welcome to the Bedwars Daily Activity Checker![/italic]", style="cyan")
        
        # Get available .json files
        json_files = get_available_json_files()
        if not json_files:
            console.print("No .json files found in the current directory.", style="red")
            return
        
        console.print("\nAvailable .json files:", style="dim")
        for i, file in enumerate(json_files, 1):
            console.print(f"{i}. {file}", style="cyan")
        
        while True:
            selection = Prompt.ask("[bold yellow]Enter the number of the .json file to check[/bold yellow]", default="1")
            try:
                selection = int(selection) - 1
                if 0 <= selection < len(json_files):
                    selected_file = json_files[selection]
                    break
                else:
                    console.print("Invalid selection. Please enter a number between 1 and {}".format(len(json_files)), style="red")
            except ValueError:
                console.print("Please enter a valid number.", style="red")
        
        console.print(f"Selected file: [cyan]{selected_file}[/cyan]")
        
        # Ask for target date
        while True:
            target_date_str = Prompt.ask("[bold yellow]Enter target date (DD-MM-YYYY)[/bold yellow]", default=datetime.datetime.now(pytz.UTC).strftime("%d-%m-%Y"))
            try:
                target_date = datetime.datetime.strptime(target_date_str, "%d-%m-%Y").date()
                break
            except ValueError:
                console.print("Invalid date format. Please use DD-MM-YYYY (e.g., 27-02-2025).", style="red")
        
        console.print(f"Checking activity for [cyan]{target_date_str}[/cyan] in [cyan]{selected_file}[/cyan]")
        
        # Load the selected file
        try:
            with open(selected_file, "r") as f:
                data = json.load(f)
                active_players = check_daily_activity(data, target_date)
                
                if active_players:
                    table = Table(title=f"Players Active on {target_date_str} from {selected_file}", style="cyan", title_style="bold")
                    table.add_column("Username", style="magenta", justify="left")
                    for player in active_players:
                        table.add_row(player)
                    console.print(table)
                else:
                    console.print(f"No players found active on [cyan]{target_date_str}[/cyan] in [cyan]{selected_file}[/cyan]", style="yellow")
        except Exception as e:
            console.print(f"Error loading {selected_file}: {e}", style="red")
    
    except KeyboardInterrupt:
        console.print("\nScript terminated by user", style="yellow")
    except Exception as e:
        console.print(f"Unexpected error: {e}", style="red")

if __name__ == "__main__":
    main()