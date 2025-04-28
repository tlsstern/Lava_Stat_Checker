from flask import Flask, render_template, jsonify, request, redirect, url_for
import hypixel_api # Make sure this imports the updated hypixel_api.py
import json
import os

app = Flask(__name__)

# Ensure the static folder exists
if not os.path.exists('static'):
    os.makedirs('static')
if not os.path.exists('static/css'):
    os.makedirs('static/css')
if not os.path.exists('static/js'):
    os.makedirs('static/js')

# Ensure the templates folder exists
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

    # Use the combined fetch function
    result_data = hypixel_api.fetch_player_data(username)

    # Check the result type
    if result_data and 'error' in result_data:
        if result_data['error'] == 'name_changed':
            # Special case: Name searched is old, inform the user
            return render_template('stats.html',
                                   error_type='name_changed',
                                   original_search=result_data.get('original_search'),
                                   current_name=result_data.get('current_name'),
                                   uuid=result_data.get('uuid')) # Pass UUID for potential link
        else:
            # General error (player not found, API error, etc.)
            return render_template('stats.html',
                                   error=result_data.get('error'),
                                   username=result_data.get('original_search', username)) # Show searched name in error
    elif result_data:
         # Success: Found player with matching name
         # Format numbers with dots as thousands separators for display
        for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths']:
            if key in result_data and isinstance(result_data[key], (int, float)):
                result_data[f'{key}_formatted'] = "{:,}".format(result_data[key]).replace(',', '.')
            else:
                 result_data[f'{key}_formatted'] = result_data.get(key, 'N/A')

        return render_template('stats.html', stats=result_data, username=result_data.get('username')) # Display current name
    else:
         # Should not happen if fetch_player_data always returns a dict, but handle defensively
         return render_template('stats.html', error="Unbekannter Fehler beim Abrufen der Daten.", username=username)


@app.route('/compare', methods=['GET'])
def compare_stats_page():
    user1_orig = request.args.get('user1')
    user2_orig = request.args.get('user2')

    if not user1_orig or not user2_orig:
         return redirect(url_for('index'))

    # Use the combined fetch function for multiple players
    stats_dict_results = hypixel_api.fetch_multiple_player_data([user1_orig, user2_orig])

    # Retrieve results using lowercase keys (as fetch_multiple_player_data uses them)
    stats1_result = stats_dict_results.get(user1_orig.lower())
    stats2_result = stats_dict_results.get(user2_orig.lower())

    # Format numbers for display if stats are valid
    def format_stats_for_compare(stats_data):
        if stats_data and 'error' not in stats_data:
            # Ensure it's not the 'name_changed' error structure
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
                           user1=user1_orig, # Pass original names for display
                           user2=user2_orig,
                           stats1=stats1_formatted, # Pass potentially formatted stats or error dict
                           stats2=stats2_formatted)


# --- API Endpoints (Consider updating if needed, but primary change is in page routes) ---

@app.route('/api/player/<username>', methods=['GET'])
def api_get_player_stats(username):
    # Use the combined fetch function for the API endpoint as well
    result_data = hypixel_api.fetch_player_data(username)

    if result_data and 'error' in result_data:
         # Return appropriate error code based on the error type
         status_code = 404 if result_data['error'] != 'name_changed' and 'API Fehler' not in result_data['error'] and 'Interner Serverfehler' not in result_data['error'] else 400 if result_data['error'] == 'name_changed' else 500
         return jsonify(result_data), status_code
    elif result_data:
        return jsonify(result_data), 200
    else:
        return jsonify({"error": "Unbekannter Fehler"}), 500


@app.route('/api/compare', methods=['GET'])
def api_compare_players():
    usernames_str = request.args.get('users')
    if not usernames_str:
        return jsonify({"error": "Keine Benutzernamen angegeben"}), 400

    usernames = [name.strip() for name in usernames_str.split(',') if name.strip()]
    if len(usernames) < 2:
         return jsonify({"error": "Mindestens zwei Benutzernamen für den Vergleich erforderlich"}), 400

    # Use the combined fetch function for multiple players
    stats_results = hypixel_api.fetch_multiple_player_data(usernames)
    # Check if any result has an error to potentially adjust the overall status code
    has_error = any(res and 'error' in res for res in stats_results.values())
    status_code = 400 if has_error else 200 # Simplified status, could be more granular

    return jsonify(stats_results), status_code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
