import json
import os


class MatchCache:
    """File-based cache for match data to avoid repeated API calls."""
    
    def __init__(self, cache_dir=".cache"):
        """
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, event_key):
        """Get the file path for a specific event's matches."""
        return os.path.join(self.cache_dir, f"{event_key}_matches.json")
    
    def exists(self, event_key):
        """Return True if a cache file exists for the event."""
        return os.path.exists(self._get_cache_path(event_key))
    
    def get(self, event_key):
        """Get cached match data, or None if not cached."""
        cache_path = self._get_cache_path(event_key)
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return None
    
    def save(self, event_key, matches):
        """Save match data to cache."""
        cache_path = self._get_cache_path(event_key)
        try:
            with open(cache_path, "w") as f:
                json.dump(matches, f)
        except IOError as e:
            print(f"Warning: Could not save cache for {event_key}: {e}")