from flask import Flask, render_template, jsonify, request, redirect, url_for
import hypixel_api
import os

app = Flask(__name__)

if not os.path.exists('static'): os.makedirs('static')
if not os.path.exists('static/css'): os.makedirs('static/css')
if not os.path.exists('static/js'): os.makedirs('static/js')
if not os.path.exists('templates'): os.makedirs('templates')

def calculate_ratio(numerator, denominator):
    """Helper to calculate ratio, handling division by zero and None inputs."""
    if numerator is None or denominator is None:
        return 0.0
    try:
        num = float(numerator)
        den = float(denominator)
        if den == 0:
            return num if num != 0 else 0.0
        return round(num / den, 2)
    except (ValueError, TypeError):
        return 0.0

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
        return scraped_data

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
                    print(f"Mojang UUID found for {username}: {player_uuid}")
        except Exception as e:
            print(f"Error getting UUID from Mojang for {username}: {e}")

    transformed = {
        'username': username,
        'uuid': player_uuid,
        'rank_info': {'display_rank': 'LAVA'},
        'level': get_safe_level(scraped_data.get('level')),
        'most_played_gamemode': 'N/A',
        'overall': {},
        'modes': {
            'core': {},
            'solos': {},
            'doubles': {},
            'threes': {},
            'fours': {},
            '4v4': {}
        },
        'fetched_by': 'scrapper',
        'original_search': scraped_data.get('original_search')
    }

    main_stats = scraped_data.get('main_stats', {})

    individual_mode_map = {
        'Solo': 'solos',
        'Doubles': 'doubles',
        '3v3v3v3': 'threes',
        '4v4v4v4': 'fours',
    }

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

    raw_overall_stats['coins'] = get_safe_int(scraped_data.get('coins'))

    calculated_core_stats = {}
    for stat_key in stat_keys:
        api_key = stat_key.lower().replace(' ', '_')
        total_for_core = 0
        for mode_key in individual_mode_map.values():
            total_for_core += raw_individual_modes_stats.get(mode_key, {}).get(api_key, 0)
        calculated_core_stats[api_key] = total_for_core

    calculated_fouvfour_stats = {}
    for key in ['wins', 'losses', 'games_played', 'kills', 'deaths', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost']:
        overall_val = raw_overall_stats.get(key, 0)
        core_val = calculated_core_stats.get(key, 0)
        calculated_fouvfour_stats[key] = max(0, overall_val - core_val)

    print(f"--- Calculated Core Stats for {transformed.get('username')} ---")
    for key, value in calculated_core_stats.items():
        print(f"  {key}: {value}")
    print(f"--- Calculated 4v4 Stats for {transformed.get('username')} ---")
    for key, value in calculated_fouvfour_stats.items():
        print(f"  {key}: {value}")
    print("-------------------------------------------------")



    transformed['overall'] = raw_overall_stats
    transformed['overall']['wlr'] = calculate_ratio(transformed['overall'].get('wins'), transformed['overall'].get('losses'))
    transformed['overall']['fkdr'] = calculate_ratio(transformed['overall'].get('final_kills'), transformed['overall'].get('final_deaths'))
    transformed['overall']['bblr'] = calculate_ratio(transformed['overall'].get('beds_broken'), transformed['overall'].get('beds_lost'))
    transformed['overall']['kdr'] = calculate_ratio(transformed['overall'].get('kills'), transformed['overall'].get('deaths'))
    transformed['overall']['win_rate'] = calculate_win_rate(transformed['overall'].get('wins'), transformed['overall'].get('games_played'))
    
    if transformed['level'] and transformed['level'] > 0:
        transformed['overall']['finals_per_star'] = round(transformed['overall'].get('final_kills', 0) / transformed['level'], 2)
    elif transformed['overall'].get('final_kills', 0) > 0:
        transformed['overall']['finals_per_star'] = float(transformed['overall'].get('final_kills', 0))
    else:
        transformed['overall']['finals_per_star'] = 0.0
        
    transformed['overall']['finals_per_game'] = calculate_finals_per_game(transformed['overall'].get('final_kills'), transformed['overall'].get('games_played'))
    transformed['overall']['bedwars_slumber_ticket_master'] = None # API only


    transformed['modes']['core'] = calculated_core_stats
    transformed['modes']['core']['wlr'] = calculate_ratio(calculated_core_stats.get('wins'), calculated_core_stats.get('losses'))
    transformed['modes']['core']['fkdr'] = calculate_ratio(calculated_core_stats.get('final_kills'), calculated_core_stats.get('final_deaths'))
    transformed['modes']['core']['bblr'] = calculate_ratio(calculated_core_stats.get('beds_broken'), calculated_core_stats.get('beds_lost'))
    transformed['modes']['core']['kdr'] = calculate_ratio(calculated_core_stats.get('kills'), calculated_core_stats.get('deaths'))
    transformed['modes']['core']['win_rate'] = calculate_win_rate(calculated_core_stats.get('wins'), calculated_core_stats.get('games_played'))
    transformed['modes']['core']['finals_per_game'] = calculate_finals_per_game(calculated_core_stats.get('final_kills'), calculated_core_stats.get('games_played'))


    for mode_key in individual_mode_map.values():
         mode_raw = raw_individual_modes_stats.get(mode_key, {})
         transformed['modes'][mode_key] = mode_raw
         mode_raw['wlr'] = calculate_ratio(mode_raw.get('wins'), mode_raw.get('losses'))
         mode_raw['fkdr'] = calculate_ratio(mode_raw.get('final_kills'), mode_raw.get('final_deaths'))
         mode_raw['bblr'] = calculate_ratio(mode_raw.get('beds_broken'), mode_raw.get('beds_lost'))
         mode_raw['kdr'] = calculate_ratio(mode_raw.get('kills'), mode_raw.get('deaths'))
         mode_raw['win_rate'] = calculate_win_rate(mode_raw.get('wins'), mode_raw.get('games_played'))
         mode_raw['finals_per_game'] = calculate_finals_per_game(mode_raw.get('final_kills'), mode_raw.get('games_played'))


    transformed['modes']['4v4'] = calculated_fouvfour_stats
    transformed['modes']['4v4']['wlr'] = calculate_ratio(calculated_fouvfour_stats.get('wins'), calculated_fouvfour_stats.get('losses'))
    transformed['modes']['4v4']['fkdr'] = calculate_ratio(calculated_fouvfour_stats.get('final_kills'), calculated_fouvfour_stats.get('final_deaths'))
    transformed['modes']['4v4']['bblr'] = calculate_ratio(calculated_fouvfour_stats.get('beds_broken'), calculated_fouvfour_stats.get('beds_lost'))
    transformed['modes']['4v4']['kdr'] = calculate_ratio(calculated_fouvfour_stats.get('kills'), calculated_fouvfour_stats.get('deaths'))
    transformed['modes']['4v4']['win_rate'] = calculate_win_rate(calculated_fouvfour_stats.get('wins'), calculated_fouvfour_stats.get('games_played'))
    transformed['modes']['4v4']['finals_per_game'] = calculate_finals_per_game(calculated_fouvfour_stats.get('final_kills'), calculated_fouvfour_stats.get('games_played'))


    most_played_gamemode = "N/A"
    max_games = -1
    scraped_mode_titles_for_most_played = {'Solo': 'Solos', 'Doubles': 'Doubles', '3v3v3v3': 'Threes', '4v4v4v4': 'Fours'}
    scraped_games_played = main_stats.get('Games Played', {})

    for scraped_mode, games_value in scraped_games_played.items():
        if scraped_mode in scraped_mode_titles_for_most_played:
            games = get_safe_int(games_value)
            if games > max_games:
                max_games = games
                most_played_gamemode = scraped_mode_titles_for_most_played[scraped_mode]

    if max_games > 0:
        transformed['most_played_gamemode'] = most_played_gamemode


    return transformed

def format_stats_for_display(stats_data):
    """Formats numerical stats and calculates ratios for display."""
    if not stats_data:
        return stats_data

    # Handle overall and mode sections
    sections_to_format = []
    if 'overall' in stats_data and stats_data['overall'] is not None:
        sections_to_format.append(stats_data['overall'])
    if 'modes' in stats_data:
        for mode_key in ['core', 'solos', 'doubles', 'threes', 'fours', '4v4']:
             mode_data = stats_data['modes'].get(mode_key)
             if mode_data is not None:
                sections_to_format.append(mode_data)


    for section in sections_to_format:
        for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths', 'coins', 'games_played']:
            section[f'{key}_formatted'] = format_number(section.get(key))

        slumber_key = 'bedwars_slumber_ticket_master'
        section[f'{slumber_key}_formatted'] = format_number(section.get(slumber_key))

        for ratio_key in ['wlr', 'fkdr', 'bblr', 'kdr', 'win_rate', 'finals_per_star', 'finals_per_game']:
             value = section.get(ratio_key)
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

         if result_data.get('fetched_by') == 'scrapper':
             stats_for_display = transform_scrapper_data(result_data)
         else:
             stats_for_display = result_data

         formatted_stats = format_stats_for_display(stats_for_display)

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
