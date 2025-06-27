#!/usr/bin/env python3
"""
PourPlan Automated Tweet Generator

This script generates and posts tweets for PourPlan pages using AI.
It can be run in test mode to preview tweets without posting.
"""

import argparse
import logging
import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import openai
import pytz
import tweepy
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import requests
import xml.etree.ElementTree as ET
import pymysql
import time

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

# === Project-specific config values ===
TWEET_COOLDOWN_DAYS = 30
TWEET_WINDOW_START = '09:00'
TWEET_WINDOW_END = '17:00'
TIMEZONE = 'America/Los_Angeles'

# Load .env before reading DB params
load_dotenv()
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'pourplan')
SITEMAP_URL = os.getenv('SITEMAP_URL', 'http://127.0.0.1:8000/sitemap.xml')

def get_recently_tweeted_urls(cooldown_days):
    """Fetch URLs tweeted in the last cooldown_days from tweet_log."""
    cutoff = datetime.now() - timedelta(days=cooldown_days)
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT page_url FROM tweet_log
                WHERE tweet_datetime >= %s
                """,
                (cutoff,)
            )
            rows = cursor.fetchall()
    return set(row['page_url'] for row in rows)

class TweetGenerator:
    def __init__(self, test_mode: bool = False):
        """Initialize the tweet generator.
        
        Args:
            test_mode: If True, only generate and display tweets without posting
        """
        self.test_mode = test_mode
        self.load_config()
        self.setup_clients()
        # Use project config values
        self.cooldown_days = TWEET_COOLDOWN_DAYS
        self.window_start = TWEET_WINDOW_START
        self.window_end = TWEET_WINDOW_END
        self.timezone = pytz.timezone(TIMEZONE)
        
    def load_config(self):
        """Load configuration from environment variables."""
        load_dotenv()
        
        # Twitter API credentials
        self.twitter_api_key = os.getenv('TWITTER_API_KEY')
        self.twitter_api_secret = os.getenv('TWITTER_API_SECRET')
        self.twitter_access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.twitter_access_secret = os.getenv('TWITTER_ACCESS_SECRET')
        
        # OpenAI API key
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Validate required configuration
        if not self.test_mode:
            required_vars = [
                'TWITTER_API_KEY', 'TWITTER_API_SECRET',
                'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_SECRET',
                'OPENAI_API_KEY'
            ]
            missing = [var for var in required_vars if not os.getenv(var)]
            if missing:
                raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    def setup_clients(self):
        """Set up API clients."""
        # OpenAI client (always set, even in test mode for dry run)
        from openai import OpenAI
        self.openai_client = OpenAI()
        logger.info(f"OpenAI client initialized: {self.openai_client}")
        if not self.test_mode:
            # Twitter client
            auth = tweepy.OAuthHandler(self.twitter_api_key, self.twitter_api_secret)
            auth.set_access_token(self.twitter_access_token, self.twitter_access_secret)
            self.twitter_client = tweepy.API(auth)
    
    def get_random_page(self) -> Optional[Tuple[str, str, dict]]:
        """Get a random eligible page from the sitemap (priority > 0.5, not tweeted recently).
        Returns (url, page_type, extra_info_dict) or None if none found.
        """
        # Fetch and parse sitemap
        try:
            resp = requests.get(SITEMAP_URL)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            logger.error(f"Failed to fetch or parse sitemap: {e}")
            return None

        # Get recently tweeted URLs
        recently_tweeted = get_recently_tweeted_urls(self.cooldown_days)

        # Parse sitemap entries
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        candidates = []
        for url_elem in root.findall('sm:url', ns):
            loc = url_elem.find('sm:loc', ns)
            priority = url_elem.find('sm:priority', ns)
            if loc is None or priority is None:
                continue
            url = loc.text.strip()
            try:
                prio = float(priority.text.strip())
            except Exception:
                continue
            if prio <= 0.5:
                continue
            if url in recently_tweeted:
                continue
            # Determine page type by URL pattern
            page_type = self._infer_page_type(url)
            if not page_type:
                continue
            candidates.append((url, page_type, {}))

        if not candidates:
            logger.warning("No eligible pages found in sitemap.")
            return None
        return random.choice(candidates)

    def _infer_page_type(self, url: str) -> Optional[str]:
        """Infer page type from URL pattern."""
        # Example patterns (customize as needed):
        # /region/  -> district
        # /region/neighborhood/  -> neighborhood
        # /region/neighborhood/winery/  -> place
        # /blog/slug/  -> blog
        path = urlparse(url).path
        if path.startswith('/blog/') and path.count('/') == 2:
            return 'blog'
        parts = [p for p in path.strip('/').split('/') if p]
        if len(parts) == 1:
            return 'district'
        if len(parts) == 2:
            return 'neighborhood'
        if len(parts) == 3:
            return 'place'
        return None
    
    def extract_page_content(self, url: str, page_type: str) -> dict:
        """Extracts content for the tweet based on page type and URL."""
        path = urlparse(url).path
        parts = [p.strip() for p in path.strip('/').split('/') if p]
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn:
            with conn.cursor() as cursor:
                if page_type == 'district':
                    # /region/
                    if len(parts) >= 1:
                        slug = parts[0]
                        logger.info(f"District slug: {slug}")
                        cursor.execute("SELECT name, description FROM regions WHERE slug=%s", (slug,))
                        row = cursor.fetchone()
                        if row:
                            return {
                                'title': row['name'],
                                'summary': row['description'] or '',
                                'url': url
                            }
                elif page_type == 'neighborhood':
                    # /region/neighborhood/
                    if len(parts) >= 2:
                        region_slug, neighborhood_slug = parts[:2]
                        logger.info(f"Neighborhood region_slug: {region_slug}, neighborhood_slug: {neighborhood_slug}")
                        cursor.execute("""
                            SELECT n.name, n.description
                            FROM neighborhoods n
                            JOIN regions r ON n.region_id = r.region_id
                            WHERE n.slug=%s AND r.slug=%s
                        """, (neighborhood_slug, region_slug))
                        row = cursor.fetchone()
                        if row:
                            return {
                                'title': row['name'],
                                'summary': row['description'] or '',
                                'url': url
                            }
                elif page_type == 'place':
                    # /region/neighborhood/winery/
                    if len(parts) >= 3:
                        region_slug, neighborhood_slug, winery_slug = parts[:3]
                        logger.info(f"Place region_slug: {region_slug}, neighborhood_slug: {neighborhood_slug}, winery_slug: {winery_slug}")
                        cursor.execute("""
                            SELECT w.name, w.place_description, w.known_for_short
                            FROM wineries w
                            JOIN neighborhoods n ON w.region_id = n.region_id AND w.neighborhood_id = n.neighborhood_id
                            JOIN regions r ON w.region_id = r.region_id
                            WHERE w.slug=%s AND n.slug=%s AND r.slug=%s
                        """, (winery_slug, neighborhood_slug, region_slug))
                        row = cursor.fetchone()
                        if row:
                            return {
                                'title': row['name'],
                                'summary': row['place_description'] or '',
                                'tags': row.get('known_for_short', ''),
                                'url': url
                            }
                elif page_type == 'blog':
                    # /blog/slug/
                    if len(parts) >= 2:
                        slug = parts[-1]
                        logger.info(f"Blog slug: {slug}")
                        cursor.execute("SELECT excerpt FROM blog_blogpage WHERE slug=%s", (slug,))
                        row = cursor.fetchone()
                        if row:
                            return {
                                'title': slug.replace('-', ' ').title(),
                                'summary': row['excerpt'] or '',
                                'url': url
                            }
        return {}

    def generate_tweet_text_and_visual(self, page_url: str, page_type: str, page_content: dict, available_visuals: dict) -> tuple:
        """Generate tweet text and select visual using GPT-4.1-nano.
        Returns (tweet_text, selected_visual_selector) or (None, None) if failed.
        """
        prompt = self._build_prompt(page_type, page_content, available_visuals)
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=150,
                temperature=0.8,
            )
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"LLM Response: {response_text}")
            
            # Parse response to extract tweet and visual choice
            tweet_text = ""
            selected_visual = None
            
            # If no visual options were provided, treat the entire response as the tweet
            if not available_visuals:
                return response_text, None
            
            # Look for TWEET: and VISUAL: patterns (case insensitive)
            import re
            
            tweet_match = re.search(r'TWEET:\s*(.+?)(?=VISUAL:|$)', response_text, re.IGNORECASE | re.DOTALL)
            if tweet_match:
                tweet_text = tweet_match.group(1).strip()
            
            visual_match = re.search(r'VISUAL:\s*(\d+)', response_text, re.IGNORECASE)
            if visual_match:
                choice_num = int(visual_match.group(1))
                visual_options = list(available_visuals.values())
                if 1 <= choice_num <= len(visual_options):
                    selected_visual = visual_options[choice_num - 1]
            
            # Fallback: if we couldn't parse the structured format, use the whole response as tweet
            if not tweet_text:
                tweet_text = response_text
                # Try to guess visual choice from content
                if available_visuals and ("wine" in response_text.lower() or "varietal" in response_text.lower()):
                    # Default to first visual option if tweet mentions wine content
                    selected_visual = list(available_visuals.values())[0]
            
            return tweet_text, selected_visual
            
        except Exception as e:
            logger.error(f"OpenAI gpt-4.1-nano error: {e}")
            return None, None

    def _build_prompt(self, page_type: str, content: dict, available_visuals: dict = None) -> str:
        """Builds the prompt for the LLM based on page type and content."""
        style_guide = (
            "Follow these style guidelines when writing the tweet:\n"
            "- Tone: Helpful, friendly, and approachable.\n"
            "- Audience: Wine lovers and casual wine tasters.\n"
            "- Emojis are allowed in moderation (no more than 1–2, used naturally).\n"
            "- Do not use hashtags.\n"
            "- Do not sound like clickbait.\n"
            "- Avoid repetitive or templated structures across tweets.\n"
        )
        
        # Add visual selection instructions if visuals are available
        visual_instructions = ""
        if available_visuals:
            visual_options = "\n".join([f"{i+1}. {option}" for i, option in enumerate(available_visuals.keys())])
            visual_instructions = f"""

