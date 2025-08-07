import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from supabase import create_client, Client
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseHandler:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.url or not self.key:
            logger.warning("Supabase credentials not found. Cache will be disabled.")
            self.client = None
        else:
            self.client: Client = create_client(self.url, self.key)
            logger.info("Supabase client initialized successfully")
    
    def get_player_uuid(self, username: str) -> Optional[str]:
        """Get player UUID from Mojang API"""
        try:
            response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}")
            if response.status_code == 200:
                data = response.json()
                uuid = data.get('id')
                # Format UUID with dashes
                if uuid and len(uuid) == 32:
                    formatted_uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
                    return formatted_uuid
            return None
        except Exception as e:
            logger.error(f"Error fetching UUID for {username}: {e}")
            return None
    
    def ensure_player_exists(self, uuid: str, username: str, category: str = "bedwars"):
        """Ensure player exists in players table"""
        if not self.client:
            return
        
        try:
            # Check if player exists
            result = self.client.table('players').select('*').eq('uuid', uuid).execute()
            
            if not result.data:
                # Insert new player
                self.client.table('players').insert({
                    'uuid': uuid,
                    'player_name': username,
                    'category': category
                }).execute()
                logger.info(f"Created new player record for {username} ({uuid})")
            else:
                # Update player name if changed
                current_name = result.data[0].get('player_name')
                if current_name != username:
                    self.client.table('players').update({
                        'player_name': username,
                        'updated_at': datetime.utcnow().isoformat()
                    }).eq('uuid', uuid).execute()
                    logger.info(f"Updated player name from {current_name} to {username}")
        except Exception as e:
            logger.error(f"Error ensuring player exists: {e}")
    
    def get_cached_stats(self, username: str, max_age_hours: int = 1) -> Optional[Dict[str, Any]]:
        """Get cached stats from Supabase"""
        if not self.client:
            return None
        
        try:
            # First try to get UUID
            uuid = self.get_player_uuid(username)
            if not uuid:
                # If can't get UUID, try by username directly
                result = self.client.rpc('get_latest_stats_by_ign', {'p_ign': username}).execute()
            else:
                result = self.client.rpc('get_latest_stats', {'p_uuid': uuid}).execute()
            
            if result.data and len(result.data) > 0:
                stats = result.data[0]
                # Check if stats are fresh enough
                updated_at = datetime.fromisoformat(stats['updated_at'].replace('Z', '+00:00'))
                if datetime.utcnow().replace(tzinfo=updated_at.tzinfo) - updated_at < timedelta(hours=max_age_hours):
                    logger.info(f"Found fresh cached stats for {username}")
                    return self._format_stats_response(stats)
                else:
                    logger.info(f"Cached stats for {username} are stale")
            
            return None
        except Exception as e:
            logger.error(f"Error getting cached stats: {e}")
            return None
    
    def save_stats(self, username: str, stats_data: Dict[str, Any], fetched_from: str = "scraper"):
        """Save stats to Supabase"""
        if not self.client:
            return
        
        try:
            # Get player UUID
            uuid = self.get_player_uuid(username)
            if not uuid:
                logger.warning(f"Could not get UUID for {username}, skipping cache save")
                return
            
            # Ensure player exists
            self.ensure_player_exists(uuid, username)
            
            # Prepare stats record
            stats_record = {
                'player_uuid': uuid,
                'player_name': username,
                'fetched_from': fetched_from,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Extract basic stats
            if fetched_from == "api":
                # Parse API response - get the actual stats from the response structure
                # The API response has stats directly in stats_data for overall stats
                stats_record.update({
                    'level': stats_data.get('level', 0),
                    'exp': stats_data.get('exp', 0),
                    'wins': stats_data.get('overall_wins', 0),
                    'losses': stats_data.get('overall_losses', 0),
                    'wlr': float(stats_data.get('overall_wlr', 0)),
                    'finals': stats_data.get('overall_final_kills', 0),
                    'final_deaths': stats_data.get('overall_final_deaths', 0),
                    'fkdr': float(stats_data.get('overall_fkdr', 0)),
                    'beds_broken': stats_data.get('overall_beds_broken', 0),
                    'beds_lost': stats_data.get('overall_beds_lost', 0),
                    'bblr': float(stats_data.get('overall_bblr', 0)),
                    'kills': stats_data.get('overall_kills', 0),
                    'deaths': stats_data.get('overall_deaths', 0),
                    'kdr': float(stats_data.get('overall_kdr', 0)),
                    'winrate': float(stats_data.get('overall_win_rate', 0)),
                    'finals_per_star': float(stats_data.get('overall_finals_per_star', 0)),
                    'detailed_stats': json.dumps(stats_data)
                })
            else:
                # Parse scraper response - data comes in modes.overall structure
                modes = stats_data.get('modes', {})
                overall = modes.get('overall', {})
                star_level = stats_data.get('star', 0)
                
                # Calculate additional metrics
                wins = self._safe_int(overall.get('wins', 0))
                losses = self._safe_int(overall.get('losses', 0))
                games_played = wins + losses
                winrate = round((wins / games_played * 100), 2) if games_played > 0 else 0
                
                finals = self._safe_int(overall.get('final_kills', 0))
                finals_per_star = round(finals / star_level, 2) if star_level > 0 else 0
                
                stats_record.update({
                    'level': star_level,
                    'exp': 0,  # Not available from scraper
                    'wins': wins,
                    'losses': losses,
                    'wlr': self._safe_float(overall.get('wlr', 0)),
                    'finals': finals,
                    'final_deaths': self._safe_int(overall.get('final_deaths', 0)),
                    'fkdr': self._safe_float(overall.get('fkdr', 0)),
                    'beds_broken': self._safe_int(overall.get('beds_broken', 0)),
                    'beds_lost': self._safe_int(overall.get('beds_lost', 0)),
                    'bblr': self._safe_float(overall.get('bblr', 0)),
                    'kills': self._safe_int(overall.get('kills', 0)),
                    'deaths': self._safe_int(overall.get('deaths', 0)),
                    'kdr': self._safe_float(overall.get('kdr', 0)),
                    'winrate': winrate,
                    'finals_per_star': finals_per_star,
                    'detailed_stats': json.dumps(stats_data)
                })
            
            # Insert stats
            self.client.table('stats').insert(stats_record).execute()
            logger.info(f"Saved stats for {username} to Supabase")
            
        except Exception as e:
            logger.error(f"Error saving stats to Supabase: {e}")
    
    def save_ping_data(self, uuid: str, ping_data: Dict[str, Any]):
        """Save ping data to Supabase"""
        if not self.client:
            return
        
        try:
            ping_record = {
                'player_uuid': uuid,
                'last_ping_string': ping_data.get('last_ping_string'),
                'last_ping_minutes': ping_data.get('last_ping_minutes'),
                'unix_timestamp': ping_data.get('unix_timestamp'),
                'average_ping': ping_data.get('average_ping')
            }
            
            self.client.table('pings').insert(ping_record).execute()
            logger.info(f"Saved ping data for UUID {uuid}")
        except Exception as e:
            logger.error(f"Error saving ping data: {e}")
    
    def save_client_tag(self, uuid: str, tag_data: Dict[str, Any]):
        """Save client tag data to Supabase"""
        if not self.client:
            return
        
        try:
            tag_record = {
                'player_uuid': uuid,
                'client_tag_name': tag_data.get('client_tag_name'),
                'client_tag_color': tag_data.get('client_tag_color'),
                'last_ping_string': tag_data.get('last_ping_string'),
                'last_ping_minutes': tag_data.get('last_ping_minutes')
            }
            
            self.client.table('client_tags').insert(tag_record).execute()
            logger.info(f"Saved client tag for UUID {uuid}")
        except Exception as e:
            logger.error(f"Error saving client tag: {e}")
    
    def _calculate_ratio(self, numerator: int, denominator: int) -> float:
        """Calculate ratio safely"""
        if denominator == 0:
            return float(numerator)
        return round(numerator / denominator, 2)
    
    def _safe_int(self, value) -> int:
        """Safely convert value to int"""
        if value is None:
            return 0
        try:
            # Handle string numbers that might have commas
            if isinstance(value, str):
                value = value.replace(',', '')
            return int(float(value))
        except (ValueError, TypeError):
            return 0
    
    def _safe_float(self, value) -> float:
        """Safely convert value to float"""
        if value is None:
            return 0.0
        try:
            if isinstance(value, str):
                value = value.replace(',', '')
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _format_stats_response(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Format stats from database to match app response format"""
        detailed = json.loads(stats.get('detailed_stats', '{}'))
        
        # Reconstruct the response to match the scraper format
        response = {
            'username': stats['player_name'],
            'star': stats.get('level', 0),
            'modes': {
                'overall': {
                    'wins': stats.get('wins', 0),
                    'losses': stats.get('losses', 0),
                    'wlr': float(stats.get('wlr', 0)),
                    'final_kills': stats.get('finals', 0),
                    'final_deaths': stats.get('final_deaths', 0),
                    'fkdr': float(stats.get('fkdr', 0)),
                    'beds_broken': stats.get('beds_broken', 0),
                    'beds_lost': stats.get('beds_lost', 0),
                    'bblr': float(stats.get('bblr', 0)),
                    'kills': stats.get('kills', 0),
                    'deaths': stats.get('deaths', 0),
                    'kdr': float(stats.get('kdr', 0)),
                    'games_played': stats.get('wins', 0) + stats.get('losses', 0)
                }
            },
            'cached': True,
            'cache_time': stats['updated_at'],
            'fetched_by': stats['fetched_from'],
            'last_updated': stats['updated_at']
        }
        
        # Merge other modes from detailed stats if available
        if 'modes' in detailed:
            for mode_key, mode_data in detailed['modes'].items():
                if mode_key != 'overall':
                    response['modes'][mode_key] = mode_data
        
        return response

# Create singleton instance
supabase_handler = SupabaseHandler()