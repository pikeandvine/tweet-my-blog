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

# Show all environment variable NAMES (for GitHub Actions debugging)
print("\n" + "=" * 40)
print("ALL ENVIRONMENT VARIABLE NAMES:")
print("(This helps debug what GitHub Actions is actually setting)")
print()

# Categorize environment variables
github_vars = []
python_vars = []
system_vars = []
app_vars = []

for key in sorted(os.environ.keys()):
    value = os.environ[key]
    
    # Categorize variables
    if key.startswith(('GITHUB_', 'RUNNER_')):
        github_vars.append(key)
    elif key.startswith(('PYTHON', 'PIP_', 'PKG_CONFIG')):
        python_vars.append(key)
    elif key in ['PATH', 'HOME', 'USER', 'SHELL', 'TERM', 'LANG', 'LC_ALL', 'TZ']:
        system_vars.append(key)
    else:
        # These are likely our app-specific variables
        app_vars.append(key)

print("🔧 APPLICATION/CUSTOM VARIABLES:")
if app_vars:
    for var in app_vars:
        value = os.environ[var]
        # Mask sensitive values but show structure
        if any(sensitive in var.lower() for sensitive in ['key', 'secret', 'token', 'password']):
            if len(value) > 8:
                masked = value[:3] + '*' * (min(len(value) - 6, 20)) + value[-3:]
            else:
                masked = '*' * len(value)
            print(f"  {var}: {masked} (length: {len(value)})")
        else:
            # Non-sensitive values, show in full but truncate if very long
            display_value = value if len(value) <= 50 else value[:47] + "..."
            print(f"  {var}: {display_value}")
else:
    print("  None found")

print(f"\n🐙 GITHUB VARIABLES: ({len(github_vars)} found)")
for var in github_vars[:10]:  # Show first 10 GitHub vars
    print(f"  {var}")
if len(github_vars) > 10:
    print(f"  ... and {len(github_vars) - 10} more")

print(f"\n🐍 PYTHON VARIABLES: ({len(python_vars)} found)")
for var in python_vars:
    print(f"  {var}")

print(f"\n💻 SYSTEM VARIABLES: ({len(system_vars)} found)")
for var in system_vars:
    print(f"  {var}")

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
        
    # Also check a few other config values for comparison
    print(f"config.blog_title: {repr(config.blog_title)}")
    print(f"config.sitemap_url: {repr(config.sitemap_url)}")
    
except Exception as e:
    print(f"❌ Error loading config: {e}") 