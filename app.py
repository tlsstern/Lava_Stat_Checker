# Lava_Stat_Checker/app.py
from flask import Flask, render_template, jsonify, request, redirect, url_for
import hypixel_api
import os
import datetime
from supabase_handler import supabase_handler

app = Flask(__name__)

# ... (keep existing setup code and helper functions like calculate_ratio, format_number, etc.) ...
if not os.path.exists('static'): os.makedirs('static')
if not os.path.exists('static/css'): os.makedirs('static/css')
if not os.path.exists('static/js'): os.makedirs('static/js')
if not os.path.exists('templates'): os.makedirs('templates')

def calculate_ratio(numerator, denominator):
    """Helper to calculate ratio, handling division by zero and None inputs."""
    numerator = float(numerator) if numerator is not None else 0
    denominator = float(denominator) if denominator is not None else 0
    if denominator == 0:
        return float(numerator) if numerator != 0 else 0.0
    return round(numerator / denominator, 2)

def calculate_win_rate(wins, games_played):
    """Helper to calculate win rate, handling division by zero and None inputs."""
    wins = float(wins) if wins is not None else 0
    games_played = float(games_played) if games_played is not None else 0
    if games_played == 0:
        return 0.0
    return round((wins / games_played) * 100, 2)

def calculate_finals_per_game(final_kills, games_played):
     """Helper to calculate finals per game, handling division by zero and None inputs."""
     final_kills = float(final_kills) if final_kills is not None else 0
     games_played = float(games_played) if games_played is not None else 0
     if games_played == 0:
        return final_kills
     return round(final_kills / games_played, 2)

def format_number(value):
    """Formats a number with apostrophe as thousand separator, returns N/A for None/invalid."""
    if value is None:
        return 'N/A'
    try:
        return "{:,}".format(int(float(value))).replace(',', "'")
    except (ValueError, TypeError):
        return 'N/A'

def time_ago(dt, now=None):
    """Returns a 'time ago' string for a given datetime object."""
    if now is None:
        now = datetime.datetime.now()
    diff = now - dt

    seconds = int(diff.total_seconds())
    if seconds < 5: # Consider anything less than 5 seconds as "just now"
        return "just now"
    if seconds < 60:
        return f"{seconds} seconds ago"
    minutes = round(seconds / 60)
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = round(minutes / 60)
    if hours < 24:
        return f"{hours} hours ago"
    days = round(hours / 24)
    return f"{days} days ago"

def get_safe_int(value):
    """Converts a value to an integer, returning 0 if None or invalid."""
    if value is None:
        return 0
    try:
        return int(float(str(value).replace(',', '')))
    except (ValueError, TypeError):
        return 0
        
def get_safe_level(value):
    if value is None:
        return None
    s_value = str(value)
    cleaned_digits = [char for char in s_value if '0' <= char <= '9']
    cleaned_string = "".join(cleaned_digits)
    if not cleaned_string:
        return None
    try:
        return int(cleaned_string)
    except ValueError:
        return None

