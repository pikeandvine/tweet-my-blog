#!/usr/bin/env python3
"""
Test script for ntfy.sh notifications

This script demonstrates how the notification system works.
Run this to test your ntfy.sh setup before using it with the tweet bot.

Usage:
    python test_notifications.py your_topic_name
    
Example:
    python test_notifications.py my-blog-tweets
"""

import sys
from tweet_bot.notifier import Notifier

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_notifications.py <your_topic_name>")
        print("Example: python test_notifications.py my-blog-tweets")
        sys.exit(1)
    
    topic = sys.argv[1]
    print(f"🔔 Testing ntfy.sh notifications with topic: {topic}")
    print(f"📱 Make sure you're subscribed to: https://ntfy.sh/{topic}")
    print()
    
    # Initialize notifier
    notifier = Notifier(topic)
    
    # Test success notification
    print("📤 Sending test tweet notification...")
    success = notifier.send_tweet_notification(
        tweet_text="🎉 This is a test tweet from your tweet bot! The notification system is working correctly.",
        post_url="https://example.com/test-post",
        tweet_id="1234567890"
    )
    
    if success:
        print("✅ Tweet notification sent successfully!")
    else:
        print("❌ Failed to send tweet notification")
        return
    
    print()
    input("Press Enter to send error notification test...")
    
    # Test error notification
    print("📤 Sending test error notification...")
    success = notifier.send_error_notification(
        error_message="This is a test error notification - everything is working fine!",
        post_url="https://example.com/test-post"
    )
    
    if success:
        print("✅ Error notification sent successfully!")
        print()
        print("🎉 All tests passed! Your notification setup is working correctly.")
        print("💡 You can now use this topic with your tweet bot by setting:")
        print(f"   NTFY_TOPIC={topic}")
    else:
        print("❌ Failed to send error notification")

if __name__ == "__main__":
    main() 