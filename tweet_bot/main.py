"""
Main orchestrator for tweet-my-blog
"""

import logging
import random
import sys
from typing import Optional

from .config import Config
from .cache_manager import CacheManager
from .sitemap_parser import SitemapParser
from .tweet_generator import TweetGenerator
from .daily_scheduler import DailyScheduler
from .random_delay import apply_random_delay

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tweet_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TweetBot:
    """Main tweet bot orchestrator"""
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.config = Config()
        
        # Validate configuration
        try:
            self.config.validate_required(test_mode)
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        # Initialize components
        self.cache = CacheManager(self.config.cache_db_path)
        self.sitemap_parser = SitemapParser(self.config.sitemap_url)
        self.tweet_generator = TweetGenerator(self.config, test_mode)
        
        logger.info("TweetBot initialized successfully")
        if test_mode:
            logger.info("Running in TEST MODE - no tweets will be posted")
    
    def run(self) -> bool:
        """Run the main tweet generation workflow"""
        try:
            logger.info("Starting tweet generation workflow")
            
            # Get cache stats
            stats = self.cache.get_stats()
            logger.info(f"Cache stats: {stats}")
            
            # Get recently tweeted URLs (respecting cooldown)
            recently_tweeted = self.cache.get_recently_tweeted_urls(self.config.cooldown_days)
            logger.info(f"Found {len(recently_tweeted)} recently tweeted URLs (cooldown: {self.config.cooldown_days} days)")
            
            # Get eligible posts
            eligible_posts = self.sitemap_parser.get_eligible_posts(recently_tweeted)
            
            if not eligible_posts:
                # Check if we should exhaust content (re-tweet old posts)
                if recently_tweeted:
                    logger.info("No new posts available, checking if we should re-tweet older content")
                    # Get all posts and allow re-tweeting
                    all_posts = self.sitemap_parser.fetch_posts()
                    if all_posts:
                        eligible_posts = all_posts
                        logger.info(f"Exhausted new content, allowing re-tweets from {len(eligible_posts)} total posts")
                    else:
                        logger.error("No posts found in sitemap")
                        return False
                else:
                    logger.error("No eligible posts found")
                    return False
            
            # Select a random post
            selected_post = random.choice(eligible_posts)
            logger.info(f"Selected post: {selected_post['title']} ({selected_post['url']})")
            
            # Scrape the post content for better context
            post_content = self.tweet_generator.scrape_post_content(selected_post['url'])
            
            # Merge sitemap data with scraped content
            post_data = {
                'url': selected_post['url'],
                'title': post_content['title'] or selected_post['title'],
                'description': post_content['description'],
                'excerpt': post_content['excerpt'],
                'featured_image': selected_post.get('featured_image'),
                'lastmod': selected_post.get('lastmod')
            }
            
            # Get previous tweets for this post to avoid redundancy
            previous_tweets = self.cache.get_previous_tweets(
                selected_post['url'], 
                self.config.max_previous_tweets
            )
            
            if previous_tweets:
                logger.info(f"Found {len(previous_tweets)} previous tweets for this post")
            
            # Generate random style parameters
            style_params = self.config.get_random_style()
            logger.info(f"Using style parameters: {style_params}")
            
            # Generate the tweet
            tweet_text = self.tweet_generator.generate_tweet_text(
                post_data, style_params, previous_tweets
            )
            
            if not tweet_text:
                logger.error("Failed to generate tweet text")
                return False
            
            logger.info(f"Generated tweet ({len(tweet_text)} chars): {tweet_text}")
            
            # Post the tweet
            tweet_id = self.tweet_generator.post_tweet(
                tweet_text, 
                post_data.get('featured_image')
            )
            
            success = tweet_id is not None
            
            # Log the result
            self.cache.log_tweet(
                post_url=post_data['url'],
                post_title=post_data['title'],
                tweet_text=tweet_text,
                tweet_id=tweet_id,
                style_params=style_params,
                success=success,
                error_message=None if success else "Failed to post tweet"
            )
            
            if success:
                logger.info(f"✅ Successfully tweeted! Tweet ID: {tweet_id}")
                if not self.test_mode:
                    print(f"🐦 Tweet posted: https://twitter.com/user/status/{tweet_id}")
                print(f"📄 Post: {post_data['url']}")
                print(f"📝 Tweet: {tweet_text}")
            else:
                logger.error("❌ Failed to post tweet")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in tweet generation workflow: {e}", exc_info=True)
            return False
    
    def get_stats(self) -> dict:
        """Get bot statistics"""
        return self.cache.get_stats()
    
    def cleanup_old_data(self, days_to_keep: int = 365) -> int:
        """Clean up old tweet history"""
        return self.cache.cleanup_old_data(days_to_keep)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tweet My Blog - Automated blog post promotion')
    parser.add_argument('--test', action='store_true', help='Run in test mode (no actual tweets)')
    parser.add_argument('--stats', action='store_true', help='Show statistics and exit')
    parser.add_argument('--cleanup', type=int, metavar='DAYS', help='Clean up tweet history older than DAYS')
    parser.add_argument('--force', action='store_true', help='Force execution regardless of schedule')
    
    args = parser.parse_args()
    
    # Quick schedule check for automated runs (skip for manual operations)
    if not any([args.stats, args.cleanup, args.force]):
        scheduler = DailyScheduler()
        if not scheduler.should_run_today():
            schedule = scheduler.get_todays_schedule()
            if schedule:
                print(f"⏰ Not scheduled to run now. Today's slot: {schedule['hour']:02d}:{schedule['minute']:02d} UTC")
            else:
                print("⏰ No schedule found for today")
            sys.exit(0)
        
        print("🎯 This is the scheduled execution time for today!")
        # Apply random delay if enabled (but not in test mode for faster testing)
        if not args.test:
            apply_random_delay()
        else:
            print("⏰ Test mode: skipping random delay")
    
    bot = TweetBot(test_mode=args.test)
    
    if args.stats:
        stats = bot.get_stats()
        print("📊 Tweet Bot Statistics:")
        print(f"   Total posts tweeted: {stats['total_posts_tweeted']}")
        print(f"   Total tweets sent: {stats['total_tweets_sent']}")
        print(f"   Tweets last 7 days: {stats['tweets_last_7_days']}")
        return
    
    if args.cleanup:
        deleted = bot.cleanup_old_data(args.cleanup)
        print(f"🧹 Cleaned up {deleted} old tweet records (older than {args.cleanup} days)")
        return
    
    # Run the main workflow
    success = bot.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 