VISUAL SELECTION (RECOMMENDED - visuals increase engagement by 40%):
The following visual elements are available on this page:
{visual_options}

Choose a visual that complements your tweet content. Wine data visualizations perform very well on social media.
Only select 0 (no visual) if none of the above would enhance your tweet.

CRITICAL: Your response must be EXACTLY in this format (no other text):

TWEET: [your tweet text here]
VISUAL: [number of your choice, or 0 for no visual]

Do NOT write anything else. Example response:
TWEET: Discover amazing wines at this hidden gem! 🍷 http://example.com
VISUAL: 1
"""
        
        base_instruction = "Write a tweet that encourages people to visit this"
        
        if page_type == 'district':
            content_section = f"Here is the page:\nTitle: {content.get('title','')}\nURL: {content.get('url','')}\nSummary: {content.get('summary','')}"
            specific_instruction = f"{base_instruction} page. Keep it under 280 characters and include the URL."
        elif page_type == 'place':
            content_section = f"Here is the page:\nWinery name: {content.get('title','')}\nURL: {content.get('url','')}\nSummary: {content.get('summary','')}\nTags: {content.get('tags','')}"
            specific_instruction = f"{base_instruction} winery and explore the page. Mention one or two appealing aspects (such as vibe, location, or seating), but do not list all tags mechanically. Keep it under 280 characters and include the URL."
        elif page_type == 'blog':
            content_section = f"Here is the article:\nTitle: {content.get('title','')}\nURL: {content.get('url','')}\nSummary: {content.get('summary','')}"
            specific_instruction = "Write a tweet that encourages people to read the article. The tweet should appeal to wine lovers and casual wine tasters. Keep it under 280 characters and include the URL."
        elif page_type == 'neighborhood':
            content_section = f"Here is the page:\nTitle: {content.get('title','')}\nURL: {content.get('url','')}\nSummary: {content.get('summary','')}"
            specific_instruction = f"{base_instruction} neighborhood. Keep it under 280 characters and include the URL."
        else:
            return style_guide
            
        return f"{style_guide}\n\n{content_section}\n\n{specific_instruction}{visual_instructions}"
    
    def scan_available_visuals(self, page_url: str) -> dict:
        """Scan page for available visual elements and return options for LLM."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(page_url, timeout=20000)
                
                available_visuals = {}
                
                # Check for wine type/varietal breakdown
                wine_sections = page.query_selector_all('h5, h2')
                for section in wine_sections:
                    if "wines at a glance" in (section.text_content() or "").lower():
                        available_visuals["Type and varietal breakdown"] = "wines-section"
                        break
                
                # Check for wine type visualization bar
                if "Type and varietal breakdown" not in available_visuals:
                    type_bars = page.query_selector_all('[style*="background-color: #7B1E3A"]')
                    if type_bars:
                        available_visuals["Type and varietal breakdown"] = "wine-type-bar"
                
                # Check for pricing overview
                pricing_elements = page.query_selector_all('.pricing-overview, .price-chart, [class*="pricing"]')
                if pricing_elements:
                    available_visuals["Price overview"] = "pricing-chart"
                
                # Check for wine varietal badges (specific wine badges, not all badges)
                varietal_badges = []
                all_badges = page.query_selector_all('.badge-burgundy-soft, .badge-chardonnay')
                for badge in all_badges[:5]:
                    text = badge.text_content()
                    if text and len(text.strip()) > 0:
                        varietal_badges.append(text.strip())
                
                if varietal_badges:
                    available_visuals[f"Wine varietals: {', '.join(varietal_badges)}"] = "wine-badges"
                
                browser.close()
                return available_visuals
        except Exception as e:
            logger.error(f"Error scanning visuals for {page_url}: {e}")
            return {}

    def capture_screenshot(self, page_url: str, selected_visual: str = None) -> Optional[Path]:
        """Capture screenshot of selected visual element."""
        if self.test_mode:
            logger.info(f"TEST MODE: Would capture screenshot for {page_url}, visual: {selected_visual}")
            return None

        if not selected_visual:
            return None

        # Prepare output directory
        output_dir = Path('tweet_images')
        output_dir.mkdir(exist_ok=True)

        # Build a filename based on the page slug and timestamp
        path = urlparse(page_url).path
        parts = [p for p in path.strip('/').split('/') if p]
        slug = '-'.join(parts)
        timestamp = int(time.time())
        filename = f"{slug}-{timestamp}.png"
        filepath = output_dir / filename

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                logger.info(f"Navigating to {page_url} for screenshot...")
                page.goto(page_url, timeout=20000)
                
                try:
                    element = None
                    
                    if selected_visual == "wines-section":
                        # Find the "Wines at a Glance" section and its parent container
                        wine_headers = page.query_selector_all('h5, h2, h3, h4')
                        for header in wine_headers:
                            header_text = (header.text_content() or "").lower()
                            if "wines at a glance" in header_text or "wine" in header_text:
                                # Try to find a meaningful parent container
                                potential_parents = [
                                    'xpath=ancestor::div[contains(@class, "col-md-6")]',
                                    'xpath=ancestor::div[contains(@class, "col-12")]',
                                    'xpath=ancestor::div[contains(@class, "mb-4")]',
                                    'xpath=ancestor::div[contains(@class, "mb-3")]'
                                ]
                                
                                for parent_xpath in potential_parents:
                                    try:
                                        parent = header.locator(parent_xpath).first
                                        if parent:
                                            # Check if this parent has substantial content
                                            parent_text = parent.text_content() or ""
                                            if len(parent_text.strip()) > 50:  # Has meaningful content
                                                element = parent
                                                break
                                    except:
                                        continue
                                if element:
                                    break
                    
                    elif selected_visual == "wine-type-bar":
                        # Find the wine type bar and its immediate container
                        type_bar = page.query_selector('[style*="background-color: #7B1E3A"]')
                        if type_bar:
                            # Get the container with the bar and summary text
                            parent = type_bar.locator('xpath=ancestor::div[contains(@class, "mb-3")]').first
                            if parent:
                                element = parent
                    
                    elif selected_visual == "wine-badges":
                        # Find a larger section that contains wine badges with context
                        # Try different container sizes, from largest to smallest
                        potential_containers = [
                            '.col-md-6',  # Half-width column
                            '.col-12',    # Full-width column  
                            '.mb-4',      # Large margin bottom
                            '.mb-3',      # Medium margin bottom
                            '.mb-2'       # Small margin bottom
                        ]
                        
                        for container_class in potential_containers:
                            containers = page.query_selector_all(container_class)
                            for container in containers:
                                wine_badges = container.query_selector_all('.badge-burgundy-soft, .badge-chardonnay, .badge')
                                # Look for containers with wine badges AND some text content
                                text_content = container.text_content() or ""
                                if (len(wine_badges) >= 2 and 
                                    len(text_content.strip()) > 20 and  # Has substantial text
                                    any(wine_word in text_content.lower() for wine_word in ['wine', 'varietal', 'grape', 'red', 'white'])):
                                    element = container
                                    break
                            if element:
                                break
                    
                    elif selected_visual == "pricing-chart":
                        # Find pricing overview elements
                        pricing_el = page.query_selector('.pricing-overview, .price-chart, [class*="pricing"]')
                        if pricing_el:
                            element = pricing_el
                    
                    if element:
                        # Get element bounding box and add padding
                        box = element.bounding_box()
                        if box:
                            padding = 40  # 40px padding on all sides for better visual spacing
                            # Calculate padded coordinates
                            x = max(0, box['x'] - padding)
                            y = max(0, box['y'] - padding)
                            width = box['width'] + (2 * padding)
                            height = box['height'] + (2 * padding)
                            
                            # Take screenshot of the padded area
                            page.screenshot(
                                path=str(filepath),
                                clip={
                                    'x': x,
                                    'y': y,
                                    'width': width,
                                    'height': height
                                }
                            )
                        else:
                            # Fallback to element screenshot if bounding box fails
                            element.screenshot(path=str(filepath))
                        
                        logger.info(f"Screenshot saved to {filepath}")
                        browser.close()
                        return filepath
                    else:
                        logger.warning(f"Could not find specific element for visual type: {selected_visual}")
                        
                except Exception as e:
                    logger.warning(f"Error capturing specific visual '{selected_visual}': {e}")
                
                browser.close()
                return None
        except Exception as e:
            logger.error(f"Playwright screenshot error for {page_url}: {e}")
            return None
    
    def post_tweet(self, tweet_text: str, image_path: Optional[Path] = None) -> Optional[str]:
        """Post tweet to Twitter.
        
        Args:
            tweet_text: Text of the tweet
            image_path: Optional path to image to attach
            
        Returns:
            Tweet ID if successful, None otherwise
        """
        if self.test_mode:
            logger.info("TEST MODE: Would post tweet:")
            logger.info(f"Text: {tweet_text}")
            if image_path:
                logger.info(f"Image: {image_path}")
            return None
            
        try:
            # TODO: Implement tweet posting logic
            pass
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return None
    
    def log_tweet(self, page_url: str, tweet_text: str, tweet_id: Optional[str],
                 image_used: bool, success: bool, error_message: Optional[str] = None):
        """Log tweet attempt to database.
        
        Args:
            page_url: URL of the page tweeted
            tweet_text: Text of the tweet
            tweet_id: Twitter ID of the tweet
            image_used: Whether an image was used
            success: Whether the tweet was successful
            error_message: Error message if unsuccessful
        """
        # TODO: Implement database logging
        pass
    
    def run(self):
        """Run the tweet generation process."""
        try:
            # Get random page
            page_info = self.get_random_page()
            if not page_info:
                logger.warning("No eligible pages found for tweeting")
                return
                
            page_url, page_type, _ = page_info
            
            # Extract content
            page_content = self.extract_page_content(page_url, page_type)
            if not page_content:
                logger.error(f"Failed to extract content for {page_url}")
                return
            
            # Scan for available visuals (only for place pages)
            available_visuals = {}
            if page_type == 'place':
                available_visuals = self.scan_available_visuals(page_url)
                logger.info(f"Found {len(available_visuals)} visual options: {list(available_visuals.keys())}")
                
            # Generate tweet text and select visual
            tweet_text, selected_visual = self.generate_tweet_text_and_visual(page_url, page_type, page_content, available_visuals)
            if not tweet_text:
                logger.error(f"Failed to generate tweet text for {page_url}")
                return
                
            if self.test_mode:
                logger.info(f"Test mode: Would tweet for {page_url} [{page_type}]")
                logger.info(f"Content: {page_content}")
                logger.info(f"Available visuals: {list(available_visuals.keys())}")
                logger.info(f"Generated tweet: {tweet_text}")
                logger.info(f"Selected visual: {selected_visual}")
                return
                
            # Capture screenshot if visual was selected
            image_path = None
            if selected_visual:
                image_path = self.capture_screenshot(page_url, selected_visual)
                
            # Post tweet
            tweet_id = self.post_tweet(tweet_text, image_path)
            
            # Log attempt
            self.log_tweet(
                page_url=page_url,
                tweet_text=tweet_text,
                tweet_id=tweet_id,
                image_used=bool(image_path),
                success=bool(tweet_id)
            )
            
        except Exception as e:
            logger.error(f"Error in tweet generation process: {e}")

def main():
    parser = argparse.ArgumentParser(description='Generate and post PourPlan tweets')
    parser.add_argument('--test', action='store_true',
                      help='Test mode: generate tweets without posting')
    args = parser.parse_args()
    
    generator = TweetGenerator(test_mode=args.test)
    generator.run()

if __name__ == '__main__':
    main() 