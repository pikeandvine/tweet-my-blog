import os
import random
import logging
from datetime import datetime, timedelta
import django
from django.db.models import Q
from django.conf import settings
from openai import OpenAI
import tweepy
from dotenv import load_dotenv
import json
from playwright.sync_api import sync_playwright
import time

# Set up logging
logging.basicConfig(
    filename='tweet_generator.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pourplan.settings')
django.setup()

# Initialize OpenAI client
client = OpenAI()
logging.info(f"OpenAI client initialized: {client}")

# Initialize Twitter client
twitter_client = tweepy.Client(
    consumer_key=os.getenv('TWITTER_API_KEY'),
    consumer_secret=os.getenv('TWITTER_API_SECRET'),
    access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
    access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
)

# Import models after Django setup
from wineries.models import Winery
from blog.models import BlogPage
from districts.models import District

def get_random_page():
    """Select a random page that hasn't been tweeted recently."""
    # Get pages that haven't been tweeted in the last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Query for pages that haven't been tweeted recently
    wineries = Winery.objects.filter(
        Q(last_tweeted__isnull=True) | Q(last_tweeted__lt=thirty_days_ago)
    )
    blog_pages = BlogPage.objects.filter(
        Q(last_tweeted__isnull=True) | Q(last_tweeted__lt=thirty_days_ago)
    )
    districts = District.objects.filter(
        Q(last_tweeted__isnull=True) | Q(last_tweeted__lt=thirty_days_ago)
    )
    
    # Combine all eligible pages
    eligible_pages = list(wineries) + list(blog_pages) + list(districts)
    
    if not eligible_pages:
        logging.warning("No eligible pages found for tweeting")
        return None
    
    return random.choice(eligible_pages)

def capture_page_image(page):
    """Capture a relevant image from the page."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page_obj = browser.new_page()
            
            # Construct the URL based on page type
            if isinstance(page, Winery):
                # Get the full URL path from the page object
                url = f"https://pourplan.com/{page.region_slug}/{page.neighborhood_slug}/{page.slug}/"
                logging.info(f"Place region_slug: {page.region_slug}, neighborhood_slug: {page.neighborhood_slug}, winery_slug: {page.slug}")
            elif isinstance(page, BlogPage):
                url = f"https://pourplan.com/blog/{page.slug}/"
            else:  # District
                url = f"https://pourplan.com/district/{page.slug}/"
            
            logging.info(f"Navigating to {url} for screenshot...")
            page_obj.goto(url)
            page_obj.wait_for_load_state('networkidle')
            
            # Try different selectors for visual elements
            selectors = [
                '.place-visual',           # Main visual component
                '.varietal-tags',          # Varietal tag cloud
                '.featured-tags',          # Featured tags section
                '.page-header',            # Page header with title
                '.main-content',           # Main content area
                '.place-details',          # Place details section
                '.place-description',      # Place description
                '.place-features',         # Place features
                '.place-tags',             # Place tags
                '.place-info',             # Place info section
                '.place-gallery',          # Place gallery
                '.place-map',              # Place map
                '.place-reviews'           # Place reviews
            ]
            
            for selector in selectors:
                try:
                    element = page_obj.query_selector(selector)
                    if element:
                        # Check if element is visible
                        is_visible = element.is_visible()
                        if not is_visible:
                            logging.info(f"Element {selector} found but not visible")
                            continue
                            
                        # Get element dimensions
                        box = element.bounding_box()
                        if box:
                            # Add some padding
                            padding = 20
                            screenshot = page_obj.screenshot(
                                clip={
                                    'x': box['x'] - padding,
                                    'y': box['y'] - padding,
                                    'width': box['width'] + (padding * 2),
                                    'height': box['height'] + (padding * 2)
                                }
                            )
                            
                            # Save the screenshot
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            filename = f"tweet_images/{page.slug}_{timestamp}.png"
                            os.makedirs('tweet_images', exist_ok=True)
                            
                            with open(filename, 'wb') as f:
                                f.write(screenshot)
                            
                            logging.info(f"Captured screenshot of {selector}: {filename}")
                            browser.close()
                            return filename
                except Exception as e:
                    logging.error(f"Error processing selector {selector}: {str(e)}")
                    continue
            
            # If no specific elements found, try to capture the main content area
            try:
                main_content = page_obj.query_selector('main')
                if main_content:
                    box = main_content.bounding_box()
                    if box:
                        screenshot = page_obj.screenshot(
                            clip={
                                'x': box['x'],
                                'y': box['y'],
                                'width': min(box['width'], 1200),  # Limit width for better presentation
                                'height': min(box['height'], 800)   # Limit height for better presentation
                            }
                        )
                        
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"tweet_images/{page.slug}_{timestamp}_main.png"
                        os.makedirs('tweet_images', exist_ok=True)
                        
                        with open(filename, 'wb') as f:
                            f.write(screenshot)
                        
                        logging.info(f"Captured main content screenshot: {filename}")
                        browser.close()
                        return filename
            except Exception as e:
                logging.error(f"Error capturing main content: {str(e)}")
            
            logging.warning(f"No suitable visual elements found on {url}")
            browser.close()
            return None
            
    except Exception as e:
        logging.error(f"Error capturing page image: {str(e)}")
        return None

def generate_tweet_content(page):
    """Generate tweet content using OpenAI."""
    # Prepare the prompt based on page type
    if isinstance(page, Winery):
        prompt = f"""Follow these style guidelines when writing the tweet:
