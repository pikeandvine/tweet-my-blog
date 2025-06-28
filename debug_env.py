#!/usr/bin/env python3
"""
Debug script to check environment variable loading
"""

import os
from dotenv import load_dotenv

print("🔍 Environment Variable Debug")
print("=" * 40)

# Load .env file (if it exists locally)
load_dotenv()

# Check specific variables
variables_to_check = [
    'NTFY_TOPIC',
    'OPENAI_API_KEY',
    'TWITTER_API_KEY',
    'SITEMAP_URL',
    'BLOG_TITLE'
]

print("Checking key environment variables:")
for var in variables_to_check:
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if 'key' in var.lower() or 'secret' in var.lower() or 'token' in var.lower():
            masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '*' * len(value)
            print(f"✅ {var}: {masked}")
        else:
            print(f"✅ {var}: {value}")
    else:
        print(f"❌ {var}: NOT SET")

print("\n" + "=" * 40)
print("All environment variables containing 'NTFY':")
ntfy_vars = {k: v for k, v in os.environ.items() if 'NTFY' in k.upper()}
if ntfy_vars:
    for k, v in ntfy_vars.items():
        print(f"  {k}: {v}")
else:
    print("  None found")

print("\nAll environment variables containing 'TOPIC':")
topic_vars = {k: v for k, v in os.environ.items() if 'TOPIC' in k.upper()}
if topic_vars:
    for k, v in topic_vars.items():
        print(f"  {k}: {v}")
else:
    print("  None found")

# Test the config loading
print("\n" + "=" * 40)
print("Testing Config class loading:")
try:
    from tweet_bot.config import Config
    config = Config()
    print(f"config.ntfy_topic: {repr(config.ntfy_topic)}")
    if config.ntfy_topic:
        print(f"✅ NTFY_TOPIC loaded successfully: {config.ntfy_topic}")
    else:
        print("❌ NTFY_TOPIC is None or empty")
except Exception as e:
    print(f"❌ Error loading config: {e}") 