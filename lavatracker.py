"""
LavaTracker - Comprehensive Bedwars Stats Tracker
Fetches and stores detailed player statistics from Hypixel API
"""

import os
import json
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('LavaTracker')

class LavaTracker:
    def __init__(self):
        # Initialize Supabase client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.hypixel_api_key = os.getenv('HYPIXEL_API_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        if not self.hypixel_api_key or self.hypixel_api_key.lower() == 'off':
            raise ValueError("Valid Hypixel API key required for LavaTracker")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("LavaTracker initialized successfully")
    
    def get_bedwars_level(self, exp: int) -> float:
        """Calculate Bedwars level from experience"""
        if not isinstance(exp, int) or exp < 0:
            return 0.0
        
        level = 100 * (exp // 487000)
        exp = exp % 487000
        
        if exp < 500: return level + exp / 500
        level += 1
        if exp < 1500: return level + (exp - 500) / 1000
        level += 1
        if exp < 3500: return level + (exp - 1500) / 2000
        level += 1
        if exp < 7000: return level + (exp - 3500) / 3500
        level += 1
        exp -= 7000
        return level + exp / 5000
    
    def calculate_ratio(self, numerator: int, denominator: int) -> float:
        """Calculate ratio safely"""
        if denominator == 0:
            return float(numerator) if numerator > 0 else 0.0
        return round(numerator / denominator, 3)
    
    def fetch_player_stats(self, uuid: str) -> Optional[Dict[str, Any]]:
        """Fetch player stats from Hypixel API"""
        try:
            url = f"https://api.hypixel.net/v2/player"
            params = {"key": self.hypixel_api_key, "uuid": uuid}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("success") or not data.get("player"):
                logger.error(f"Failed to fetch stats for UUID {uuid}")
                return None
            
            return data["player"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error for UUID {uuid}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching stats for UUID {uuid}: {e}")
            return None
    
    def parse_bedwars_stats(self, player_data: Dict) -> Dict[str, Any]:
        """Parse Bedwars stats from player data"""
        stats = player_data.get("stats", {})
        bw_stats = stats.get("Bedwars", {})
        achievements = player_data.get("achievements", {})
        
        # Calculate level
        exp = bw_stats.get("Experience", 0)
        level = int(self.get_bedwars_level(exp))
        
        # Overall stats
        wins = bw_stats.get("wins_bedwars", 0)
        losses = bw_stats.get("losses_bedwars", 0)
        games_played = wins + losses
        
        kills = bw_stats.get("kills_bedwars", 0)
        deaths = bw_stats.get("deaths_bedwars", 0)
        
        final_kills = bw_stats.get("final_kills_bedwars", 0)
        final_deaths = bw_stats.get("final_deaths_bedwars", 0)
        
        beds_broken = bw_stats.get("beds_broken_bedwars", 0)
        beds_lost = bw_stats.get("beds_lost_bedwars", 0)
        
        # Calculate ratios
        wlr = self.calculate_ratio(wins, losses)
        winrate = round((wins / games_played * 100), 2) if games_played > 0 else 0.0
        kdr = self.calculate_ratio(kills, deaths)
        fkdr = self.calculate_ratio(final_kills, final_deaths)
        bblr = self.calculate_ratio(beds_broken, beds_lost)
        
        # Per-star metrics
        finals_per_star = round(final_kills / level, 3) if level > 0 else 0.0
        wins_per_star = round(wins / level, 3) if level > 0 else 0.0
        
        # Resources collected
        iron_collected = bw_stats.get("iron_resources_collected_bedwars", 0)
        gold_collected = bw_stats.get("gold_resources_collected_bedwars", 0)
        diamonds_collected = bw_stats.get("diamond_resources_collected_bedwars", 0)
        emeralds_collected = bw_stats.get("emerald_resources_collected_bedwars", 0)
        
        # Mode-specific stats
        solo_stats = self.extract_mode_stats(bw_stats, "eight_one_")
        doubles_stats = self.extract_mode_stats(bw_stats, "eight_two_")
        threes_stats = self.extract_mode_stats(bw_stats, "four_three_")
        fours_stats = self.extract_mode_stats(bw_stats, "four_four_")
        four_v_four_stats = self.extract_mode_stats(bw_stats, "two_four_")
        
        # Calculate most played mode
        mode_games = {
            "Solo": solo_stats.get("games_played", 0),
            "Doubles": doubles_stats.get("games_played", 0),
            "3v3v3v3": threes_stats.get("games_played", 0),
            "4v4v4v4": fours_stats.get("games_played", 0),
            "4v4": four_v_four_stats.get("games_played", 0)
        }
        most_played_mode = max(mode_games, key=mode_games.get) if any(mode_games.values()) else "None"
        most_played_games = mode_games[most_played_mode] if most_played_mode != "None" else 0
        
        return {
            "player_name": player_data.get("displayname", "Unknown"),
            "level": level,
            "exp": exp,
            "coins": bw_stats.get("coins", 0),
            "games_played": games_played,
            "wins": wins,
            "losses": losses,
            "win_loss_ratio": wlr,
            "winrate": winrate,
            "kills": kills,
            "deaths": deaths,
            "kill_death_ratio": kdr,
            "final_kills": final_kills,
            "final_deaths": final_deaths,
            "final_kill_death_ratio": fkdr,
            "beds_broken": beds_broken,
            "beds_lost": beds_lost,
            "bed_break_loss_ratio": bblr,
            "iron_collected": iron_collected,
            "gold_collected": gold_collected,
            "diamonds_collected": diamonds_collected,
            "emeralds_collected": emeralds_collected,
            "items_purchased": bw_stats.get("_items_purchased_bedwars", 0),
            "winstreak": bw_stats.get("winstreak", 0),
            "finals_per_star": finals_per_star,
            "wins_per_star": wins_per_star,
            "most_played_mode": most_played_mode,
            "most_played_games": most_played_games,
            "solo_stats": json.dumps(solo_stats),
            "doubles_stats": json.dumps(doubles_stats),
            "threes_stats": json.dumps(threes_stats),
            "fours_stats": json.dumps(fours_stats),
            "four_v_four_stats": json.dumps(four_v_four_stats),
            "raw_stats": json.dumps(bw_stats)
        }
    
    def extract_mode_stats(self, bw_stats: Dict, prefix: str) -> Dict[str, Any]:
        """Extract stats for a specific game mode"""
        return {
            "wins": bw_stats.get(f"{prefix}wins_bedwars", 0),
            "losses": bw_stats.get(f"{prefix}losses_bedwars", 0),
            "kills": bw_stats.get(f"{prefix}kills_bedwars", 0),
            "deaths": bw_stats.get(f"{prefix}deaths_bedwars", 0),
            "final_kills": bw_stats.get(f"{prefix}final_kills_bedwars", 0),
            "final_deaths": bw_stats.get(f"{prefix}final_deaths_bedwars", 0),
            "beds_broken": bw_stats.get(f"{prefix}beds_broken_bedwars", 0),
            "beds_lost": bw_stats.get(f"{prefix}beds_lost_bedwars", 0),
            "games_played": bw_stats.get(f"{prefix}games_played_bedwars", 0),
            "winstreak": bw_stats.get(f"{prefix}winstreak", 0)
        }
    
    def save_tracked_stats(self, uuid: str, stats: Dict[str, Any]) -> bool:
        """Save tracked stats to Supabase"""
        try:
            # Add UUID and timestamp
            stats["player_uuid"] = uuid
            stats["tracked_at"] = datetime.now(timezone.utc).isoformat()
            stats["updated_at"] = datetime.now(timezone.utc).isoformat()
            stats["fetched_from"] = "hypixel_api"
            
            # Insert into database
            result = self.supabase.table('tracked_stats').insert(stats).execute()
            
            if result.data:
                logger.info(f"Successfully saved stats for {stats['player_name']} ({uuid})")
                return True
            else:
                logger.error(f"Failed to save stats for {uuid}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving stats for {uuid}: {e}")
            return False
    
    def track_player(self, uuid: str) -> bool:
        """Main method to track a player's stats"""
        logger.info(f"Tracking player with UUID: {uuid}")
        
        # Fetch player data
        player_data = self.fetch_player_stats(uuid)
        if not player_data:
            logger.error(f"Could not fetch data for UUID: {uuid}")
            return False
        
        # Parse Bedwars stats
        stats = self.parse_bedwars_stats(player_data)
        
        # Save to database
        return self.save_tracked_stats(uuid, stats)
    
    def track_multiple_players(self, uuids: List[str]) -> Dict[str, bool]:
        """Track multiple players"""
        results = {}
        for uuid in uuids:
            results[uuid] = self.track_player(uuid)
        return results
    
    def get_all_players_from_db(self) -> List[Dict[str, str]]:
        """Get all players from the players table"""
        try:
            result = self.supabase.table('players').select('uuid, player_name').execute()
            if result.data:
                return result.data
            return []
        except Exception as e:
            logger.error(f"Error fetching players from database: {e}")
            return []
    
    def track_all_players(self):
        """Track all players in the database"""
        players = self.get_all_players_from_db()
        
        if not players:
            logger.warning("No players found in database")
            return
        
        logger.info(f"Tracking {len(players)} players...")
        
        success_count = 0
        for player in players:
            uuid = player['uuid']
            name = player['player_name']
            
            logger.info(f"Tracking {name} ({uuid})...")
            if self.track_player(uuid):
                success_count += 1
            
        logger.info(f"Tracking complete: {success_count}/{len(players)} players tracked successfully")

def main():
    """Main function to run the tracker"""
    try:
        tracker = LavaTracker()
        
        # Example: Track all players
        tracker.track_all_players()
        
        # Example: Track specific player
        # tracker.track_player("uuid-here")
        
        # Example: Track multiple specific players
        # uuids = ["uuid1", "uuid2", "uuid3"]
        # results = tracker.track_multiple_players(uuids)
        # print(f"Tracking results: {results}")
        
    except Exception as e:
        logger.error(f"Failed to initialize LavaTracker: {e}")

if __name__ == "__main__":
    main()