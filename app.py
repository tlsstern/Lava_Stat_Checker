from flask import Flask, render_template, jsonify, request, redirect, url_for
# Ensure hypixel_api import is correct (assuming you added scrapper fallback there)
import hypixel_api
import json
import os
import math # Import math for ratio calculations
import traceback # Import traceback for better error logging

app = Flask(__name__)

# Create directories if they don't exist
if not os.path.exists('static'): os.makedirs('static')
if not os.path.exists('static/css'): os.makedirs('static/css')
if not os.path.exists('static/js'): os.makedirs('static/js')
if not os.path.exists('templates'): os.makedirs('templates')

def calculate_ratio(numerator, denominator):
    """Helper to calculate ratio, handling division by zero and None inputs."""
    if numerator is None or denominator is None:
        return 0.0 # Treat None as 0 for calculation purposes before ratio check
    try:
        num = float(numerator)
        den = float(denominator)
        if den == 0:
            return num if num != 0 else 0.0
        return round(num / den, 2)
    except (ValueError, TypeError):
        return 0.0 # Return 0.0 if inputs are not valid numbers

def calculate_win_rate(wins, games_played):
    """Helper to calculate win rate, handling division by zero and None inputs."""
    if wins is None or games_played is None:
        return 0.0
    try:
        win_f = float(wins)
        games_f = float(games_played)
        if games_f == 0:
            return 0.0
        return round((win_f / games_f) * 100, 2)
    except (ValueError, TypeError):
        return 0.0

def calculate_finals_per_game(final_kills, games_played):
     """Helper to calculate finals per game, handling division by zero and None inputs."""
     if final_kills is None or games_played is None:
         return 0.0
     try:
         fk_f = float(final_kills)
         games_f = float(games_played)
         if games_f == 0:
             return fk_f if fk_f != 0 else 0.0
         return round(fk_f / games_f, 2)
     except (ValueError, TypeError):
         return 0.0

def format_number(value):
    """Formats a number with apostrophe as thousand separator, returns N/A for None/invalid."""
    if value is None:
        return 'N/A'
    try:
        # Convert to int for formatting, handle floats by truncating
        return "{:,}".format(int(float(value))).replace(',', "'")
    except (ValueError, TypeError):
        return 'N/A'

def get_safe_int(value):
    """Converts a value to an integer, returning 0 if None or invalid."""
    if value is None:
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0

def get_safe_level(value):
    if value is None:
        return None

    s_value = str(value)
    cleaned_digits = []
    for char in s_value:
        if '0' <= char <= '9':
            cleaned_digits.append(char)

    cleaned_string = "".join(cleaned_digits)

    if not cleaned_string:
        return None

    try:
        return int(cleaned_string)
    except ValueError:
        return None

