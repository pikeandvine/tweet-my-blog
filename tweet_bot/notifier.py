"""
Notification system for tweet-my-blog
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class Notifier:
    """Handles notifications via ntfy.sh"""
    
    def __init__(self, ntfy_topic: Optional[str] = None):
        self.ntfy_topic = ntfy_topic
        
    def send_tweet_notification(self, tweet_text: str, post_url: str, tweet_id: Optional[str] = None) -> bool:
        """Send a notification when a tweet is posted"""
        if not self.ntfy_topic:
            logger.debug("No ntfy.sh topic configured, skipping notification")
            return True  # Return True since this is expected behavior
            
        try:
            # Construct the notification message
            title = "Tweet Posted!"
            
            message_parts = [
                f"🐦 Tweet Posted!",
                "",
                f"📝 {tweet_text}",
                "",
                f"📄 Post: {post_url}"
            ]
            
            if tweet_id:
                message_parts.append(f"🔗 Tweet: https://twitter.com/user/status/{tweet_id}")
            
            message = "\n".join(message_parts)
            
            # Send notification to ntfy.sh
            response = requests.post(
                f"https://ntfy.sh/{self.ntfy_topic}",
                headers={
                    "Title": title,
                    "Tags": "bird,blog,automation"
                },
                data=message.encode('utf-8'),
                timeout=10
            )
            
            response.raise_for_status()
            logger.info(f"✅ Notification sent to ntfy.sh topic: {self.ntfy_topic}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send ntfy.sh notification: {e}")
            return False
    
    def send_error_notification(self, error_message: str, post_url: Optional[str] = None) -> bool:
        """Send a notification when tweet generation fails"""
        if not self.ntfy_topic:
            logger.debug("No ntfy.sh topic configured, skipping error notification")
            return True
            
        try:
            title = "Tweet Generation Failed"
            
            message_parts = [
                f"⚠️ Tweet Generation Failed",
                "",
                f"❌ {error_message}"
            ]
            
            if post_url:
                message_parts.append(f"📄 Post: {post_url}")
            
            message = "\n".join(message_parts)
            
            # Send notification to ntfy.sh
            response = requests.post(
                f"https://ntfy.sh/{self.ntfy_topic}",
                headers={
                    "Title": title,
                    "Tags": "warning,blog,automation",
                    "Priority": "high"
                },
                data=message.encode('utf-8'),
                timeout=10
            )
            
            response.raise_for_status()
            logger.info(f"✅ Error notification sent to ntfy.sh topic: {self.ntfy_topic}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send ntfy.sh error notification: {e}")
            return False 