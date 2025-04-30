from flask import Flask, render_template, jsonify, request, redirect, url_for
import scrapper # Use the scraper
import json
import os
import re # Import regex for cleaning numbers

app = Flask(__name__)

# --- Helper Functions (Unchanged) ---

def clean_and_convert(value_str, target_type=int):
    """Cleans string numbers (removes ',', ''', '✫') and converts to int or float."""
    if value_str is None:
        return 0 if target_type == int else 0.0
    try:
        cleaned_str = re.sub(r"[,'✫]", "", str(value_str).strip())
        if not cleaned_str or cleaned_str.lower() == 'n/a':
            return 0 if target_type == int else 0.0
        return target_type(float(cleaned_str))
    except (ValueError, TypeError):
        return 0 if target_type == int else 0.0

def calculate_ratio(numerator, denominator):
    """Safely calculates a ratio, handling division by zero."""
    num = clean_and_convert(numerator, float)
    den = clean_and_convert(denominator, float)
    if den == 0:
        return num if num != 0 else 0.0
    return round(num / den, 2)

def format_stat_section(section_data):
    """Adds formatted string versions of stats."""
    if not section_data:
        return section_data
    # Format main numerical stats
    for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths', 'coins', 'games_played']:
        value = section_data.get(key)
        if value is not None and isinstance(value, (int, float)):
            section_data[f'{key}_formatted'] = "{:,}".format(int(value)).replace(',', "'")
        elif key not in section_data or value is None: # Handle missing or None
             section_data[f'{key}_formatted'] = 'N/A'
        # else: keep existing non-numeric value

    # Specific handling for potentially missing/non-calculable stats
    slumber_key = 'bedwars_slumber_ticket_master'
    if slumber_key not in section_data or section_data[slumber_key] is None:
         section_data[f'{slumber_key}_formatted'] = 'N/A'
    elif isinstance(section_data[slumber_key], (int, float)):
         section_data[f'{slumber_key}_formatted'] = "{:,}".format(int(section_data[slumber_key])).replace(',', "'")

    # Ensure ratios and calculated stats are formatted correctly if they exist as numbers
    for ratio_key in ['wlr', 'fkdr', 'bblr', 'kdr', 'win_rate', 'finals_per_game', 'finals_per_star']:
        ratio_value = section_data.get(ratio_key)
        if isinstance(ratio_value, (int, float)):
             formatted_val = f"{ratio_value:.2f}"
             section_data[f'{ratio_key}'] = formatted_val
             section_data[f'{ratio_key}_formatted'] = formatted_val
        elif ratio_key not in section_data or ratio_value is None:
             section_data[f'{ratio_key}'] = 'N/A'
             section_data[f'{ratio_key}_formatted'] = 'N/A'
        # else: keep existing string like 'N/A'

    return section_data

# --- Transformation Function ---