- Tone: Helpful, friendly, and approachable.
- Audience: Wine lovers and casual wine tasters.
- Emojis are allowed in moderation (no more than 1–2, used naturally).
- Do not use hashtags.
- Do not sound like clickbait.
- Avoid repetitive or templated structures across tweets.

You are writing a short, engaging tweet to promote a winery page.

Here is the page:
Winery name: {page.name}
URL: https://pourplan.com/winery/{page.slug}/
Summary: {page.description}
Tags: {', '.join(page.tags.names())}

Write a tweet that encourages people to visit this winery and explore the page. Mention one or two appealing aspects (such as vibe, location, or seating), but do not list all tags mechanically. Keep it under 280 characters and include the URL."""
    
    elif isinstance(page, BlogPage):
        prompt = f"""Follow these style guidelines when writing the tweet:
- Tone: Helpful, friendly, and approachable.
- Audience: Wine lovers and casual wine tasters.
- Emojis are allowed in moderation (no more than 1–2, used naturally).
- Do not use hashtags.
- Do not sound like clickbait.
- Avoid repetitive or templated structures across tweets.

You are writing a short, engaging tweet to promote a blog article about wine tasting.

Here is the article:
Title: {page.title}
URL: https://pourplan.com/blog/{page.slug}/
Summary: {page.search_description or page.body}

Write a tweet that encourages people to read the article. The tweet should appeal to wine lovers and casual wine tasters. Keep it under 280 characters and include the URL."""
    
    else:  # District
        prompt = f"""Follow these style guidelines when writing the tweet:
- Tone: Helpful, friendly, and approachable.
- Audience: Wine lovers and casual wine tasters.
- Emojis are allowed in moderation (no more than 1–2, used naturally).
- Do not use hashtags.
- Do not sound like clickbait.
- Avoid repetitive or templated structures across tweets.

You are writing a short, engaging tweet to promote a wine tasting guide page.

Here is the page:
Title: {page.name}
URL: https://pourplan.com/district/{page.slug}/
Summary: {page.description}

Write a tweet that encourages people to visit this page. Keep it under 280 characters and include the URL."""

    try:
        # Log the prompt for debugging
        logging.info("Preparing to send prompt to OpenAI...")
        logging.info(f"Page type: {type(page).__name__}")
        logging.info(f"Page name: {page.name}")
        logging.info(f"Prompt content: {json.dumps(prompt)}")
        
        # Try with gpt-4o first
        try:
            logging.info("Attempting to use gpt-4o...")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates engaging tweets for a wine tasting website."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            logging.info("Successfully got response from gpt-4o")
        except Exception as e:
            logging.error(f"Error with gpt-4o: {str(e)}")
            # Fallback to gpt-4.1-mini
            logging.info("Falling back to gpt-4.1-mini...")
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates engaging tweets for a wine tasting website."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            logging.info("Successfully got response from gpt-4.1-mini")
        
        # Log the response for debugging
        tweet_content = response.choices[0].message.content.strip()
        logging.info(f"Generated tweet content: {json.dumps(tweet_content)}")
        
        return tweet_content
    except Exception as e:
        logging.error(f"Error generating tweet content: {str(e)}")
        logging.error(f"Error type: {type(e).__name__}")
        logging.error(f"Error details: {str(e)}")
        return None

def post_tweet(tweet_content, image_path=None):
    """Post the tweet using Twitter API."""
    try:
        if image_path:
            # Upload media
            media = twitter_client.media_upload(image_path)
            # Post tweet with media
            response = twitter_client.create_tweet(
                text=tweet_content,
                media_ids=[media.media_id]
            )
        else:
            # Post tweet without media
            response = twitter_client.create_tweet(text=tweet_content)
        
        return response.data['id']
    except Exception as e:
        logging.error(f"Error posting tweet: {str(e)}")
        return None

def update_page_tweet_status(page, tweet_id):
    """Update the page's last_tweeted timestamp and tweet_id."""
    try:
        page.last_tweeted = datetime.now()
        page.last_tweet_id = tweet_id
        page.save()
    except Exception as e:
        logging.error(f"Error updating page tweet status: {str(e)}")

def main():
    """Main function to generate and post a tweet."""
    try:
        # Get a random page
        page = get_random_page()
        if not page:
            logging.warning("No eligible pages found for tweeting")
            return

        # Generate tweet content
        tweet_content = generate_tweet_content(page)
        if not tweet_content:
            logging.error("Failed to generate tweet content")
            return

        # Capture page image
        image_path = capture_page_image(page)
        
        # Post the tweet
        tweet_id = post_tweet(tweet_content, image_path)
        if not tweet_id:
            logging.error("Failed to post tweet")
            return

        # Update page status
        update_page_tweet_status(page, tweet_id)
        
        logging.info(f"Successfully posted tweet {tweet_id} for page {page}")
        
    except Exception as e:
        logging.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    main() 