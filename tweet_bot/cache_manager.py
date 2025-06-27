"""
SQLite cache manager for tracking tweeted posts and preventing redundancy
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

class CacheManager:
    """Manages SQLite cache for tweet history and post tracking"""
    
    def __init__(self, db_path: str = 'cache.db'):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table for tracking posts we've tweeted about
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tweeted_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_url TEXT UNIQUE NOT NULL,
                    post_title TEXT,
                    first_tweeted_at DATETIME,
                    last_tweeted_at DATETIME,
                    tweet_count INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table for tracking actual tweets sent
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tweet_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_url TEXT NOT NULL,
                    tweet_text TEXT NOT NULL,
                    tweet_id TEXT,
                    tweeted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    style_params TEXT,  -- JSON of style choices used
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    FOREIGN KEY (post_url) REFERENCES tweeted_posts (post_url)
                )
            ''')
            
            # Index for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_post_url ON tweeted_posts (post_url)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tweeted_at ON tweet_history (tweeted_at)
            ''')
            
            conn.commit()
    
    def get_recently_tweeted_urls(self, cooldown_days: int) -> set:
        """Get URLs that were tweeted within the cooldown period"""
        cutoff_date = datetime.now() - timedelta(days=cooldown_days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT post_url FROM tweeted_posts 
                WHERE last_tweeted_at >= ?
            ''', (cutoff_date,))
            
            return {row[0] for row in cursor.fetchall()}
    
    def get_previous_tweets(self, post_url: str, limit: int = 3) -> List[Dict]:
        """Get the last N tweets for a specific post"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tweet_text, style_params, tweeted_at 
                FROM tweet_history 
                WHERE post_url = ? AND success = TRUE
                ORDER BY tweeted_at DESC 
                LIMIT ?
            ''', (post_url, limit))
            
            tweets = []
            for row in cursor.fetchall():
                style_params = json.loads(row[1]) if row[1] else {}
                tweets.append({
                    'tweet_text': row[0],
                    'style_params': style_params,
                    'tweeted_at': row[2]
                })
            
            return tweets
    
    def log_tweet(self, post_url: str, post_title: str, tweet_text: str, 
                  tweet_id: Optional[str], style_params: Dict, 
                  success: bool = True, error_message: Optional[str] = None):
        """Log a tweet attempt to the database"""
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert or update the tweeted_posts table
            cursor.execute('''
                INSERT OR REPLACE INTO tweeted_posts 
                (post_url, post_title, first_tweeted_at, last_tweeted_at, tweet_count)
                VALUES (
                    ?, ?, 
                    COALESCE((SELECT first_tweeted_at FROM tweeted_posts WHERE post_url = ?), ?),
                    ?,
                    COALESCE((SELECT tweet_count FROM tweeted_posts WHERE post_url = ?) + 1, 1)
                )
            ''', (post_url, post_title, post_url, now, now, post_url))
            
            # Insert the tweet history
            cursor.execute('''
                INSERT INTO tweet_history 
                (post_url, tweet_text, tweet_id, tweeted_at, style_params, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (post_url, tweet_text, tweet_id, now, json.dumps(style_params), success, error_message))
            
            conn.commit()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total posts tweeted
            cursor.execute('SELECT COUNT(*) FROM tweeted_posts')
            total_posts = cursor.fetchone()[0]
            
            # Total tweets sent
            cursor.execute('SELECT COUNT(*) FROM tweet_history WHERE success = TRUE')
            total_tweets = cursor.fetchone()[0]
            
            # Recent activity (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            cursor.execute('SELECT COUNT(*) FROM tweet_history WHERE tweeted_at >= ? AND success = TRUE', (week_ago,))
            recent_tweets = cursor.fetchone()[0]
            
            return {
                'total_posts_tweeted': total_posts,
                'total_tweets_sent': total_tweets,
                'tweets_last_7_days': recent_tweets
            }
    
    def cleanup_old_data(self, days_to_keep: int = 365):
        """Clean up old tweet history (keep posts table but clean history)"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tweet_history WHERE tweeted_at < ?', (cutoff_date,))
            deleted = cursor.rowcount
            conn.commit()
            
            return deleted 