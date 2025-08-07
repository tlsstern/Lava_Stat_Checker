import json
from datetime import datetime, timedelta
from supabase_handler import supabase_handler
from typing import Dict, List, Optional, Tuple

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
    print(f"{C.BOLD}{C.HEADER}║ 📊 BedWars Stats Comparison Tool (Supabase) 📊    ║{C.ENDC}")
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

def get_available_players() -> List[str]:
    """Get list of players with stats in Supabase."""
    if not supabase_handler.client:
        print(f"{C.RED}Supabase connection not available.{C.ENDC}")
        return []
    
    try:
        # Get unique player names from stats table
        result = supabase_handler.client.table('stats').select('player_name').execute()
        if result.data:
            # Remove duplicates and sort
            players = list(set(record['player_name'] for record in result.data))
            return sorted(players, key=str.lower)
        return []
    except Exception as e:
        print(f"{C.RED}Error fetching players: {e}{C.ENDC}")
        return []

def get_player_history(player_name: str, days_back: int = 30) -> List[Dict]:
    """Get historical stats for a player from Supabase."""
    if not supabase_handler.client:
        return []
    
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Query stats within date range
        result = supabase_handler.client.table('stats')\
            .select('*')\
            .eq('player_name', player_name)\
            .gte('created_at', start_date.isoformat())\
            .lte('created_at', end_date.isoformat())\
            .order('created_at', desc=False)\
            .execute()
        
        if result.data:
            return result.data
        return []
    except Exception as e:
        print(f"{C.RED}Error fetching player history: {e}{C.ENDC}")
        return []

def format_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return timestamp_str

def parse_stats_from_record(record: Dict) -> Dict:
    """Parse stats from a database record into the expected format."""
    # Parse detailed_stats JSON if it exists
    detailed_stats = {}
    if record.get('detailed_stats'):
        try:
            detailed_stats = json.loads(record['detailed_stats'])
        except:
            pass
    
    # Build modes structure from database columns
    overall = {
        'wins': record.get('wins', 0),
        'losses': record.get('losses', 0),
        'wlr': float(record.get('wlr', 0)),
        'final_kills': record.get('finals', 0),
        'final_deaths': record.get('final_deaths', 0),
        'fkdr': float(record.get('fkdr', 0)),
        'beds_broken': record.get('beds_broken', 0),
        'beds_lost': record.get('beds_lost', 0),
        'bblr': float(record.get('bblr', 0)),
        'kills': record.get('kills', 0),
        'deaths': record.get('deaths', 0),
        'kdr': float(record.get('kdr', 0)),
        'games_played': record.get('wins', 0) + record.get('losses', 0)
    }
    
    # Start with overall mode
    modes = {'overall': overall}
    
    # Add other modes from detailed_stats if available
    if 'modes' in detailed_stats:
        for mode_key, mode_data in detailed_stats['modes'].items():
            if mode_key != 'overall':
                modes[mode_key] = mode_data
    
    return {
        'username': record['player_name'],
        'level': record.get('level', 0),
        'modes': modes,
        'timestamp': record.get('created_at'),
        'fetched_from': record.get('fetched_from', 'unknown')
    }

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

def display_player_gains(username, gains_data, old_stats, new_stats, old_timestamp, new_timestamp):
    """Displays a formatted table of player stat gains for a session."""
    width = 60
    header_text = f" 📊 SESSION GAINS FOR: {username} "
    
    print(f"\n{C.BOLD}{C.CYAN}╔{header_text.center(width, '═')}╗{C.ENDC}")
    
    # Display time period
    time_info = f"From: {format_timestamp(old_timestamp)}"
    print(f"{C.CYAN}║{C.YELLOW}{time_info.center(width)}{C.CYAN}║{C.ENDC}")
    time_info = f"To:   {format_timestamp(new_timestamp)}"
    print(f"{C.CYAN}║{C.YELLOW}{time_info.center(width)}{C.CYAN}║{C.ENDC}")
    print(f"{C.CYAN}╠{'═' * width}╣{C.ENDC}")

    if not gains_data:
        no_data_text = "No stat gains found for this period."
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
    
    # Check Supabase connection
    if not supabase_handler.client:
        print(f"{C.RED}Error: Supabase connection not configured.{C.ENDC}")
        print(f"{C.YELLOW}Please set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file{C.ENDC}")
        return
    
    # Get available players
    print(f"\n{C.YELLOW}Fetching available players from Supabase...{C.ENDC}")
    players = get_available_players()
    
    if not players:
        print(f"{C.RED}No players found in database. Play some games first!{C.ENDC}")
        return
    
    # Select player
    player = select_from_list(players, "Choose a player to view stats history:")
    if not player:
        print(f"\n{C.RED}Player selection cancelled. Exiting.{C.ENDC}")
        return
    
    # Get player history
    print(f"\n{C.YELLOW}Fetching stats history for {player}...{C.ENDC}")
    history = get_player_history(player, days_back=30)
    
    if len(history) < 2:
        print(f"{C.RED}Not enough historical data. Need at least 2 data points to compare.{C.ENDC}")
        return
    
    # Format history for selection
    history_options = []
    for i, record in enumerate(history):
        timestamp = format_timestamp(record['created_at'])
        source = record.get('fetched_from', 'unknown')
        level = record.get('level', 0)
        history_options.append(f"{timestamp} | Level {level} | Source: {source}")
    
    # Select first data point
    print(f"\n{C.YELLOW}Select the OLDER data point (starting point):{C.ENDC}")
    choice1_idx = select_from_list(history_options, "Choose the FIRST (older) data point:")
    if choice1_idx is None:
        print(f"\n{C.RED}Selection cancelled. Exiting.{C.ENDC}")
        return
    
    # Get index from selection
    idx1 = history_options.index(choice1_idx)
    
    # Select second data point
    print(f"\n{C.YELLOW}Select the NEWER data point (end point):{C.ENDC}")
    choice2_idx = select_from_list(history_options, "Choose the SECOND (newer) data point:")
    if choice2_idx is None:
        print(f"\n{C.RED}Selection cancelled. Exiting.{C.ENDC}")
        return
    
    # Get index from selection
    idx2 = history_options.index(choice2_idx)
    
    if idx1 == idx2:
        print(f"\n{C.RED}You selected the same data point twice. Exiting.{C.ENDC}")
        return
    
    # Parse stats from selected records
    old_stats = parse_stats_from_record(history[idx1])
    new_stats = parse_stats_from_record(history[idx2])
    
    # Calculate gains
    gains = calculate_gains(old_stats, new_stats)
    
    if not gains:
        print(f"\n{C.YELLOW}No stat changes between these two data points.{C.ENDC}")
        return
    
    # Display gains
    display_player_gains(
        player, 
        gains, 
        old_stats, 
        new_stats,
        history[idx1]['created_at'],
        history[idx2]['created_at']
    )

if __name__ == "__main__":
    main()