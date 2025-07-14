import json
import glob
from datetime import datetime

class C:
    """ANSI Color Codes"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'

def print_banner():
    """Prints a welcome banner."""
    print(f"{C.BOLD}{C.HEADER}╔{'═' * 52}╗{C.ENDC}")
    print(f"{C.BOLD}{C.HEADER}║ 📊 BedWars Stats Gain Calculator & Comparison Tool ║{C.ENDC}")
    print(f"{C.BOLD}{C.HEADER}╚{'═' * 52}╝{C.ENDC}")

def select_from_list(items, prompt_message):
    """Prompts the user to select an item from a list."""
    if not items:
        return None
    print(f"\n{C.BOLD}{C.YELLOW}{prompt_message}{C.ENDC}")
    for i, item in enumerate(items, 1):
        print(f"  {C.CYAN}{i}{C.ENDC}) {item}")
    while True:
        try:
            choice = int(input(f"{C.YELLOW} › Enter your choice: {C.ENDC}"))
            if 1 <= choice <= len(items):
                return items[choice - 1]
            else:
                print(f"{C.RED}Invalid number. Please try again.{C.ENDC}")
        except ValueError:
            print(f"{C.RED}Invalid input. Please enter a number.{C.ENDC}")

def get_usernames_from_file(filename):
    """Extracts all usernames (keys) from a JSON file."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return set(data.keys())
    except (json.JSONDecodeError, FileNotFoundError):
        return set()