def transform_scrapper_data(scraped_data):
    """
    Transforms scrapper data to a structure similar to API data,
    including only specified stats and calculating Core and 4v4.
    """
    if not scraped_data or scraped_data.get('error'):
        # If scrapper itself returned an error, return it as is
        return scraped_data

    transformed = {
        'username': scraped_data.get('username'),
        'uuid': None, # Scrapper doesn't provide UUID directly
        'rank_info': {'display_rank': 'N/A'}, # Set rank to N/A for scraped data
        'level': get_safe_level(scraped_data.get('level')),
        'most_played_gamemode': 'N/A', # Will calculate below
        'overall': {}, # Initialize overall dict
        'modes': {
            'core': {}, # Calculated Core
            'solos': {},
            'doubles': {},
            'threes': {},
            'fours': {},
            '4v4': {} # Calculated 4v4
        },
        'fetched_by': 'scrapper',
        # Removed api_error_details from transformed data passed to template
        'original_search': scraped_data.get('original_search')
    }

    main_stats = scraped_data.get('main_stats', {})

    # Mapping of scrapper individual mode names to API-like keys
    individual_mode_map = {
        'Solo': 'solos',
        'Doubles': 'doubles',
        '3v3v3v3': 'threes',
        '4v4v4v4': 'fours',
    }

    # Extract raw stats for individual modes and Overall from main_stats
    stat_keys = ['Games Played', 'Wins', 'Losses', 'Kills', 'Deaths', 'Final Kills', 'Final Deaths', 'Beds Broken', 'Beds Lost']

    raw_individual_modes_stats = {api_mode_key: {} for api_mode_key in individual_mode_map.values()}
    raw_overall_stats = {}

    for stat_name in stat_keys:
        mode_values = main_stats.get(stat_name, {})
        api_key = stat_name.lower().replace(' ', '_')

        for scraped_mode, value in mode_values.items():
            if scraped_mode == 'Overall':
                raw_overall_stats[api_key] = get_safe_int(value)
            elif scraped_mode in individual_mode_map:
                mapped_mode_key = individual_mode_map[scraped_mode]
                raw_individual_modes_stats[mapped_mode_key][api_key] = get_safe_int(value)

    # Add Coins (from overall scrapper data)
    raw_overall_stats['coins'] = get_safe_int(scraped_data.get('coins'))

    # --- Calculate Core Stats (Sum of Individual Modes) ---
    calculated_core_stats = {}
    for stat_key in stat_keys:
        api_key = stat_key.lower().replace(' ', '_')
        total_for_core = 0
        for mode_key in individual_mode_map.values():
            total_for_core += raw_individual_modes_stats.get(mode_key, {}).get(api_key, 0)
        calculated_core_stats[api_key] = total_for_core

    # --- Calculate 4v4 Stats (Scraped Overall - Calculated Core) ---
    calculated_fouvfour_stats = {}
    for key in ['wins', 'losses', 'games_played', 'kills', 'deaths', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost']:
        overall_val = raw_overall_stats.get(key, 0)
        core_val = calculated_core_stats.get(key, 0) # Use the calculated core value
        # Ensure subtraction result is not negative
        calculated_fouvfour_stats[key] = max(0, overall_val - core_val)

    # --- Print calculated Core and 4v4 for debugging ---
    print(f"--- Calculated Core Stats for {transformed.get('username')} ---")
    for key, value in calculated_core_stats.items():
        print(f"  {key}: {value}")
    print(f"--- Calculated 4v4 Stats for {transformed.get('username')} ---")
    for key, value in calculated_fouvfour_stats.items():
        print(f"  {key}: {value}")
    print("-------------------------------------------------")


    # --- Populate Transformed Structure and Calculate Ratios ---

    # Overall
    transformed['overall'] = raw_overall_stats # Assign the raw overall data
    transformed['overall']['wlr'] = calculate_ratio(transformed['overall'].get('wins'), transformed['overall'].get('losses'))
    transformed['overall']['fkdr'] = calculate_ratio(transformed['overall'].get('final_kills'), transformed['overall'].get('final_deaths'))
    transformed['overall']['bblr'] = calculate_ratio(transformed['overall'].get('beds_broken'), transformed['overall'].get('beds_lost'))
    transformed['overall']['kdr'] = calculate_ratio(transformed['overall'].get('kills'), transformed['overall'].get('deaths'))
    transformed['overall']['win_rate'] = calculate_win_rate(transformed['overall'].get('wins'), transformed['overall'].get('games_played'))
    transformed['overall']['finals_per_star'] = 0.0 # Not reliably calculated from scraped data
    transformed['overall']['finals_per_game'] = calculate_finals_per_game(transformed['overall'].get('final_kills'), transformed['overall'].get('games_played'))
    transformed['overall']['bedwars_slumber_ticket_master'] = None # API only


    # Core (Calculated)
    transformed['modes']['core'] = calculated_core_stats
    transformed['modes']['core']['wlr'] = calculate_ratio(calculated_core_stats.get('wins'), calculated_core_stats.get('losses'))
    transformed['modes']['core']['fkdr'] = calculate_ratio(calculated_core_stats.get('final_kills'), calculated_core_stats.get('final_deaths'))
    transformed['modes']['core']['bblr'] = calculate_ratio(calculated_core_stats.get('beds_broken'), calculated_core_stats.get('beds_lost'))
    transformed['modes']['core']['kdr'] = calculate_ratio(calculated_core_stats.get('kills'), calculated_core_stats.get('deaths'))
    transformed['modes']['core']['win_rate'] = calculate_win_rate(calculated_core_stats.get('wins'), calculated_core_stats.get('games_played'))
    transformed['modes']['core']['finals_per_game'] = calculate_finals_per_game(calculated_core_stats.get('final_kills'), calculated_core_stats.get('games_played'))


    # Individual Modes (Solos, Doubles, Threes, Fours)
    for mode_key in individual_mode_map.values():
         mode_raw = raw_individual_modes_stats.get(mode_key, {})
         transformed['modes'][mode_key] = mode_raw # Assign the raw individual mode data
         mode_raw['wlr'] = calculate_ratio(mode_raw.get('wins'), mode_raw.get('losses'))
         mode_raw['fkdr'] = calculate_ratio(mode_raw.get('final_kills'), mode_raw.get('final_deaths'))
         mode_raw['bblr'] = calculate_ratio(mode_raw.get('beds_broken'), mode_raw.get('beds_lost'))
         mode_raw['kdr'] = calculate_ratio(mode_raw.get('kills'), mode_raw.get('deaths'))
         mode_raw['win_rate'] = calculate_win_rate(mode_raw.get('wins'), mode_raw.get('games_played'))
         mode_raw['finals_per_game'] = calculate_finals_per_game(mode_raw.get('final_kills'), mode_raw.get('games_played'))


    # 4v4 (Calculated)
    transformed['modes']['4v4'] = calculated_fouvfour_stats
    transformed['modes']['4v4']['wlr'] = calculate_ratio(calculated_fouvfour_stats.get('wins'), calculated_fouvfour_stats.get('losses'))
    transformed['modes']['4v4']['fkdr'] = calculate_ratio(calculated_fouvfour_stats.get('final_kills'), calculated_fouvfour_stats.get('final_deaths'))
    transformed['modes']['4v4']['bblr'] = calculate_ratio(calculated_fouvfour_stats.get('beds_broken'), calculated_fouvfour_stats.get('beds_lost'))
    transformed['modes']['4v4']['kdr'] = calculate_ratio(calculated_fouvfour_stats.get('kills'), calculated_fouvfour_stats.get('deaths'))
    transformed['modes']['4v4']['win_rate'] = calculate_win_rate(calculated_fouvfour_stats.get('wins'), calculated_fouvfour_stats.get('games_played'))
    transformed['modes']['4v4']['finals_per_game'] = calculate_finals_per_game(calculated_fouvfour_stats.get('final_kills'), calculated_fouvfour_stats.get('games_played'))


    # Determine Most Played Gamemode from scraped Games Played for individual modes
    most_played_gamemode = "N/A"
    max_games = -1
    # Mapping of scraped mode names for display for the modes we are considering for "Most Played"
    scraped_mode_titles_for_most_played = {'Solo': 'Solos', 'Doubles': 'Doubles', '3v3v3v3': 'Threes', '4v4v4v4': 'Fours'}
    scraped_games_played = main_stats.get('Games Played', {})

    for scraped_mode, games_value in scraped_games_played.items():
        if scraped_mode in scraped_mode_titles_for_most_played: # Only consider the specified modes
            games = get_safe_int(games_value)
            if games > max_games:
                max_games = games
                most_played_gamemode = scraped_mode_titles_for_most_played[scraped_mode]

    if max_games > 0:
        transformed['most_played_gamemode'] = most_played_gamemode


    return transformed


# This function now handles formatting for both API and transformed Scrapper data
def format_stats_for_display(stats_data):
    """Formats numerical stats and calculates ratios for display."""
    if not stats_data:
        return stats_data

    # Handle overall and mode sections
    sections_to_format = []
    if 'overall' in stats_data and stats_data['overall'] is not None:
        sections_to_format.append(stats_data['overall'])
    if 'modes' in stats_data:
        # Iterate through all modes, including the calculated 4v4
        for mode_key in ['core', 'solos', 'doubles', 'threes', 'fours', '4v4']:
             mode_data = stats_data['modes'].get(mode_key)
             if mode_data is not None:
                sections_to_format.append(mode_data)


    for section in sections_to_format:
        # Format raw numbers
        for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths', 'coins', 'games_played']:
            section[f'{key}_formatted'] = format_number(section.get(key))

        # Format specific API-only stats that might not be in scrapper data
        slumber_key = 'bedwars_slumber_ticket_master'
        section[f'{slumber_key}_formatted'] = format_number(section.get(slumber_key))

        # Format ratios
        for ratio_key in ['wlr', 'fkdr', 'bblr', 'kdr', 'win_rate', 'finals_per_star', 'finals_per_game']:
             value = section.get(ratio_key)
             # Ensure value is treated as a number before formatting
             try:
                 float_value = float(value) if value is not None else None
             except (ValueError, TypeError):
                 float_value = None

             if float_value is not None:
                  section[ratio_key] = "{:,.2f}".format(float_value)
             else:
                 section[ratio_key] = 'N/A' # Keep N/A if not a number


    return stats_data


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/player', methods=['GET'])
def player_stats_page():
    username = request.args.get('username')
    if not username:
        return redirect(url_for('index'))

    # fetch_player_data now handles API + Scrapper fallback
    result_data = hypixel_api.fetch_player_data(username)

    # Check if the result is a name change error from API
    if result_data and result_data.get('error') == 'name_changed':
        print(f"App: Handling name change error for {username}.")
        return render_template('stats.html',
                               error_type='name_changed',
                               original_search=result_data.get('original_search'),
                               current_name=result_data.get('current_name'),
                               uuid=result_data.get('uuid'))

    # Check if the result is an error from either API or Scrapper
    # (excluding the specific 'name_changed' type handled above)
    if result_data and result_data.get('error'):
         print(f"App: Handling general error for {username}. Error: {result_data.get('error')}. Source: {result_data.get('fetched_by')}.")
         # Pass the original search and fetched_by for context in the error message
         return render_template('stats.html',
                                error=result_data.get('error'),
                                username=result_data.get('original_search', username),
                                fetched_by=result_data.get('fetched_by')
                                )

    # If no errors, process and render data
    if result_data:
         print(f"App: Successfully fetched data for {username} via {result_data.get('fetched_by')}.")

         # Transform scrapper data to API-like structure if needed
         if result_data.get('fetched_by') == 'scrapper':
             stats_for_display = transform_scrapper_data(result_data)
         else: # Data is already in API structure
             stats_for_display = result_data

         # Format the data for display regardless of original source
         formatted_stats = format_stats_for_display(stats_for_display)

         # Pass the formatted data to the template
         return render_template('stats.html', stats=formatted_stats, username=stats_for_display.get('username', username))
    else:
         # Should ideally not happen with current fetch_player_data logic,
         # but as a final fallback
         print(f"App: Unknown error or no data returned for {username}.")
         return render_template('stats.html', error="Unknown error fetching data.", username=username)


@app.route('/compare', methods=['GET'])
def compare_stats_page():
    user1_orig = request.args.get('user1')
    user2_orig = request.args.get('user2')

    if not user1_orig or not user2_orig:
         return redirect(url_for('index'))

    # fetch_multiple_player_data handles fallback internally
    stats_dict_results = hypixel_api.fetch_multiple_player_data([user1_orig, user2_orig])

    stats1_result = stats_dict_results.get(user1_orig.lower())
    stats2_result = stats_dict_results.get(user2_orig.lower())

    # Function to prepare stats result (either API or Scrapper) for comparison display
    def prepare_stats_for_compare(stats_data):
        if not stats_data:
            return None # Return None if no data/error

        # Handle specific name change error for compare display
        if stats_data.get('error') == 'name_changed':
             return stats_data # Pass the name_changed info directly

        if stats_data.get('error'):
             return stats_data # Pass the error info directly

        # If data is from scrapper, transform it first
        if stats_data.get('fetched_by') == 'scrapper':
             # Transform scrapper data to API-like structure for comparison
             # NOTE: Comparison logic in compare.html still needs to be fully compatible
             # with this transformed structure and handle potential N/A values.
             transformed_stats = transform_scrapper_data(stats_data)
             return transformed_stats
        else:
             # Data is already in API structure, format for comparison display
             # This formatting is less about structure and more about number/ratio presentation
             return format_stats_for_display(stats_data) # Use the same formatting logic as single player


    # Prepare stats for both players using the new function
    stats1_processed = prepare_stats_for_compare(stats1_result)
    stats2_processed = prepare_stats_for_compare(stats2_result)

    # NOTE: The compare.html template relies on a consistent structure for comparison.
    # While we are transforming scrapper data to an API-like structure,
    # the comparison logic in compare.html (e.g., macro compare_stat_row)
    # needs to be robust enough to handle potential differences or missing data
    # between API data and transformed scrapper data.
    # This might still require further adjustments in compare.html depending
    # on how the comparison macro works and what data it expects.
    return render_template('compare.html',
        user1=user1_orig,
        user2=user2_orig,
        stats1=stats1_processed, # Pass the processed/transformed data
        stats2=stats2_processed) # Pass the processed/transformed data


# API endpoints - These will return data from either API or scrapper based on the fallback
@app.route('/api/player/<username>', methods=['GET'])
def api_get_player_stats(username):
    result_data = hypixel_api.fetch_player_data(username)

    # Transform scrapper data to API-like structure for API consumers as well
    if result_data and result_data.get('fetched_by') == 'scrapper' and not result_data.get('error'):
        stats_for_api = transform_scrapper_data(result_data)
    else:
        stats_for_api = result_data # No transformation needed for API data

    # Format the transformed/API data for consistent API output
    formatted_api_stats = format_stats_for_display(stats_for_api)


    # Adjust status code based on fetched_by and error type
    if formatted_api_stats and 'error' in formatted_api_stats:
         status_code = 404 if formatted_api_stats.get('error') != 'name_changed' and formatted_api_stats.get('fetched_by') not in ['api_error', 'scrapper'] else \
                       400 if formatted_api_stats.get('error') == 'name_changed' else \
                       500 # Treat API/Scrapper errors as internal server errors for the API endpoint

         return jsonify(formatted_api_stats), status_code
    elif formatted_api_stats:
        # API endpoint will return the transformed/formatted data, including 'fetched_by'
        return jsonify(formatted_api_stats), 200
    else:
        # Should be caught by fetch_player_data's error handling, but safety net
        return jsonify({"error": "Unknown server error fetching player data.", "fetched_by": "unknown"}), 500

@app.route('/api/compare', methods=['GET'])
def api_compare_players():
    usernames_str = request.args.get('users')
    if not usernames_str:
        return jsonify({"error": "No usernames provided"}), 400
    usernames = [name.strip() for name in usernames_str.split(',') if name.strip()]
    if len(usernames) < 2:
         return jsonify({"error": "At least two usernames required for comparison"}), 400

    # fetch_multiple_player_data handles fallback internally
    stats_dict_results = hypixel_api.fetch_multiple_player_data(usernames)

    # Prepare results for API output, transforming scrapper data
    api_output_results = {}
    for username, result_data in stats_dict_results.items():
         if result_data and result_data.get('fetched_by') == 'scrapper' and not result_data.get('error'):
             transformed_stats = transform_scrapper_data(result_data)
         else:
             transformed_stats = result_data # No transformation needed for API data

         api_output_results[username] = format_stats_for_display(transformed_stats)


    # Check if any result has a non-name_changed error for status code
    has_critical_error = any(res and res.get('error') and res.get('error') != 'name_changed' for res in api_output_results.values())
    status_code = 500 if has_critical_error else 200
    # API endpoint will return the transformed/formatted results.
    return jsonify(api_output_results), status_code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