def transform_scraped_data(scraped_data, original_search_term):
    """Transforms data from scrape_bwstats to mimic hypixel_api output."""
    if not scraped_data or scraped_data.get('error'):
        error_message = scraped_data.get('error', 'Failed to scrape data')
        return {"error": error_message, "original_search": original_search_term}

    transformed = {
        "username": scraped_data.get('username', original_search_term),
        "uuid": None,
        "rank_info": {"display_rank": "N/A"},
        "level": clean_and_convert(scraped_data.get('level'), int),
        "most_played_gamemode": "N/A",
        "original_search": original_search_term,
        "fetched_by": "scraper",
        "overall": {},
        "modes": { # Initialize modes structure
            "solos": {}, "doubles": {}, "threes": {}, "fours": {}, "4v4": {}, "core": {}
        }
    }

    main_stats = scraped_data.get('main_stats', {})
    if not isinstance(main_stats, dict):
         print(f"Warning: main_stats is not a dictionary for {original_search_term}: {main_stats}")
         return {"error": "Invalid main_stats structure from scraper", "original_search": original_search_term}


    # --- Populate Overall Stats ---
    overall = transformed['overall']
    player_level = transformed['level']

    overall['coins'] = clean_and_convert(scraped_data.get('coins'), int)
    overall['wins'] = clean_and_convert(main_stats.get('Wins', {}).get('Overall'), int)
    overall['losses'] = clean_and_convert(main_stats.get('Losses', {}).get('Overall'), int)
    overall['final_kills'] = clean_and_convert(main_stats.get('Final Kills', {}).get('Overall'), int)
    overall['final_deaths'] = clean_and_convert(main_stats.get('Final Deaths', {}).get('Overall'), int)
    overall['beds_broken'] = clean_and_convert(main_stats.get('Beds Broken', {}).get('Overall'), int)
    overall['beds_lost'] = clean_and_convert(main_stats.get('Beds Lost', {}).get('Overall'), int)
    overall['kills'] = clean_and_convert(main_stats.get('Kills', {}).get('Overall'), int)
    overall['deaths'] = clean_and_convert(main_stats.get('Deaths', {}).get('Overall'), int)

    overall['games_played'] = overall['wins'] + overall['losses']
    overall['wlr'] = calculate_ratio(overall['wins'], overall['losses'])
    overall['fkdr'] = calculate_ratio(overall['final_kills'], overall['final_deaths'])
    overall['bblr'] = calculate_ratio(overall['beds_broken'], overall['beds_lost'])
    overall['kdr'] = calculate_ratio(overall['kills'], overall['deaths'])
    overall['win_rate'] = round((overall['wins'] / overall['games_played']) * 100, 2) if overall['games_played'] > 0 else 0.0
    overall['finals_per_game'] = round(overall['final_kills'] / overall['games_played'], 2) if overall['games_played'] > 0 else float(overall['final_kills'])
    overall['finals_per_star'] = round(overall['final_kills'] / player_level, 2) if player_level > 0 else float(overall['final_kills'])
    overall['bedwars_slumber_ticket_master'] = None

    # --- Populate Mode Stats from main_stats ---
    modes_data = transformed['modes']

    # Mapping from scraper's mode names (keys in inner dicts of main_stats)
    # REMOVED '4v4' as it's calculated later
    scraper_mode_to_internal = {
        'Solo': 'solos',
        'Doubles': 'doubles',
        '3v3v3v3': 'threes',
        '4v4v4v4': 'fours',
    }
    # Mapping from scraper's stat names (keys in outer dict of main_stats)
    scraper_stat_to_internal = {
        'Wins': 'wins', 'Losses': 'losses', 'Final Kills': 'final_kills',
        'Final Deaths': 'final_deaths', 'Beds Broken': 'beds_broken',
        'Beds Lost': 'beds_lost', 'Kills': 'kills', 'Deaths': 'deaths',
        'Games Played': 'games_played'
    }
    # Base stats needed for calculations (internal keys)
    base_stat_keys = ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths']


    # Iterate through the stats provided by the scraper in main_stats
    for scraped_stat_name, mode_values_dict in main_stats.items():
        internal_stat_key = scraper_stat_to_internal.get(scraped_stat_name)
        if not internal_stat_key: continue

        if not isinstance(mode_values_dict, dict): continue

        # Iterate through the modes provided for this stat
        for scraped_mode_name, value_str in mode_values_dict.items():
            internal_mode_key = scraper_mode_to_internal.get(scraped_mode_name)
            if internal_mode_key: # Only process modes in the map (solos, doubles, threes, fours)
                if internal_mode_key in modes_data:
                     modes_data[internal_mode_key][internal_stat_key] = clean_and_convert(value_str, int)


    # --- Calculate Derived Stats for Scraped Modes & Find Most Played (excluding 4v4 for now) ---
    max_games = -1
    most_played_key = None
    mode_titles = {'solos': 'Solos', 'doubles': 'Doubles', 'threes': 'Threes', 'fours': 'Fours', '4v4': '4v4'}

    # Iterate through the modes we scraped directly
    for mode_key in scraper_mode_to_internal.values():
        mode_dict = modes_data[mode_key]

        # Ensure all base stats are present
        for base_key in base_stat_keys:
             if base_key not in mode_dict:
                 mode_dict[base_key] = 0
        # Ensure games_played exists
        if 'games_played' not in mode_dict:
            mode_dict['games_played'] = mode_dict.get('wins', 0) + mode_dict.get('losses', 0)

        # Calculate derived stats
        if mode_dict.get('games_played', 0) > 0:
            mode_dict['wlr'] = calculate_ratio(mode_dict.get('wins'), mode_dict.get('losses'))
            mode_dict['fkdr'] = calculate_ratio(mode_dict.get('final_kills'), mode_dict.get('final_deaths'))
            mode_dict['bblr'] = calculate_ratio(mode_dict.get('beds_broken'), mode_dict.get('beds_lost'))
            mode_dict['kdr'] = calculate_ratio(mode_dict.get('kills'), mode_dict.get('deaths'))
            mode_dict['win_rate'] = round((mode_dict.get('wins', 0) / mode_dict['games_played']) * 100, 2)
            mode_dict['finals_per_game'] = round(mode_dict.get('final_kills', 0) / mode_dict['games_played'], 2)
        else: # Defaults for 0 games
            mode_dict['wlr'] = 0.0
            mode_dict['fkdr'] = float(mode_dict.get('final_kills', 0))
            mode_dict['bblr'] = float(mode_dict.get('beds_broken', 0))
            mode_dict['kdr'] = float(mode_dict.get('kills', 0))
            mode_dict['win_rate'] = 0.0
            mode_dict['finals_per_game'] = float(mode_dict.get('final_kills', 0))

        # Track most played among these modes
        current_games = mode_dict.get('games_played', 0)
        if current_games > max_games:
            max_games = current_games
            most_played_key = mode_key


    # --- Calculate Aggregated Core Stats ---
    core_modes = ["solos", "doubles", "threes", "fours"]
    core_stats_agg = {k: 0 for k in base_stat_keys} # Aggregate only base stats

    for mode_key in core_modes:
        if mode_data := modes_data.get(mode_key):
             for stat_key in base_stat_keys:
                core_stats_agg[stat_key] += mode_data.get(stat_key, 0)

    core_dict = modes_data['core']
    core_dict.update(core_stats_agg) # Add the aggregated sums

    # Calculate derived core stats
    core_dict['games_played'] = core_dict.get('wins', 0) + core_dict.get('losses', 0)
    if core_dict.get('games_played', 0) > 0:
        core_dict['wlr'] = calculate_ratio(core_dict.get('wins'), core_dict.get('losses'))
        core_dict['fkdr'] = calculate_ratio(core_dict.get('final_kills'), core_dict.get('final_deaths'))
        core_dict['bblr'] = calculate_ratio(core_dict.get('beds_broken'), core_dict.get('beds_lost'))
        core_dict['kdr'] = calculate_ratio(core_dict.get('kills'), core_dict.get('deaths'))
        core_dict['win_rate'] = round((core_dict.get('wins', 0) / core_dict['games_played']) * 100, 2)
        core_dict['finals_per_game'] = round(core_dict.get('final_kills', 0) / core_dict['games_played'], 2)
    else: # Defaults for core if 0 games
         core_dict.update({k: 0.0 for k in ['wlr', 'win_rate']})
         core_dict['fkdr'] = float(core_dict.get('final_kills', 0))
         core_dict['bblr'] = float(core_dict.get('beds_broken', 0))
         core_dict['kdr'] = float(core_dict.get('kills', 0))
         core_dict['finals_per_game'] = float(core_dict.get('final_kills', 0))


    # --- Calculate 4v4 Stats by Subtraction ---
    four_v_four_dict = modes_data['4v4']
    for stat_key in base_stat_keys:
        # Subtract core from overall. Ensure non-negative results.
        four_v_four_dict[stat_key] = max(0, overall.get(stat_key, 0) - core_dict.get(stat_key, 0))

    # Calculate derived 4v4 stats
    four_v_four_dict['games_played'] = four_v_four_dict.get('wins', 0) + four_v_four_dict.get('losses', 0)
    if four_v_four_dict.get('games_played', 0) > 0:
        four_v_four_dict['wlr'] = calculate_ratio(four_v_four_dict.get('wins'), four_v_four_dict.get('losses'))
        four_v_four_dict['fkdr'] = calculate_ratio(four_v_four_dict.get('final_kills'), four_v_four_dict.get('final_deaths'))
        four_v_four_dict['bblr'] = calculate_ratio(four_v_four_dict.get('beds_broken'), four_v_four_dict.get('beds_lost'))
        four_v_four_dict['kdr'] = calculate_ratio(four_v_four_dict.get('kills'), four_v_four_dict.get('deaths'))
        four_v_four_dict['win_rate'] = round((four_v_four_dict.get('wins', 0) / four_v_four_dict['games_played']) * 100, 2)
        four_v_four_dict['finals_per_game'] = round(four_v_four_dict.get('final_kills', 0) / four_v_four_dict['games_played'], 2)
    else: # Defaults for 4v4 if 0 games
        four_v_four_dict.update({k: 0.0 for k in ['wlr', 'win_rate']})
        four_v_four_dict['fkdr'] = float(four_v_four_dict.get('final_kills', 0))
        four_v_four_dict['bblr'] = float(four_v_four_dict.get('beds_broken', 0))
        four_v_four_dict['kdr'] = float(four_v_four_dict.get('kills', 0))
        four_v_four_dict['finals_per_game'] = float(four_v_four_dict.get('final_kills', 0))

    # --- Update Most Played Check ---
    # Check if calculated 4v4 games are the most played
    if four_v_four_dict.get('games_played', 0) > max_games:
         most_played_key = '4v4'

    if most_played_key:
         transformed['most_played_gamemode'] = mode_titles.get(most_played_key, "N/A")


    # --- Apply Formatting ---
    transformed['overall'] = format_stat_section(transformed['overall'])
    for mode_key in modes_data: # Format all modes including 'core' and calculated '4v4'
        transformed['modes'][mode_key] = format_stat_section(modes_data[mode_key])


    return transformed

