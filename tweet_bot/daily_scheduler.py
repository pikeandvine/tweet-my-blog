"""
Daily scheduler for human-like tweet timing
"""

import json
import os
import random
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class DailyScheduler:
    """Manages daily tweet scheduling with human-like timing"""
    
    def __init__(self, schedule_file: str = "daily_schedule.json"):
        self.schedule_file = schedule_file
    
    def should_run_today(self) -> bool:
        """
        Check if this execution should proceed with tweeting today.
        Returns True if it's this run's turn, False if another time slot was chosen.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_hour = datetime.now(timezone.utc).hour
        
        # Load or create today's schedule
        schedule = self._get_or_create_schedule(today)
        
        # Check if current hour matches the scheduled hour
        scheduled_hour = schedule.get("hour")
        
        if scheduled_hour is None:
            return False
            
        # Simple hour-based matching - much more reliable for GitHub Actions
        return current_hour == scheduled_hour
    
    def _get_or_create_schedule(self, today: str) -> Dict[str, Any]:
        """Get existing schedule or create a new one for today"""
        
        # Try to load existing schedule
        if os.path.exists(self.schedule_file):
            try:
                with open(self.schedule_file, 'r') as f:
                    data = json.load(f)
                    
                # If schedule exists for today, return it
                if data.get("date") == today:
                    return data
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Create new schedule for today
        schedule = self._create_todays_schedule(today)
        self._save_schedule(schedule)
        return schedule
    
    def _create_todays_schedule(self, today: str) -> Dict[str, Any]:
        """Create a random schedule for today from available time slots"""
        
        # Available time slots (hour, minute) - matching the cron schedule
        # These correspond to 6am-4pm PDT (13-23 UTC)
        time_slots = [
            (13, 12),  # 6:12am PDT
            (14, 23),  # 7:23am PDT  
            (15, 8),   # 8:08am PDT
            (16, 37),  # 9:37am PDT
            (17, 19),  # 10:19am PDT
            (18, 26),  # 11:26am PDT
            (19, 43),  # 12:43pm PDT
            (20, 17),  # 1:17pm PDT
            (21, 33),  # 2:33pm PDT
            (22, 11),  # 3:11pm PDT
            (23, 29),  # 4:29pm PDT
        ]
        
        # Pick a random time slot for today
        chosen_hour, chosen_minute = random.choice(time_slots)
        
        return {
            "date": today,
            "hour": chosen_hour,
            "minute": chosen_minute,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _save_schedule(self, schedule: Dict[str, Any]) -> None:
        """Save schedule to file"""
        try:
            with open(self.schedule_file, 'w') as f:
                json.dump(schedule, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save schedule file: {e}")
    
    def get_todays_schedule(self) -> Optional[Dict[str, Any]]:
        """Get today's schedule if it exists"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._get_or_create_schedule(today) 