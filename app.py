# app.py
from flask import Flask, render_template, jsonify, request, redirect, url_for
import hypixel_api # Import the updated hypixel_api module
import json
import os # Import os module for path operations

app = Flask(__name__)

# --- Ensure necessary directories exist ---
# Create static directories if they don't exist
if not os.path.exists('static'):
    os.makedirs('static')
if not os.path.exists('static/css'):
    os.makedirs('static/css')
if not os.path.exists('static/js'):
    os.makedirs('static/js')
# Create templates directory if it doesn't exist
if not os.path.exists('templates'):
    os.makedirs('templates')

# --- Route Definitions ---

@app.route('/')
def index():
    """Renders the main search page."""
    print("Rendering index page")
    return render_template('index.html')

@app.route('/player', methods=['GET'])
def player_stats_page():
    """Handles single player search and displays stats or errors."""
    username = request.args.get('username')
    print(f"Received request for player stats: {username}")
    if not username:
        print("No username provided, redirecting to index.")
        return redirect(url_for('index'))

    # Use the combined fetch function from hypixel_api
    result_data = hypixel_api.fetch_player_data(username)
    print(f"Result from fetch_player_data for {username}: {result_data.get('error', 'Success')}")

    # Check the result type
    if result_data and 'error' in result_data:
        if result_data['error'] == 'name_changed':
            # Special case: Name searched is old, inform the user
            print(f"Rendering name changed warning for search '{username}', current name '{result_data.get('current_name')}'")
            return render_template('stats.html',
                                   error_type='name_changed', # Pass specific error type to template
                                   original_search=result_data.get('original_search'),
                                   current_name=result_data.get('current_name'),
                                   uuid=result_data.get('uuid')) # Pass UUID for potential link
        else:
            # General error (player not found, API error, etc.)
            print(f"Rendering general error for {username}: {result_data.get('error')}")
            return render_template('stats.html',
                                   error=result_data.get('error'), # Pass the error message
                                   username=result_data.get('original_search', username)) # Show searched name in error context
    elif result_data:
         # Success: Found player with matching name
         print(f"Rendering stats page for {result_data.get('username')}")
         # Format numbers with dots as thousands separators for display
         # Iterate through keys that need formatting
         for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths']:
            if key in result_data and isinstance(result_data[key], (int, float)):
                # Create a new key with '_formatted' suffix
                result_data[f'{key}_formatted'] = "{:,}".format(result_data[key]).replace(',', '.')
            else:
                 # If key doesn't exist or isn't a number, use original value or 'N/A'
                 result_data[f'{key}_formatted'] = result_data.get(key, 'N/A')

         # Render the stats template with the fetched and formatted data
         return render_template('stats.html', stats=result_data, username=result_data.get('username')) # Display current name
    else:
         # Fallback case (should not happen if fetch_player_data works correctly)
         print(f"Unknown error or empty result for {username}")
         return render_template('stats.html', error="Unknown error fetching data.", username=username)


@app.route('/compare', methods=['GET'])
def compare_stats_page():
    """Handles comparison between two players."""
    user1_orig = request.args.get('user1')
    user2_orig = request.args.get('user2')
    print(f"Received request to compare: {user1_orig} vs {user2_orig}")

    if not user1_orig or not user2_orig:
         print("Missing one or both usernames for comparison, redirecting to index.")
         return redirect(url_for('index'))

    # Use the combined fetch function for multiple players
    stats_dict_results = hypixel_api.fetch_multiple_player_data([user1_orig, user2_orig])
    print(f"Results from fetch_multiple_player_data: {stats_dict_results}")

    # Retrieve results using lowercase keys (as fetch_multiple_player_data uses them)
    stats1_result = stats_dict_results.get(user1_orig.lower())
    stats2_result = stats_dict_results.get(user2_orig.lower())

    # Helper function to format numbers for display in comparison, handles errors
    def format_stats_for_compare(stats_data):
        # Check if stats_data is valid and not an error dictionary
        if stats_data and not stats_data.get('error'):
            # Iterate through keys needing formatting
            for key in ['wins', 'losses', 'final_kills', 'final_deaths', 'beds_broken', 'beds_lost', 'kills', 'deaths']:
                 if key in stats_data and isinstance(stats_data[key], (int, float)):
                    # Add formatted version
                    stats_data[f'{key}_formatted'] = "{:,}".format(stats_data[key]).replace(',', '.')
                 else:
                     # Ensure formatted key exists even if value is missing or not number
                     stats_data[f'{key}_formatted'] = stats_data.get(key, 'N/A')
        # Return the modified dictionary (or original if it was an error/None)
        return stats_data

    # Format stats for both players
    stats1_formatted = format_stats_for_compare(stats1_result)
    stats2_formatted = format_stats_for_compare(stats2_result)
    print(f"Formatted stats for comparison: User1={stats1_formatted}, User2={stats2_formatted}")

    # Render the comparison template
    return render_template('compare.html',
                           user1=user1_orig, # Pass original names for display
                           user2=user2_orig,
                           stats1=stats1_formatted, # Pass potentially formatted stats or error dict
                           stats2=stats2_formatted)


# --- API Endpoints (for potential future use with JavaScript) ---

@app.route('/api/player/<username>', methods=['GET'])
def api_get_player_stats(username):
    """API endpoint to get stats for a single player."""
    print(f"API request for player: {username}")
    # Use the combined fetch function for the API endpoint as well
    result_data = hypixel_api.fetch_player_data(username)

    if result_data and 'error' in result_data:
         # Return appropriate error code based on the error type
         # 404 for not found, 400 for name changed (client error), 500 for server/API issues
         status_code = 404 if result_data['error'] != 'name_changed' and 'API' not in result_data['error'] and 'Internal' not in result_data['error'] else 400 if result_data['error'] == 'name_changed' else 500
         print(f"API error for {username}: {result_data['error']}, status: {status_code}")
         return jsonify(result_data), status_code
    elif result_data:
        print(f"API success for {username}")
        return jsonify(result_data), 200 # OK status
    else:
        print(f"API unknown error for {username}")
        return jsonify({"error": "Unknown server error"}), 500 # Internal Server Error


@app.route('/api/compare', methods=['GET'])
def api_compare_players():
    """API endpoint to get stats for multiple players for comparison."""
    usernames_str = request.args.get('users') # e.g., users=PlayerA,PlayerB
    print(f"API request for comparison: users={usernames_str}")
    if not usernames_str:
        print("API compare error: No users provided.")
        return jsonify({"error": "No usernames provided"}), 400 # Bad Request

    # Split and clean usernames
    usernames = [name.strip() for name in usernames_str.split(',') if name.strip()]
    if len(usernames) < 2:
         print("API compare error: Less than two users provided.")
         return jsonify({"error": "At least two usernames required for comparison"}), 400 # Bad Request

    # Use the combined fetch function for multiple players
    stats_results = hypixel_api.fetch_multiple_player_data(usernames)
    print(f"API compare results: {stats_results}")

    # Check if any result has an error to potentially adjust the overall status code
    # A simple check: if any error exists, return 400, otherwise 200. Could be more granular.
    has_error = any(res and 'error' in res for res in stats_results.values())
    status_code = 400 if has_error else 200 # Bad Request if any error, otherwise OK

    return jsonify(stats_results), status_code


# --- Main execution block ---
if __name__ == '__main__':
    print("Starting Flask development server...")
    # Run the Flask app
    # host='0.0.0.0' makes the server accessible on your network
    # debug=True enables auto-reloading and detailed error pages (disable for production)
    app.run(host='0.0.0.0', port=5000, debug=True)
