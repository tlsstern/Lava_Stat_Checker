import scrapper
import app
import sys
import json
from flask import Flask

def debug_full_flow():
    username = "Technoblade" if len(sys.argv) < 2 else sys.argv[1]
    print(f"\n=== DEBUGGING FULL FLOW FOR: {username} ===\n")
    
    # Step 1: Get raw data from scraper
    print(f"Step 1: Scraping data for {username}")
    scraped_data = scrapper.scrape_bwstats(username)
    print(f"  Raw level from scraper: {repr(scraped_data.get('level'))}")
    
    # Step 2: Transform the data
    print("\nStep 2: Transforming scraped data")
    transformed_data = app.transform_scraped_data(scraped_data, username)
    print(f"  Level after transform: {repr(transformed_data.get('level'))}")
    
    # Step 3: Apply formatting to the data (simulating what happens before template render)
    print("\nStep 3: Applying formatting to overall stats")
    if 'overall' in transformed_data:
        transformed_data['overall'] = app.format_stat_section(transformed_data['overall'])
    else:
        print("  No overall stats found to format")
    
    # Also format the mode stats
    if 'modes' in transformed_data:
        for mode_key, mode_data in transformed_data['modes'].items():
            if mode_data:
                transformed_data['modes'][mode_key] = app.format_stat_section(mode_data)
    
    # Step 4: Inspect the formatted level value that would be displayed
    print("\nStep 4: Final values that would be displayed in template")
    print(f"  Level (direct): {transformed_data.get('level')}")
    # Check if level is being formatted elsewhere
    level_formatted = None
    if 'level_formatted' in transformed_data:
        level_formatted = transformed_data['level_formatted']
    print(f"  Level formatted: {level_formatted}")
    
    # Check how the value is used in calculations
    print("\nStep 5: Check overall calculations that use level")
    if 'overall' in transformed_data:
        finals_per_star = transformed_data['overall'].get('finals_per_star')
        print(f"  Finals per star: {finals_per_star}")
        
        # Check raw calculation
        final_kills = scraped_data.get('main_stats', {}).get('Final Kills', {}).get('Overall')
        print(f"  Raw final kills: {final_kills}")
        if scraped_data.get('level') and final_kills:
            try:
                level_value = float(scraped_data.get('level').replace(',', '').replace('✫', '').strip())
                final_kills_value = float(final_kills.replace(',', ''))
                manual_calc = round(final_kills_value / level_value, 2)
                print(f"  Manual finals_per_star calculation: {manual_calc}")
            except (ValueError, ZeroDivisionError, AttributeError) as e:
                print(f"  Error in manual calculation: {e}")
    
    # Step 6: Check mode stats formatting
    print("\nStep 6: Checking formatting of mode stats")
    if 'modes' in transformed_data:
        for mode_key, mode_data in transformed_data['modes'].items():
            print(f"  Mode {mode_key} games played: {mode_data.get('games_played')}")
    
    # Step 7: Full data dump for inspection
    print("\nStep 7: Full transformed data dump")
    print(f"  Player username: {transformed_data.get('username')}")
    print(f"  Player level: {transformed_data.get('level')}")
    print(f"  Fetched by: {transformed_data.get('fetched_by')}")
    print("  --- Overall Stats Sample ---")
    if 'overall' in transformed_data:
        for key in ['wins', 'losses', 'final_kills', 'final_deaths']:
            print(f"    {key}: {transformed_data['overall'].get(key)}, formatted: {transformed_data['overall'].get(f'{key}_formatted')}")
    
    # Check if a Flask app is currently running
    try:
        test_app = Flask(__name__)
        with test_app.app_context():
            # Simulate template rendering logic
            level_display = f"{transformed_data.get('level')}"
            print(f"\nSimulated template display of level: {level_display}")
    except Exception as e:
        print(f"Error creating Flask context: {e}")

if __name__ == "__main__":
    debug_full_flow() 