def get_player_stats_from_file(filename, username):
    """Retrieves stats for a specific player from a JSON file."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return data.get(username)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def normalize_modes(modes_dict):
    """Normalizes mode names to lowercase to handle inconsistencies."""
    normalized = {}
    for mode, stats in modes_dict.items():
        key = mode.lower()
        if key not in normalized:
            normalized[key] = {}
        normalized[key].update(stats)
    return normalized

def calculate_gains(old_stats, new_stats):
    """Calculates the difference in stats between two data points."""
    gains = {}
    if not old_stats or not new_stats:
        return None
    norm_new_modes = normalize_modes(new_stats.get("modes", {}))
    norm_old_modes = normalize_modes(old_stats.get("modes", {}))
    for mode, new_mode_stats in norm_new_modes.items():
        if mode in norm_old_modes:
            old_mode_stats = norm_old_modes[mode]
            mode_gains = {}
            for stat, new_value in new_mode_stats.items():
                if stat in old_mode_stats:
                    old_value = old_mode_stats[stat]
                    try:
                        # Ensure values are treated as numbers
                        new_val = float(str(new_value).replace(",", ""))
                        old_val = float(str(old_value).replace(",", ""))
                        gain = new_val - old_val
                        if gain != 0:
                            mode_gains[stat] = gain
                    except (ValueError, TypeError):
                        pass # Ignore stats that can't be converted to numbers
            if mode_gains:
                gains[mode.capitalize()] = mode_gains
    return gains

def calculate_fkdr_gain(old_stats, new_stats, mode='overall'):
    """Calculates the FKDR for a session based on gains for a specific mode."""
    if not old_stats or not new_stats:
        return "N/A"
    try:
        # Use the mode parameter to get the correct stats
        norm_new_mode_stats = normalize_modes(new_stats.get("modes", {})).get(mode.lower(), {})
        norm_old_mode_stats = normalize_modes(old_stats.get("modes", {})).get(mode.lower(), {})

        if not norm_new_mode_stats or not norm_old_mode_stats:
            return "N/A"

        old_fk = float(str(norm_old_mode_stats.get("final_kills", 0)).replace(",", ""))
        new_fk = float(str(norm_new_mode_stats.get("final_kills", 0)).replace(",", ""))
        old_fd = float(str(norm_old_mode_stats.get("final_deaths", 0)).replace(",", ""))
        new_fd = float(str(norm_new_mode_stats.get("final_deaths", 0)).replace(",", ""))
        fk_gain = new_fk - old_fk
        fd_gain = new_fd - old_fd

        if fd_gain == 0:
            return "Infinite" if fk_gain > 0 else "0.00"
        return f"{fk_gain / fd_gain:.2f}"
    except (ValueError, TypeError, KeyError):
        return "N/A"

def display_player_gains(username, gains_data, old_stats, new_stats):
    """Displays a formatted table of player stat gains for a session."""
    width = 50
    header_text = f" 📊 SESSION GAINS FOR: {username} "
    
    print(f"\n{C.BOLD}{C.CYAN}╔{header_text.center(width, '═')}╗{C.ENDC}")

    if not gains_data:
        no_data_text = "No stat gains found for this session."
        print(f"{C.CYAN}║{no_data_text.center(width)}{C.CYAN}║{C.ENDC}")
    else:
        mode_order = ["Overall", "Solos", "Doubles", "Threes", "Fours"]
        
        present_modes = gains_data.keys()
        final_order = [mode for mode in mode_order if mode in present_modes]
        other_modes = sorted([mode for mode in present_modes if mode not in mode_order])
        final_order.extend(other_modes)

        for mode in final_order:
            stats = gains_data[mode]
            mode_header = f" {mode.capitalize()} "
            print(f"{C.CYAN}╠{C.BOLD}{mode_header.center(width, '─')}{C.CYAN}╣{C.ENDC}")
            
            # Calculate and display FKDR for the current mode
            mode_fkdr = calculate_fkdr_gain(old_stats, new_stats, mode=mode)
            if mode_fkdr != "N/A":
                fkdr_str = f"Session FKDR: {mode_fkdr}"
                centered_fkdr_str = fkdr_str.center(width)
                print(f"{C.CYAN}║{C.GREEN}{centered_fkdr_str}{C.CYAN}║{C.ENDC}")
                print(f"{C.CYAN}╠{'─' * width}╣{C.ENDC}")

            max_len = max(len(s.replace('_', ' ')) for s in stats.keys()) if stats else 0
            
            for stat, value in sorted(stats.items()):
                stat_name = stat.replace('_', ' ').capitalize()
                
                color = C.GREEN if value > 0 else C.RED
                
                if isinstance(value, float):
                    value_str = f"{value:+.2f}"
                else:
                    value_str = f"{int(value):+}"

                left_part = f" {stat_name.ljust(max_len)} : "
                padding = width - len(left_part) - len(value_str) - 1
                
                line = f"{left_part}{' ' * padding}{color}{value_str}{C.CYAN} "
                print(f"{C.CYAN}║{line}║{C.ENDC}")

    print(f"{C.CYAN}╚{'═'.ljust(width, '═')}╝{C.ENDC}")

def main():
    """Main function to run the stats comparison tool."""
    print_banner()
    cache_files = glob.glob('cache_*.json')
    if len(cache_files) < 2:
        print(f"{C.RED}Not enough cache files found. Need at least 2 to compare. Exiting.{C.ENDC}")
        return
    
    print(f"{C.YELLOW}Select the OLDER file first (the starting point).{C.ENDC}")
    file1 = select_from_list(cache_files, "Choose the FIRST (older) file:")
    if not file1:
        print(f"\n{C.RED}File selection cancelled. Exiting.{C.ENDC}")
        return

    print(f"\n{C.YELLOW}Now, select the NEWER file (the end point).{C.ENDC}")
    file2 = select_from_list(cache_files, "Choose the SECOND (newer) file:")
    if not file2:
        print(f"\n{C.RED}File selection cancelled. Exiting.{C.ENDC}")
        return

    if file1 == file2:
        print(f"\n{C.RED}You selected the same file twice. Exiting.{C.ENDC}")
        return
        
    users1 = get_usernames_from_file(file1)
    users2 = get_usernames_from_file(file2)
    
    common_users = sorted(list(users1.intersection(users2)))
    
    if not common_users:
        print(f"\n{C.RED}No common players found between {file1} and {file2}. Exiting.{C.ENDC}")
        return
        
    username = select_from_list(common_users, "Choose a player to compare stats for:")
    
    if not username:
        print(f"\n{C.RED}Player selection cancelled. Exiting.{C.ENDC}")
        return
        
    old_player_data = get_player_stats_from_file(file1, username)
    new_player_data = get_player_stats_from_file(file2, username)
    
    if not old_player_data or not new_player_data:
        print(f"\n{C.RED}Could not retrieve data for the specified user in one of the files. Exiting.{C.ENDC}")
        return
        
    gains = calculate_gains(old_player_data, new_player_data)
    
    if not gains:
        print(f"\n{C.YELLOW}No stat gains to display for {username}.{C.ENDC}")
        return

    display_player_gains(username, gains, old_player_data, new_player_data)

if __name__ == "__main__":
    main()
