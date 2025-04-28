from flask import Flask, render_template, jsonify, request, redirect, url_for
import hypixel_api
import json
import os # Import os module

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

    uuid = hypixel_api.get_player_uuid(username)
    if not uuid:
        return render_template('stats.html', error=f"Spieler '{username}' nicht gefunden.", username=username)

    stats = hypixel_api.get_player_stats(uuid)
    if not stats or 'error' in stats:
         return render_template('stats.html', error=stats.get('error', 'Unbekannter Fehler beim Abrufen der Stats.'), username=username)

    # Format numbers with dots as thousands separators for display
    for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths']:
        if key in stats and isinstance(stats[key], (int, float)):
            stats[f'{key}_formatted'] = "{:,}".format(stats[key]).replace(',', '.')
        else:
             stats[f'{key}_formatted'] = stats.get(key, 'N/A') # Keep original if not number or missing

    return render_template('stats.html', stats=stats, username=username)

@app.route('/compare', methods=['GET'])
def compare_stats_page():
    user1_orig = request.args.get('user1')
    user2_orig = request.args.get('user2')

    if not user1_orig or not user2_orig:
         return redirect(url_for('index'))

    # Use lowercase for lookup, but pass original names to template
    user1_lower = user1_orig.lower()
    user2_lower = user2_orig.lower()

    stats_dict = hypixel_api.get_multiple_player_stats([user1_orig, user2_orig])

    # Retrieve stats using lowercase keys
    stats1 = stats_dict.get(user1_lower)
    stats2 = stats_dict.get(user2_lower)

    # Add original usernames back for display if needed, or use the ones from args
    if stats1 and 'username' not in stats1: stats1['username'] = user1_orig
    if stats2 and 'username' not in stats2: stats2['username'] = user2_orig

    # Format numbers for display in comparison
    def format_stats_for_compare(stats_data):
        if stats_data and 'error' not in stats_data:
            for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths']:
                 if key in stats_data and isinstance(stats_data[key], (int, float)):
                    stats_data[f'{key}_formatted'] = "{:,}".format(stats_data[key]).replace(',', '.')
                 else:
                     stats_data[f'{key}_formatted'] = stats_data.get(key, 'N/A')
        return stats_data

    stats1 = format_stats_for_compare(stats1)
    stats2 = format_stats_for_compare(stats2)


    return render_template('compare.html',
                           user1=user1_orig, # Pass original names
                           user2=user2_orig,
                           stats1=stats1,
                           stats2=stats2)


# --- API Endpoints ---

@app.route('/api/player/<username>', methods=['GET'])
def api_get_player_stats(username):
    uuid = hypixel_api.get_player_uuid(username)
    if not uuid:
        return jsonify({"error": "Spieler nicht gefunden"}), 404

    stats = hypixel_api.get_player_stats(uuid)
    if not stats or 'error' in stats:
        return jsonify({"error": stats.get('error', 'Fehler beim Abrufen der Stats')}), 500

    return jsonify(stats)

@app.route('/api/compare', methods=['GET'])
def api_compare_players():
    usernames_str = request.args.get('users')
    if not usernames_str:
        return jsonify({"error": "Keine Benutzernamen angegeben"}), 400

    usernames = [name.strip() for name in usernames_str.split(',') if name.strip()]
    if len(usernames) < 2:
         return jsonify({"error": "Mindestens zwei Benutzernamen für den Vergleich erforderlich"}), 400

    stats = hypixel_api.get_multiple_player_stats(usernames)
    return jsonify(stats)


if __name__ == '__main__':
    # Make sure the server is accessible on the network, useful for testing on other devices
    # Use 0.0.0.0 to listen on all available network interfaces
    # The default port is 5000
    app.run(host='0.0.0.0', port=5000, debug=True) # Debug-Modus für Entwicklung aktivieren
