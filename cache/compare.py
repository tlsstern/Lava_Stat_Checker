import json

def compare_player_stats(file1, file2, username1, username2):
    """
    Compares player stats from two different files for two different users.

    Args:
        file1 (str): The path to the first JSON file.
        file2 (str): The path to the second JSON file.
        username1 (str): The username of the first player.
        username2 (str): The username of the second player.
    """

    with open(file1) as f1, open(file2) as f2:
        data1 = json.load(f1)
        data2 = json.load(f2)

    player1_data_new = data1.get(username1)
    player1_data_old = data2.get(username1)

    player2_data_new = data1.get(username2)
    player2_data_old = data2.get(username2)


    def calculate_gains(old_stats, new_stats):
        gains = {}
        if not old_stats or not new_stats:
            return None

        for mode, new_mode_stats in new_stats["modes"].items():
            if mode in old_stats["modes"]:
                old_mode_stats = old_stats["modes"][mode]
                mode_gains = {}
                for stat, new_value in new_mode_stats.items():
                    if stat in old_mode_stats:
                        old_value = old_mode_stats[stat]
                        # Convert to float for calculation, handling commas
                        try:
                            new_val = float(str(new_value).replace(",", ""))
                            old_val = float(str(old_value).replace(",", ""))
                            mode_gains[stat] = new_val - old_val
                        except (ValueError, TypeError):
                            pass
                gains[mode] = mode_gains
        return gains

    def calculate_fkdr_gain(old_stats, new_stats):
        if not old_stats or not new_stats:
            return "N/A"
        try:
            old_fk = float(str(old_stats["modes"]["overall"]["final_kills"]).replace(",", ""))
            new_fk = float(str(new_stats["modes"]["overall"]["final_kills"]).replace(",", ""))
            old_fd = float(str(old_stats["modes"]["overall"]["final_deaths"]).replace(",", ""))
            new_fd = float(str(new_stats["modes"]["overall"]["final_deaths"]).replace(",", ""))
            if (new_fd - old_fd) == 0:
                return "Infinite"
            return round((new_fk - old_fk) / (new_fd - old_fd), 2)
        except (ValueError, TypeError, KeyError):
            return "N/A"


    player1_gains = calculate_gains(player1_data_old, player1_data_new)
    player2_gains = calculate_gains(player2_data_old, player2_data_new)

    print(f"Stats gain for {username1}:")
    if player1_gains:
        for mode, gains in player1_gains.items():
            print(f"\n--- {mode.capitalize()} ---")
            for stat, value in gains.items():
                print(f"{stat.replace('_', ' ').capitalize()}: {value:+.2f}")
        print("\nFKDR Gain (Overall):", calculate_fkdr_gain(player1_data_old, player1_data_new))

    print(f"\n\nStats gain for {username2}:")
    if player2_gains:
        for mode, gains in player2_gains.items():
            print(f"\n--- {mode.capitalize()} ---")
            for stat, value in gains.items():
                print(f"{stat.replace('_', ' ').capitalize()}: {value:+.2f}")
    else:
        print(f"No data found for {username2} in one of the files.")


# --- Execution ---
compare_player_stats('cache_10_07_2025.json', 'cache_04_07_2025.json', 'wlnks', 'ohDevil')