# --- Flask Routes (Unchanged) ---

@app.route('/')
def index():
    if not os.path.exists('templates/index.html'):
         return "Error: index.html template not found.", 404
    return render_template('index.html')

@app.route('/player', methods=['GET'])
def player_stats_page():
    username = request.args.get('username')
    if not username:
        return redirect(url_for('index'))

    scraped_result = scrapper.scrape_bwstats(username)
    transformed_data = transform_scraped_data(scraped_result, username)

    if transformed_data and 'error' in transformed_data:
         return render_template('stats.html',
                                error=transformed_data.get('error'),
                                username=username)
    elif transformed_data:
         return render_template('stats.html', stats=transformed_data, username=transformed_data.get('username', username))
    else:
         return render_template('stats.html', error="Unknown error processing scraped data.", username=username)


@app.route('/compare', methods=['GET'])
def compare_stats_page():
    user1_orig = request.args.get('user1')
    user2_orig = request.args.get('user2')

    if not user1_orig or not user2_orig:
         return redirect(url_for('index'))

    scraped1 = scrapper.scrape_bwstats(user1_orig)
    stats1_transformed = transform_scraped_data(scraped1, user1_orig)

    scraped2 = scrapper.scrape_bwstats(user2_orig)
    stats2_transformed = transform_scraped_data(scraped2, user2_orig)

    return render_template('compare.html',
        user1=user1_orig,
        user2=user2_orig,
        stats1=stats1_transformed,
        stats2=stats2_transformed)


