from flask import Flask, render_template, jsonify, request, redirect, url_for
import hypixel_api
import json
import os

app = Flask(__name__)

if not os.path.exists('static'):
    os.makedirs('static')
if not os.path.exists('static/css'):
    os.makedirs('static/css')
if not os.path.exists('static/js'):
    os.makedirs('static/js')

if not os.path.exists('templates'):
    os.makedirs('templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/player', methods=['GET'])
def player_stats_page():
    username = request.args.get('username')
    if not username:
        return redirect(url_for('index'))

    result_data = hypixel_api.fetch_player_data(username)

    if result_data and 'error' in result_data:
        if result_data['error'] == 'name_changed':
            return render_template('stats.html',
                                   error_type='name_changed',
                                   original_search=result_data.get('original_search'),
                                   current_name=result_data.get('current_name'),
                                   uuid=result_data.get('uuid'))
        else:
            return render_template('stats.html',
                                   error=result_data.get('error'),
                                   username=result_data.get('original_search', username))
    elif result_data:
        for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths']:
            if key in result_data and isinstance(result_data[key], (int, float)):
                result_data[f'{key}_formatted'] = "{:,}".format(result_data[key]).replace(',', '.')
            else:
                 result_data[f'{key}_formatted'] = result_data.get(key, 'N/A')

        return render_template('stats.html', stats=result_data, username=result_data.get('username'))
    else:
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

    def format_stats_for_compare(stats_data):
        if stats_data and not stats_data.get('error'):
            if stats_data.get('error') != 'name_changed':
                for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths']:
                     if key in stats_data and isinstance(stats_data[key], (int, float)):
                        stats_data[f'{key}_formatted'] = "{:,}".format(stats_data[key]).replace(',', '.')
                     else:
                         stats_data[f'{key}_formatted'] = stats_data.get(key, 'N/A')
        return stats_data

    stats1_formatted = format_stats_for_compare(stats1_result)
    stats2_formatted = format_stats_for_compare(stats2_result)

    return render_template('compare.html',
                           user1=user1_orig,
                           user2=user2_orig,
                           stats1=stats1_formatted,
                           stats2=stats2_formatted)


@app.route('/api/player/<username>', methods=['GET'])
def api_get_player_stats(username):
    result_data = hypixel_api.fetch_player_data(username)

    if result_data and 'error' in result_data:
         status_code = 404 if result_data['error'] != 'name_changed' and 'API' not in result_data['error'] and 'Internal' not in result_data['error'] else 400 if result_data['error'] == 'name_changed' else 500
         return jsonify(result_data), status_code
    elif result_data:
        return jsonify(result_data), 200
    else:
        return jsonify({"error": "Unknown server error"}), 500


@app.route('/api/compare', methods=['GET'])
def api_compare_players():
    usernames_str = request.args.get('users')
    if not usernames_str:
        return jsonify({"error": "No usernames provided"}), 400

    usernames = [name.strip() for name in usernames_str.split(',') if name.strip()]
    if len(usernames) < 2:
         return jsonify({"error": "At least two usernames required for comparison"}), 400

    stats_results = hypixel_api.fetch_multiple_player_data(usernames)

    has_error = any(res and 'error' in res for res in stats_results.values())
    status_code = 400 if has_error else 200

    return jsonify(stats_results), status_code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
