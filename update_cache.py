#!/usr/bin/env python3
"""
Cache Update Script
Run this locally to update the cache for popular players.
The Render deployment will use this cached data.
"""

import scrapper
import time
import sys
from datetime import datetime

# Add your most searched players here
POPULAR_PLAYERS = [
    'Technoblade', 'Dream', 'Gamerboy80', 'Purpled',
    'Hannahxxrose', 'Wallibear', 'gqtor', 'chazm',
    'Dewier', 'Bombies', 'Manhal_IQ_', 'Aquavrse',
    'Krtzyy', 'Sypherpk', 'xNestorio', 'Calvin',
    # Add more players as needed
]

def update_cache(players=None):
    """Update cache for specified players or use default list"""
    if players is None:
        players = POPULAR_PLAYERS
    
    print(f"Cache Update Starting - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Updating {len(players)} players...")
    print("-" * 50)
    
    success_count = 0
    failed_players = []
    
    for i, player in enumerate(players, 1):
        print(f"[{i}/{len(players)}] Updating {player}...", end=" ")
        
        try:
            result = scrapper.scrape_bwstats(player)
            
            if 'error' not in result:
                print("✓ Success")
                success_count += 1
            else:
                print(f"✗ Failed: {result['error']}")
                failed_players.append(player)
        except Exception as e:
            print(f"✗ Error: {e}")
            failed_players.append(player)
        
        # Be nice to the server - wait between requests
        if i < len(players):
            time.sleep(2)
    
    print("-" * 50)
    print(f"Cache Update Complete!")
    print(f"Success: {success_count}/{len(players)}")
    
    if failed_players:
        print(f"Failed players: {', '.join(failed_players)}")
        print("These players might not exist or may be temporarily unavailable.")
    
    print(f"\nCache will be used by Render deployment for up to 7 days.")
    print("Run this script daily for best results.")

def main():
    """Main function with argument parsing"""
    if len(sys.argv) > 1:
        # Custom players provided as arguments
        custom_players = sys.argv[1:]
        print(f"Updating custom players: {', '.join(custom_players)}")
        update_cache(custom_players)
    else:
        # Use default popular players
        update_cache()

if __name__ == "__main__":
    main()