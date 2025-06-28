#!/usr/bin/env python3
"""
Test script for Twitter API authentication

This script helps debug Twitter API connection issues.
Run this to verify your Twitter API credentials are working correctly.

Usage:
    python test_twitter_auth.py
"""

import os
from dotenv import load_dotenv
import tweepy

# Load environment variables
load_dotenv()

def test_twitter_auth():
    """Test Twitter API authentication"""
    
    # Get credentials
    api_key = os.getenv('TWITTER_API_KEY')
    api_secret = os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    
    print("🐦 Testing Twitter API Authentication")
    print("=" * 40)
    
    # Check if credentials are present
    missing_creds = []
    if not api_key:
        missing_creds.append('TWITTER_API_KEY')
    if not api_secret:
        missing_creds.append('TWITTER_API_SECRET')
    if not access_token:
        missing_creds.append('TWITTER_ACCESS_TOKEN')
    if not access_token_secret:
        missing_creds.append('TWITTER_ACCESS_TOKEN_SECRET')
    
    if missing_creds:
        print("❌ Missing credentials:")
        for cred in missing_creds:
            print(f"   - {cred}")
        print("\nPlease set these environment variables in your .env file")
        return False
    
    # Partially mask credentials for display
    def mask_credential(cred):
        if len(cred) > 8:
            return cred[:4] + '*' * (len(cred) - 8) + cred[-4:]
        return '*' * len(cred)
    
    print("✅ Found credentials:")
    print(f"   API Key: {mask_credential(api_key)}")
    print(f"   API Secret: {mask_credential(api_secret)}")
    print(f"   Access Token: {mask_credential(access_token)}")
    print(f"   Access Token Secret: {mask_credential(access_token_secret)}")
    print()
    
    try:
        # Test v1.1 API (for media upload)
        print("🔐 Testing Twitter v1.1 API...")
        auth = tweepy.OAuthHandler(api_key, api_secret)
        auth.set_access_token(access_token, access_token_secret)
        api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
        
        # Test by getting user info
        user = api_v1.verify_credentials()
        print(f"✅ v1.1 API authenticated as: @{user.screen_name}")
        
        # Test v2 API (for posting tweets)
        print("🔐 Testing Twitter v2 API...")
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=True
        )
        
        # Test by getting user info
        me = client_v2.get_me()
        print(f"✅ v2 API authenticated as: @{me.data.username}")
        
        print("\n🎉 All tests passed! Your Twitter API credentials are working correctly.")
        
        # Check permissions
        print("\n🔍 Checking API permissions...")
        try:
            # Try to get recent tweets to check read permissions
            tweets = client_v2.get_me(user_fields=['public_metrics'])
            print("✅ Read permissions: OK")
            
            # Note: We can't easily test write permissions without actually posting
            print("⚠️  Write permissions: Cannot test without posting a tweet")
            print("   If you get 401 errors when posting, check that your app has 'Read and Write' permissions")
            
        except Exception as e:
            print(f"⚠️  Permission check failed: {e}")
        
        return True
        
    except tweepy.Unauthorized as e:
        print(f"❌ Authentication failed: {e}")
        print("\nPossible issues:")
        print("1. Check that your API keys are correct")
        print("2. Ensure your Twitter app has 'Read and Write' permissions")
        print("3. Regenerate your access tokens after changing permissions")
        print("4. Make sure your Twitter account is not restricted")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_twitter_auth()
    exit(0 if success else 1) 