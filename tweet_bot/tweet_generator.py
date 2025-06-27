"""
Tweet generation and posting using OpenAI and Twitter API
"""

import logging
import random
import requests
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
import tweepy
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class TweetGenerator:
    """Generates and posts tweets using OpenAI and Twitter API"""
    
    def __init__(self, config, test_mode: bool = False):
        self.config = config
        self.test_mode = test_mode
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=config.openai_api_key)
        
        # Initialize Twitter client (only if not in test mode)
        if not test_mode:
            auth = tweepy.OAuthHandler(
                config.twitter_api_key,
                config.twitter_api_secret
            )
            auth.set_access_token(
                config.twitter_access_token,
                config.twitter_access_token_secret
            )
            self.twitter_api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Also initialize the v2 client for posting
            self.twitter_client = tweepy.Client(
                consumer_key=config.twitter_api_key,
                consumer_secret=config.twitter_api_secret,
                access_token=config.twitter_access_token,
                access_token_secret=config.twitter_access_token_secret,
                wait_on_rate_limit=True
            )
    
    def scrape_post_content(self, url: str) -> Dict[str, str]:
        """Scrape the actual post content for better tweet generation"""
        try:
            logger.info(f"Scraping content from {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = None
            title_selectors = ['h1.entry-title', 'h1.post-title', 'h1', 'title']
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text().strip()
                    break
            
            # Extract meta description
            description = None
            desc_elem = soup.find('meta', {'name': 'description'})
            if desc_elem:
                description = desc_elem.get('content', '').strip()
            
            # Extract first paragraph or excerpt
            excerpt = None
            excerpt_selectors = [
                '.entry-excerpt', '.post-excerpt', '.excerpt',
                '.entry-content p', '.post-content p', '.content p'
            ]
            for selector in excerpt_selectors:
                excerpt_elem = soup.select_one(selector)
                if excerpt_elem:
                    excerpt = excerpt_elem.get_text().strip()
                    # Clean up and limit length
                    excerpt = re.sub(r'\s+', ' ', excerpt)
                    if len(excerpt) > 300:
                        excerpt = excerpt[:300] + '...'
                    break
            
            return {
                'title': title or 'Blog Post',
                'description': description or '',
                'excerpt': excerpt or ''
            }
            
        except Exception as e:
            logger.error(f"Failed to scrape content from {url}: {e}")
            return {
                'title': 'Blog Post',
                'description': '',
                'excerpt': ''
            }
    
    def generate_tweet_text(self, post_data: Dict, style_params: Dict, 
                           previous_tweets: List[Dict]) -> str:
        """Generate tweet text using OpenAI"""
        
        # Build the prompt
        prompt = self._build_prompt(post_data, style_params, previous_tweets)
        
        try:
            logger.info("Generating tweet with OpenAI")
            logger.debug(f"Prompt: {prompt}")
            
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are a social media expert who writes engaging tweets to promote blog posts. You write in a natural, human voice that doesn't sound like AI-generated content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.8,  # Add some creativity
                presence_penalty=0.6,  # Encourage variety
                frequency_penalty=0.6  # Reduce repetition
            )
            
            tweet_text = response.choices[0].message.content.strip()
            
            # Clean up the tweet text
            tweet_text = self._clean_tweet_text(tweet_text, post_data['url'])
            
            logger.info(f"Generated tweet: {tweet_text}")
            return tweet_text
            
        except Exception as e:
            logger.error(f"Failed to generate tweet: {e}")
            # Fallback to a simple template
            return f"Check out this post: {post_data['title']} {post_data['url']}"
    
    def _build_prompt(self, post_data: Dict, style_params: Dict, 
                     previous_tweets: List[Dict]) -> str:
        """Build the OpenAI prompt based on post data and style parameters"""
        
        prompt_parts = [
            f"Write a tweet promoting this blog post:",
            f"Title: {post_data['title']}",
        ]
        
        if post_data.get('description'):
            prompt_parts.append(f"Description: {post_data['description']}")
        
        if post_data.get('excerpt'):
            prompt_parts.append(f"Excerpt: {post_data['excerpt']}")
        
        # Add publish date context if available
        if post_data.get('lastmod'):
            prompt_parts.append(f"Published: {post_data['lastmod']}")
        
        prompt_parts.append(f"URL: {post_data['url']}")
        prompt_parts.append("")
        
        # Add style instructions
        prompt_parts.extend(self._get_style_instructions(style_params))
        
        # Add previous tweets to avoid
        if previous_tweets:
            prompt_parts.append("")
            prompt_parts.append("IMPORTANT: We've previously tweeted about this post. Make sure your tweet is completely different from these previous tweets:")
            for i, prev_tweet in enumerate(previous_tweets, 1):
                prompt_parts.append(f"{i}. {prev_tweet['tweet_text']}")
            prompt_parts.append("")
            prompt_parts.append("Your new tweet must use different wording, angle, and style than the above.")
        
        prompt_parts.extend([
            "",
            "Requirements:",
            f"- Must include the URL: {post_data['url']}",
            "- Maximum 280 characters total",
            "- Natural, human voice (not AI-sounding)",
            "- Engaging and clickable",
            "- DO NOT refer to the post as 'latest', 'new', or 'just published' unless it's from the last 7 days",
            "- Focus on the content value rather than recency",
            f"- Blog context: {self.config.blog_title} - {self.config.blog_description}",
            "",
            "GRAMMAR RULES:",
            "- NO Oxford commas (do not use comma before 'and' in lists)",
            "- NO em dashes (—) - use regular hyphens (-) or avoid dashes entirely"
        ])
        
        return "\n".join(prompt_parts)
    
    def _get_style_instructions(self, style_params: Dict) -> List[str]:
        """Convert style parameters into prompt instructions"""
        instructions = []
        
        # Emoji style
        emoji_style = style_params.get('emoji_style', 'none')
        if emoji_style == 'none':
            instructions.append("- Use no emojis")
        elif emoji_style == 'minimal_1':
            instructions.append("- Use exactly 1 emoji, placed naturally")
        elif emoji_style == 'moderate_2-3':
            instructions.append("- Use 2-3 emojis maximum, placed naturally")
        elif emoji_style == 'enthusiastic_3+':
            instructions.append("- Use 3+ emojis to show enthusiasm")
        
        # Tone
        tone = style_params.get('tone', 'conversational')
        tone_instructions = {
            'professional': "- Professional, authoritative tone",
            'casual': "- Casual, friendly tone",
            'enthusiastic': "- Enthusiastic, energetic tone",
            'conversational': "- Conversational, approachable tone"
        }
        instructions.append(tone_instructions.get(tone, tone_instructions['conversational']))
        
        # CTA style
        cta_style = style_params.get('cta_style', 'direct')
        cta_instructions = {
            'direct': "- Direct call-to-action (e.g., 'Read more:', 'Check it out:')",
            'question': "- Use a question to create curiosity",
            'intrigue': "- Create intrigue without giving everything away",
            'benefit-focused': "- Focus on the benefit/value to the reader"
        }
        instructions.append(cta_instructions.get(cta_style, cta_instructions['direct']))
        
        # Length target
        length_target = style_params.get('length_target', 'medium_220')
        length_instructions = {
            'concise_180': "- Keep it concise, under 180 characters",
            'medium_220': "- Aim for around 220 characters",
            'full_280': "- Use the full 280 character limit if needed"
        }
        instructions.append(length_instructions.get(length_target, length_instructions['medium_220']))
        
        # Hashtags
        if style_params.get('include_hashtags', False):
            instructions.append("- Include 1-2 relevant hashtags")
        else:
            instructions.append("- No hashtags")
        
        return instructions
    
    def _clean_tweet_text(self, tweet_text: str, post_url: str) -> str:
        """Clean and validate the generated tweet text"""
        # Remove quotes if the AI wrapped the response in quotes
        tweet_text = tweet_text.strip('"\'')
        
        # Ensure URL is included
        if post_url not in tweet_text:
            # If there's room, add the URL
            if len(tweet_text) + len(post_url) + 1 <= 280:
                tweet_text = f"{tweet_text} {post_url}"
            else:
                # Replace end of tweet with URL
                max_text_length = 280 - len(post_url) - 1
                tweet_text = tweet_text[:max_text_length].rsplit(' ', 1)[0] + f" {post_url}"
        
        # Ensure it's not too long
        if len(tweet_text) > 280:
            # Trim and add URL back
            max_text_length = 280 - len(post_url) - 1
            tweet_text = tweet_text[:max_text_length].rsplit(' ', 1)[0] + f" {post_url}"
        
        return tweet_text
    
    def post_tweet(self, tweet_text: str, image_url: Optional[str] = None) -> Optional[str]:
        """Post tweet to Twitter and return tweet ID"""
        if self.test_mode:
            logger.info("TEST MODE: Would post tweet:")
            logger.info(f"Text: {tweet_text}")
            if image_url:
                logger.info(f"Image: {image_url}")
            return "test_tweet_id"
        
        try:
            media_ids = []
            
            # Handle image if provided
            if image_url:
                media_ids = self._upload_image(image_url)
            
            # Post the tweet
            if media_ids:
                response = self.twitter_client.create_tweet(
                    text=tweet_text,
                    media_ids=media_ids
                )
            else:
                response = self.twitter_client.create_tweet(text=tweet_text)
            
            tweet_id = response.data['id']
            logger.info(f"Successfully posted tweet: {tweet_id}")
            return tweet_id
            
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return None
    
    def _upload_image(self, image_url: str) -> List[str]:
        """Download and upload image to Twitter"""
        try:
            # Download the image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Upload to Twitter using v1.1 API (v2 doesn't support media upload yet)
            media = self.twitter_api.media_upload(filename="temp_image.jpg", file=response.content)
            return [media.media_id]
            
        except Exception as e:
            logger.error(f"Failed to upload image {image_url}: {e}")
            return [] 