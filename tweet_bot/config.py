"""
Configuration management for tweet-my-blog
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

class Config:
    """Configuration class with environment variable handling"""
    
    def __init__(self):
        # Required API keys
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.twitter_api_key = os.getenv('TWITTER_API_KEY')
        self.twitter_api_secret = os.getenv('TWITTER_API_SECRET')
        self.twitter_access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.twitter_access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        # Blog configuration
        self.sitemap_url = os.getenv('SITEMAP_URL', 'https://pikeandvine.com/post-sitemap.xml')
        self.blog_title = os.getenv('BLOG_TITLE', 'Pike & Vine')
        self.blog_description = os.getenv('BLOG_DESCRIPTION', 'SaaS Marketing & Growth')
        
        # Tweet configuration
        self.cooldown_days = int(os.getenv('COOLDOWN_DAYS', '30'))
        self.tweet_frequency = os.getenv('TWEET_FREQUENCY', 'daily')  # daily, hourly, etc.
        self.max_previous_tweets = int(os.getenv('MAX_PREVIOUS_TWEETS', '3'))
        
        # Database
        self.cache_db_path = os.getenv('CACHE_DB_PATH', 'cache.db')
        
        # Notifications
        self.ntfy_topic = os.getenv('NTFY_TOPIC')  # Optional - no notification if not set
        
        # AI Model configuration
        # Options: gpt-4.1-mini (recommended), gpt-4.1-nano (ultra-cheap), gpt-4o-mini (older)
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
        
        # Style variations
        self.style_variations = {
            'emoji_style': ['none', 'minimal_1', 'moderate_2-3', 'enthusiastic_3+'],
            'tone': ['professional', 'casual', 'enthusiastic', 'conversational'],
            'cta_style': ['direct', 'question', 'intrigue', 'benefit-focused'],
            'length_target': ['concise_180', 'medium_220', 'full_280'],
            'include_hashtags': [True, False]
        }
        
    def validate_required(self, test_mode: bool = False) -> None:
        """Validate that required configuration is present"""
        required_vars = ['OPENAI_API_KEY']
        
        if not test_mode:
            required_vars.extend([
                'TWITTER_API_KEY',
                'TWITTER_API_SECRET', 
                'TWITTER_ACCESS_TOKEN',
                'TWITTER_ACCESS_TOKEN_SECRET'
            ])
        
        missing = []
        for var in required_vars:
            if not getattr(self, var.lower()):
                missing.append(var)
                
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
            
    def get_random_style(self) -> Dict[str, Any]:
        """Get a random combination of style parameters"""
        import random
        
        return {
            param: random.choice(options) 
            for param, options in self.style_variations.items()
        } 