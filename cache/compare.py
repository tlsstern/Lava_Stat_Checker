import json
import glob
from datetime import datetime

def select_from_list(items, prompt_message):
    if not items:
        return None
    print(prompt_message)
    for i, item in enumerate(items, 1):
        print(f"  {i}) {item}")
    while True:
        try:
            choice = int(input("Enter your choice (number): "))
            if 1 <= choice <= len(items):
                return items[choice - 1]
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

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
    print("\n" + "="*50)
    print(f"        📊 STATS GAIN FOR: {username}")
    print(f"        From: {old_ts}")
    print(f"        To:   {new_ts}")
    print("="*50)
    player_gains = calculate_gains(old_stats, new_stats)
    if not player_gains:
        print("\nNo comparable stats found or no change detected.")
        print("="*50)
        return
    
    # --- Custom Sort Order Logic ---
    mode_order = ["Overall", "Solos", "Doubles", "Threes", "Fours"]
    present_modes = player_gains.keys()
    final_order = [mode for mode in mode_order if mode in present_modes]
    other_modes = sorted([mode for mode in present_modes if mode not in mode_order])
    final_order.extend(other_modes)
    # --- End of Sort Logic ---

    for mode in final_order:
        gains = player_gains[mode]
        print(f"\n--- {mode} ---")
        has_printed_stat = False
        for stat, value in sorted(gains.items()):
            if value != 0:
                print(f"{stat.replace('_', ' ').capitalize()}: {value:+.2f}")
                has_printed_stat = True
        if not has_printed_stat:
             print("No changes in this mode.")
    fkdr_gain = calculate_fkdr_gain(old_stats, new_stats)
    print(f"\nFKDR Gain (Overall): {fkdr_gain}")
    print("="*50)

def main():
    cache_files = glob.glob('cache_*.json')
    if not cache_files:
        print("No cache files found (e.g., 'cache_*.json'). Exiting.")
        return
    print("--- Select Cache Files to Compare ---")
    file1 = select_from_list(cache_files, "Choose the first file:")
    file2 = select_from_list(cache_files, "Choose the second file:")
    if not file1 or not file2:
        print("File selection cancelled. Exiting.")
        return
    users1 = get_usernames_from_file(file1)
    users2 = get_usernames_from_file(file2)
    common_users = sorted(list(users1.intersection(users2)))
    if not common_users:
        print(f"\nNo common players found between {file1} and {file2}. Exiting.")
        return
    print("\n--- Select Player ---")
    username = select_from_list(common_users, "Choose a player to compare (found in both files):")
    if not username:
        print("Player selection cancelled. Exiting.")
        return
    player_data1 = get_player_stats_from_file(file1, username)
    player_data2 = get_player_stats_from_file(file2, username)
    if not player_data1 or not player_data2:
        print("\nCould not retrieve data for the specified user in one of the files. Exiting.")
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
            print("\n[INFO] Files were selected out of chronological order. Swapping them automatically.")
    except (TypeError, ValueError):
        print("\n[WARNING] Could not parse 'last_updated' timestamp to automatically sort files.")
        print("Displaying results based on selection order. This may be incorrect.")
        player_data_old = player_data2
        player_data_new = player_data1
    display_player_gains(username, player_data_old, player_data_new)

if __name__ == "__main__":
    main()