@app.route('/api/player/<username>', methods=['GET'])
def api_get_player_stats(username):
    scraped_result = scrapper.scrape_bwstats(username)
    transformed_data = transform_scraped_data(scraped_result, username)

    if transformed_data and 'error' in transformed_data:
         status_code = 404
         return jsonify(transformed_data), status_code
    elif transformed_data:
        return jsonify(transformed_data), 200
    else:
        return jsonify({"error": "Unknown server error processing scraped data"}), 500

@app.route('/api/compare', methods=['GET'])
def api_compare_players():
    usernames_str = request.args.get('users')
    if not usernames_str:
        return jsonify({"error": "No usernames provided"}), 400
    usernames = [name.strip() for name in usernames_str.split(',') if name.strip()]
    if len(usernames) < 2:
         return jsonify({"error": "At least two usernames required for comparison"}), 400

    results_transformed = {}
    for name in usernames:
        scraped_data = scrapper.scrape_bwstats(name)
        results_transformed[name] = transform_scraped_data(scraped_data, name)

    has_error = any(res and res.get('error') for res in results_transformed.values())
    status_code = 400 if has_error else 200

    return jsonify(results_transformed), status_code

if __name__ == '__main__':
    if not os.path.exists('static'): os.makedirs('static')
    if not os.path.exists('templates'): os.makedirs('templates')
    app.run(host='0.0.0.0', port=5000, debug=True)