def transform_scrapper_data(scraped_data):
    """
    Transforms scrapper data from bwstats.shivam.pro to the app's standard structure.
    """
    if not scraped_data or scraped_data.get('error'):
        return scraped_data

    print(f"Debug transform_scrapper_data - Input keys: {scraped_data.keys() if scraped_data else 'None'}")
    username = scraped_data.get('username')
    player_uuid = None
    if username:
        try:
            import requests
            response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and 'id' in data:
                    player_uuid = data.get('id')
        except Exception as e:
            print(f"Error getting UUID from Mojang for {username}: {e}")

    final_modes = {}
    scraped_modes = scraped_data.get('modes', {})
    print(f"Debug: scraped_modes keys: {scraped_modes.keys()}")
    
    # First, process all modes from the scraper
    for mode_key, mode_data in scraped_modes.items():
        processed_mode = {}
        for key, value in mode_data.items():
            # Always convert numerical stats to integers, ignore pre-calculated ratios from scraper
            if key not in ['wlr', 'kdr', 'fkdr', 'bblr']:
                processed_mode[key] = get_safe_int(value)

        # Recalculate all ratios to ensure consistency
        processed_mode['wlr'] = calculate_ratio(processed_mode.get('wins'), processed_mode.get('losses'))
        processed_mode['kdr'] = calculate_ratio(processed_mode.get('kills'), processed_mode.get('deaths'))
        processed_mode['fkdr'] = calculate_ratio(processed_mode.get('final_kills'), processed_mode.get('final_deaths'))
        processed_mode['bblr'] = calculate_ratio(processed_mode.get('beds_broken'), processed_mode.get('beds_lost'))
        processed_mode['win_rate'] = calculate_win_rate(processed_mode.get('wins'), processed_mode.get('games_played'))
        processed_mode['finals_per_game'] = calculate_finals_per_game(processed_mode.get('final_kills'), processed_mode.get('games_played'))
        final_modes[mode_key] = processed_mode

    # Aggregate stats for 'Core Modes'
    core_keys = ['solos', 'doubles', 'threes', 'fours']
    core_agg = {
        'wins': 0, 'losses': 0, 'final_kills': 0, 'final_deaths': 0, 'beds_broken': 0,
        'beds_lost': 0, 'kills': 0, 'deaths': 0, 'games_played': 0
    }
    for mode_key in core_keys:
        if mode_key in final_modes:
            for stat in core_agg:
                core_agg[stat] += final_modes[mode_key].get(stat, 0)

    # Calculate ratios for core mode
    core_agg['wlr'] = calculate_ratio(core_agg['wins'], core_agg['losses'])
    core_agg['fkdr'] = calculate_ratio(core_agg['final_kills'], core_agg['final_deaths'])
    core_agg['bblr'] = calculate_ratio(core_agg['beds_broken'], core_agg['beds_lost'])
    core_agg['kdr'] = calculate_ratio(core_agg['kills'], core_agg['deaths'])
    core_agg['win_rate'] = calculate_win_rate(core_agg['wins'], core_agg['games_played'])
    core_agg['finals_per_game'] = calculate_finals_per_game(core_agg['final_kills'], core_agg['games_played'])
    final_modes['core'] = core_agg

    # Calculate 4v4 stats
    if 'overall' in final_modes and 'core' in final_modes:
        overall_stats = final_modes['overall']
        core_stats = final_modes['core']
        v4_stats = {}
        for stat in core_stats:
            if stat not in ['wlr', 'fkdr', 'bblr', 'kdr', 'win_rate', 'finals_per_game']:
                v4_stats[stat] = overall_stats.get(stat, 0) - core_stats.get(stat, 0)

        v4_stats['wlr'] = calculate_ratio(v4_stats.get('wins'), v4_stats.get('losses'))
        v4_stats['fkdr'] = calculate_ratio(v4_stats.get('final_kills'), v4_stats.get('final_deaths'))
        v4_stats['bblr'] = calculate_ratio(v4_stats.get('beds_broken'), v4_stats.get('beds_lost'))
        v4_stats['kdr'] = calculate_ratio(v4_stats.get('kills'), v4_stats.get('deaths'))
        v4_stats['win_rate'] = calculate_win_rate(v4_stats.get('wins'), v4_stats.get('games_played'))
        v4_stats['finals_per_game'] = calculate_finals_per_game(v4_stats.get('final_kills'), v4_stats.get('games_played'))
        final_modes['4v4'] = v4_stats

    level = scraped_data.get("star", 0)
    # Try to parse level as int if it's a string
    if isinstance(level, str):
        try:
            level = int(level)
        except (ValueError, TypeError):
            level = 0
    
    overall_fk = final_modes.get('overall', {}).get('final_kills', 0)
    if level and overall_fk:
        final_modes.get('overall', {})['finals_per_star'] = round(overall_fk / level, 2)
    
    transformed = {
        'username': username,
        'uuid': player_uuid,
        'rank_info': {'display_rank': 'LAVA'},
        'level': level,
        'most_played_gamemode': 'N/A',
        'overall': final_modes.get('overall'),
        'modes': final_modes,
        'fetched_by': scraped_data.get('fetched_by', 'scrapper'),  # Preserve original fetched_by
        'original_search': username,
        'last_updated': scraped_data.get('last_updated')
    }
    
    if transformed.get('overall'):
        transformed['overall']['bedwars_slumber_ticket_master'] = None # Not available from this source

    return transformed

# ... (The rest of your app.py file remains the same) ...

def format_stats_for_display(stats_data):
    """Formats numerical stats and calculates ratios for display."""
    if not stats_data:
        return stats_data

    # Handle overall and mode sections
    sections_to_format = []
    if 'overall' in stats_data and stats_data['overall'] is not None:
        sections_to_format.append(stats_data['overall'])
    if 'modes' in stats_data:
        for mode_key, mode_data in stats_data['modes'].items():
             if mode_data is not None and mode_key != 'overall':
                sections_to_format.append(mode_data)


    for section in sections_to_format:
        for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths', 'coins', 'games_played', 'bedwars_slumber_ticket_master']:
            section[f'{key}_formatted'] = format_number(section.get(key))

        for ratio_key in ['wlr', 'fkdr', 'bblr', 'kdr', 'win_rate', 'finals_per_star', 'finals_per_game']:
             value = section.get(ratio_key)
             # Try to convert to float, ignoring non-numeric values like '-'
             try:
                 float_value = float(value)
             except (ValueError, TypeError, AttributeError):
                 float_value = None

             if float_value is not None:
                  section[ratio_key] = "{:,.2f}".format(float_value)
             else:
                 # If value is a non-numeric string (like '-'), display it as is, otherwise 'N/A'
                 section[ratio_key] = value if isinstance(value, str) and not value.replace('.','',1).isdigit() else 'N/A'
                 
    return stats_data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/player', methods=['GET'])
