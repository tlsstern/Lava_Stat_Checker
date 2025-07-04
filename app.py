# Lava_Stat_Checker/app.py
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
        return int(float(str(value).replace(',', '')))
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
    using only the overall stats provided by the scrapper.
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
        'level': get_safe_int(scraped_data.get('star')),
        'most_played_gamemode': scraped_data.get('most_played', 'N/A'),
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

    transformed['overall']['wins'] = get_safe_int(scraped_data.get('Wins'))
    transformed['overall']['losses'] = get_safe_int(scraped_data.get('Losses'))
    transformed['overall']['final_kills'] = get_safe_int(scraped_data.get('Final Kills'))
    transformed['overall']['final_deaths'] = get_safe_int(scraped_data.get('Final Deaths'))
    transformed['overall']['beds_broken'] = get_safe_int(scraped_data.get('Beds Broken'))
    transformed['overall']['beds_lost'] = get_safe_int(scraped_data.get('Beds Lost'))
    transformed['overall']['kills'] = get_safe_int(scraped_data.get('Kills'))
    transformed['overall']['deaths'] = get_safe_int(scraped_data.get('Deaths'))
    transformed['overall']['games_played'] = get_safe_int(scraped_data.get('Games Played'))
    transformed['overall']['coins'] = 0
    transformed['overall']['bedwars_slumber_ticket_master'] = None

    transformed['overall']['wlr'] = scraped_data.get('Win/Loss Ratio')
    transformed['overall']['fkdr'] = scraped_data.get('Final K/D Ratio (FKDR)')
    transformed['overall']['bblr'] = scraped_data.get('Beds B/L Ratio (BBLR)')
    transformed['overall']['kdr'] = scraped_data.get('K/D Ratio (KDR)')

    transformed['overall']['win_rate'] = calculate_win_rate(transformed['overall'].get('wins'), transformed['overall'].get('games_played'))
    transformed['overall']['finals_per_game'] = calculate_finals_per_game(transformed['overall'].get('final_kills'), transformed['overall'].get('games_played'))

    if transformed['level'] and transformed['level'] > 0:
        transformed['overall']['finals_per_star'] = round(transformed['overall'].get('final_kills', 0) / transformed['level'], 2)
    elif transformed['overall'].get('final_kills', 0) > 0:
        transformed['overall']['finals_per_star'] = float(transformed['overall'].get('final_kills', 0))
    else:
        transformed['overall']['finals_per_star'] = 0.0

    transformed['modes']['core'] = transformed['overall'].copy()
    transformed['modes']['4v4'] = transformed['overall'].copy()

    return transformed

def format_stats_for_display(stats_data):
    """Formats numerical stats and calculates ratios for display."""
    if not stats_data:
        return stats_data

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
                 section[ratio_key] = 'N/A'


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