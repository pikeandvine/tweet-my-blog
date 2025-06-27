"""
WordPress sitemap parser for extracting blog post information
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class SitemapParser:
    """Parses WordPress post sitemaps and extracts post information"""
    
    def __init__(self, sitemap_url: str):
        self.sitemap_url = sitemap_url
    
    def fetch_posts(self) -> List[Dict]:
        """Fetch and parse all posts from the sitemap"""
        try:
            logger.info(f"Fetching sitemap from {self.sitemap_url}")
            response = requests.get(self.sitemap_url, timeout=30)
            response.raise_for_status()
            
            return self._parse_sitemap_xml(response.content)
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch sitemap: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"Failed to parse sitemap XML: {e}")
            return []
    
    def _parse_sitemap_xml(self, xml_content: bytes) -> List[Dict]:
        """Parse the XML sitemap content"""
        try:
            root = ET.fromstring(xml_content)
            
            # Handle WordPress sitemap namespace
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'image': 'http://www.google.com/schemas/sitemap-image/1.1'
            }
            
            posts = []
            
            for url_elem in root.findall('sitemap:url', namespaces):
                post_data = self._extract_post_data(url_elem, namespaces)
                if post_data:
                    posts.append(post_data)
            
            logger.info(f"Parsed {len(posts)} posts from sitemap")
            return posts
            
        except Exception as e:
            logger.error(f"Error parsing sitemap XML: {e}")
            return []
    
    def _extract_post_data(self, url_elem, namespaces: Dict) -> Optional[Dict]:
        """Extract post data from a URL element"""
        try:
            # Get basic URL info
            loc_elem = url_elem.find('sitemap:loc', namespaces)
            if loc_elem is None:
                return None
            
            url = loc_elem.text.strip()
            
            # Skip if not a blog post URL (customize this for your site structure)
            if not self._is_blog_post_url(url):
                return None
            
            # Get last modified date
            lastmod_elem = url_elem.find('sitemap:lastmod', namespaces)
            lastmod = lastmod_elem.text if lastmod_elem is not None else None
            
            # Get featured image (WordPress includes these in image:image tags)
            image_elem = url_elem.find('image:image', namespaces)
            featured_image = None
            
            if image_elem is not None:
                image_loc = image_elem.find('image:loc', namespaces)
                if image_loc is not None:
                    featured_image = image_loc.text.strip()
            
            # Extract title from URL (we'll get the real title when we scrape)
            title = self._extract_title_from_url(url)
            
            return {
                'url': url,
                'title': title,
                'lastmod': lastmod,
                'featured_image': featured_image
            }
            
        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            return None
    
    def _is_blog_post_url(self, url: str) -> bool:
        """Determine if URL is a blog post (customize for your site)"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # For pikeandvine.com, blog posts are typically /post-slug/
        # Exclude main blog page and other non-post pages
        if path in ['/', '/blog/', '/blog']:
            return False
        
        # Exclude common WordPress pages
        excluded_patterns = [
            '/wp-', '/feed', '/sitemap', '/category/', '/tag/', 
            '/author/', '/search/', '/page/', '/privacy', '/terms'
        ]
        
        for pattern in excluded_patterns:
            if pattern in path:
                return False
        
        # Must have content (not just domain)
        if len(path.strip('/')) == 0:
            return False
            
        return True
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract a basic title from the URL slug"""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if '/' in path:
            # Take the last part if there are multiple segments
            slug = path.split('/')[-1]
        else:
            slug = path
        
        # Convert slug to title-case
        title = slug.replace('-', ' ').replace('_', ' ').title()
        return title
    
    def get_eligible_posts(self, excluded_urls: set) -> List[Dict]:
        """Get posts that are eligible for tweeting (not in excluded set)"""
        all_posts = self.fetch_posts()
        
        eligible = [
            post for post in all_posts 
            if post['url'] not in excluded_urls
        ]
        
        logger.info(f"Found {len(eligible)} eligible posts out of {len(all_posts)} total")
        return eligible 