def player_stats_page():
    username = request.args.get('username')
    if not username:
        return redirect(url_for('index'))

    result_data = hypixel_api.fetch_player_data(username)

    if result_data and result_data.get('error') == 'name_changed':
        print(f"App: Handling name change error for {username}.")
        return render_template('stats.html',
                               error_type='name_changed',
                               original_search=result_data.get('original_search'),
                               current_name=result_data.get('current_name'),
                               uuid=result_data.get('uuid'))

    if result_data and result_data.get('error'):
         print(f"App: Handling general error for {username}. Error: {result_data.get('error')}. Source: {result_data.get('fetched_by')}.")
         return render_template('stats.html',
                                error=result_data.get('error'),
                                username=result_data.get('original_search', username),
                                fetched_by=result_data.get('fetched_by')
                                )

    if result_data:
         print(f"App: Successfully fetched data for {username} via {result_data.get('fetched_by')}.")
         fetched_time = datetime.datetime.now()

         # Check both 'scrapper' and 'scraper' for compatibility
         if result_data.get('fetched_by') in ['scrapper', 'scraper']:
             print(f"Debug: Transforming scraper data. Keys: {result_data.keys()}")
             if 'modes' in result_data and 'overall' in result_data.get('modes', {}):
                 print(f"Debug: Overall stats keys: {result_data['modes']['overall'].keys()}")
             stats_for_display = transform_scrapper_data(result_data)
         else:
             stats_for_display = result_data

         formatted_stats = format_stats_for_display(stats_for_display)
         
         # Use the scraped timestamp if available, otherwise use the current time
         if stats_for_display.get('fetched_by') == 'scrapper' and 'last_updated' in stats_for_display:
             fetched_time = datetime.datetime.fromisoformat(stats_for_display['last_updated'])
         else:
             fetched_time = datetime.datetime.now()

         formatted_stats['fetched_at'] = time_ago(fetched_time)

         return render_template('stats.html', stats=formatted_stats, username=stats_for_display.get('username', username))
    else:
         print(f"App: Unknown error or no data returned for {username}.")
         return render_template('stats.html', error="Unknown error fetching data.", username=username)


@app.route('/compare', methods=['GET'])
def compare_stats_page():
    user1_orig = request.args.get('user1')
    user2_orig = request.args.get('user2')

    if not user1_orig or not user2_orig:
         return redirect(url_for('index'))
    
    stats_dict_results = hypixel_api.fetch_multiple_player_data([user1_orig, user2_orig])

    stats1_result = stats_dict_results.get(user1_orig.lower())
    stats2_result = stats_dict_results.get(user2_orig.lower())

    def prepare_stats_for_compare(stats_data):
        if not stats_data:
            return None

        if stats_data.get('error') == 'name_changed':
             return stats_data

        if stats_data.get('error'):
             return stats_data

        if stats_data.get('fetched_by') == 'scrapper':
             transformed_stats = transform_scrapper_data(stats_data)
             return transformed_stats
        else:
             return format_stats_for_display(stats_data) 


    stats1_processed = prepare_stats_for_compare(stats1_result)
    stats2_processed = prepare_stats_for_compare(stats2_result)

    return render_template('compare.html',
        user1=user1_orig,
        user2=user2_orig,
        stats1=stats1_processed,
        stats2=stats2_processed)


@app.route('/api/player/<username>', methods=['GET'])
def api_get_player_stats(username):
    result_data = hypixel_api.fetch_player_data(username)

    if result_data and result_data.get('fetched_by') == 'scrapper' and not result_data.get('error'):
        stats_for_api = transform_scrapper_data(result_data)
    else:
        stats_for_api = result_data 

    formatted_api_stats = format_stats_for_display(stats_for_api)


    if formatted_api_stats and 'error' in formatted_api_stats:
         status_code = 404 if formatted_api_stats.get('error') != 'name_changed' and formatted_api_stats.get('fetched_by') not in ['api_error', 'scrapper'] else \
                       400 if formatted_api_stats.get('error') == 'name_changed' else \
                       500

         return jsonify(formatted_api_stats), status_code
    elif formatted_api_stats:
        return jsonify(formatted_api_stats), 200
    else:
        return jsonify({"error": "Unknown server error fetching player data.", "fetched_by": "unknown"}), 500

@app.route('/api/compare', methods=['GET'])
def api_compare_players():
    usernames_str = request.args.get('users')
    if not usernames_str:
        return jsonify({"error": "No usernames provided"}), 400
    usernames = [name.strip() for name in usernames_str.split(',') if name.strip()]
    if len(usernames) < 2:
         return jsonify({"error": "At least two usernames required for comparison"}), 400

    stats_dict_results = hypixel_api.fetch_multiple_player_data(usernames)

    api_output_results = {}
    for username, result_data in stats_dict_results.items():
         if result_data and result_data.get('fetched_by') == 'scrapper' and not result_data.get('error'):
             transformed_stats = transform_scrapper_data(result_data)
         else:
             transformed_stats = result_data

         api_output_results[username] = format_stats_for_display(transformed_stats)


    has_critical_error = any(res and res.get('error') and res.get('error') != 'name_changed' for res in api_output_results.values())
    status_code = 500 if has_critical_error else 200
    return jsonify(api_output_results), status_code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)