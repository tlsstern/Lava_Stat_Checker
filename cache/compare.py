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
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return set(data.keys())
    except (json.JSONDecodeError, FileNotFoundError):
        return set()

def get_player_stats_from_file(filename, username):
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return data.get(username)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def normalize_modes(modes_dict):
    normalized = {}
    for mode, stats in modes_dict.items():
        key = mode.lower()
        if key not in normalized:
            normalized[key] = {}
        normalized[key].update(stats)
    return normalized

def calculate_gains(old_stats, new_stats):
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
                        new_val = float(str(new_value).replace(",", ""))
                        old_val = float(str(old_value).replace(",", ""))
                        mode_gains[stat] = new_val - old_val
                    except (ValueError, TypeError):
                        pass
            if mode_gains:
                gains[mode.capitalize()] = mode_gains
    return gains

def calculate_fkdr_gain(old_stats, new_stats):
    if not old_stats or not new_stats:
        return "N/A"
    try:
        norm_new_overall = normalize_modes(new_stats.get("modes", {})).get("overall", {})
        norm_old_overall = normalize_modes(old_stats.get("modes", {})).get("overall", {})
        if not norm_new_overall or not norm_old_overall:
            return "N/A"
        old_fk = float(str(norm_old_overall.get("final_kills", 0)).replace(",", ""))
        new_fk = float(str(norm_new_overall.get("final_kills", 0)).replace(",", ""))
        old_fd = float(str(norm_old_overall.get("final_deaths", 0)).replace(",", ""))
        new_fd = float(str(norm_new_overall.get("final_deaths", 0)).replace(",", ""))
        fk_gain = new_fk - old_fk
        fd_gain = new_fd - old_fd
        if fd_gain == 0:
            return "Infinite" if fk_gain > 0 else "0.00"
        return round(fk_gain / fd_gain, 2)
    except (ValueError, TypeError, KeyError):
        return "N/A"

def display_player_gains(username, old_stats, new_stats):
    old_ts = old_stats.get('last_updated', 'Unknown')
    new_ts = new_stats.get('last_updated', 'Unknown')
    player_gains = calculate_gains(old_stats, new_stats)
    fkdr_gain = calculate_fkdr_gain(old_stats, new_stats)
    
    width = 50
    header_text = f" 📊 STATS GAIN FOR: {username} "
    
    print(f"\n{C.BOLD}{C.BLUE}╔{header_text.center(width, '═')}╗{C.ENDC}")
    print(f"{C.BLUE}║{''.ljust(width)}║{C.ENDC}")
    print(f"{C.BLUE}║{C.YELLOW}{'From:'.ljust(8)}{old_ts.ljust(width - 8)}{C.BLUE}║{C.ENDC}")
    print(f"{C.BLUE}║{C.YELLOW}{'To:'.ljust(8)}{new_ts.ljust(width - 8)}{C.BLUE}║{C.ENDC}")
    print(f"{C.BLUE}║{''.ljust(width)}║{C.ENDC}")

    if not player_gains:
        no_data_text = "No comparable stats found."
        print(f"{C.BLUE}║{no_data_text.center(width)}{C.BLUE}║{C.ENDC}")
    else:
        mode_order = ["Overall", "Solos", "Doubles", "Threes", "Fours"]
        float_stats = {'fkdr', 'wlr', 'bblr', 'kdr'}
        
        present_modes = player_gains.keys()
        final_order = [mode for mode in mode_order if mode in present_modes]
        other_modes = sorted([mode for mode in present_modes if mode not in mode_order])
        final_order.extend(other_modes)

        for mode in final_order:
            gains = player_gains[mode]
            mode_header = f" {mode} "
            print(f"{C.BLUE}╠{C.BOLD}{mode_header.center(width, '─')}{C.BLUE}╣{C.ENDC}")
            
            has_printed_stat = False
            max_len = max(len(s.replace('_', ' ')) for s in gains.keys()) if gains else 0
            
            for stat, value in sorted(gains.items()):
                if value != 0:
                    has_printed_stat = True
                    stat_name = stat.replace('_', ' ').capitalize()
                    color = C.GREEN if value > 0 else C.RED
                    
                    if stat in float_stats:
                        value_str = f"{value:.2f}"
                    else:
                        value_str = f"{value:.0f}"
                    
                    left_part = f" {stat_name.ljust(max_len)} : "
                    right_part_colored = f"{color}{value_str}{C.ENDC}"
                    
                    total_len_inside_box = width
                    padding = total_len_inside_box - len(left_part) - len(value_str) -1
                    
                    line = f"{left_part}{' ' * padding}{right_part_colored} "
                    print(f"{C.BLUE}║{line}{C.BLUE}║{C.ENDC}")

            if not has_printed_stat:
                no_change_text = "No changes in this mode."
                print(f"{C.BLUE}║{no_change_text.center(width)}{C.BLUE}║{C.ENDC}")

    fkdr_header = " FKDR Gain (Overall) "
    print(f"{C.BLUE}╠{C.BOLD}{fkdr_header.center(width, '═')}{C.BLUE}╣{C.ENDC}")
    fkdr_line = f"{C.GREEN}{fkdr_gain}{C.ENDC}".center(width + len(C.GREEN) + len(C.ENDC))
    print(f"{C.BLUE}║{fkdr_line}{C.BLUE}║{C.ENDC}")
    print(f"{C.BLUE}╚{'═'.ljust(width, '═')}╝{C.ENDC}")


def main():
    print_banner()
    cache_files = glob.glob('cache_*.json')
    if not cache_files:
        print(f"{C.RED}No cache files found (e.g., 'cache_*.json'). Exiting.{C.ENDC}")
        return
    
    file1 = select_from_list(cache_files, "Choose the first file:")
    file2 = select_from_list(cache_files, "Choose the second file:")
    
    if not file1 or not file2:
        print(f"\n{C.RED}File selection cancelled. Exiting.{C.ENDC}")
        return
        
    users1 = get_usernames_from_file(file1)
    users2 = get_usernames_from_file(file2)
    common_users = sorted(list(users1.intersection(users2)))
    
    if not common_users:
        print(f"\n{C.RED}No common players found between {file1} and {file2}. Exiting.{C.ENDC}")
        return
        
    username = select_from_list(common_users, "Choose a player to compare (found in both files):")
    
    if not username:
        print(f"\n{C.RED}Player selection cancelled. Exiting.{C.ENDC}")
        return
        
    player_data1 = get_player_stats_from_file(file1, username)
    player_data2 = get_player_stats_from_file(file2, username)
    
    if not player_data1 or not player_data2:
        print(f"\n{C.RED}Could not retrieve data for the specified user in one of the files. Exiting.{C.ENDC}")
        return
        
    try:
        dt1 = datetime.fromisoformat(player_data1.get('last_updated'))
        dt2 = datetime.fromisoformat(player_data2.get('last_updated'))
        if dt1 < dt2:
            player_data_old = player_data1
            player_data_new = player_data2
        else:
            player_data_old = player_data2
            player_data_new = player_data1
            print(f"\n{C.CYAN}[INFO] Files were selected out of order. Swapping automatically.{C.ENDC}")
    except (TypeError, ValueError):
        print(f"\n{C.YELLOW}[WARNING] Could not parse 'last_updated' timestamp to automatically sort files.{C.ENDC}")
        player_data_old = player_data2
        player_data_new = player_data1
        
    display_player_gains(username, player_data_old, player_data_new)

if __name__ == "__main__":
    main()