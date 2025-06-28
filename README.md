# 🐦 Tweet My Blog

Automatically promote your WordPress blog posts on Twitter using AI-generated tweets. This serverless solution runs entirely on GitHub Actions and uses OpenAI to create engaging, varied tweets that promote your content without sounding repetitive or robotic.

## ✨ Features

- **WordPress Integration**: Parses your `post-sitemap.xml` to discover blog posts
- **AI-Powered Tweets**: Uses OpenAI GPT-4.1 Mini (April 2025) to generate engaging, human-sounding tweets
- **Human-Like Scheduling**: Tweets at random times each day (6am-4pm) with optional delays for natural timing
- **Smart Caching**: SQLite-based system prevents re-tweeting too frequently and avoids redundant content
- **Style Variations**: Randomizes emoji usage, tone, CTA style, and length for natural variety
- **Featured Image Support**: Automatically includes featured images from your WordPress posts
- **Nearly Zero Cost**: Runs on GitHub Actions free tier with minimal API usage (~$0.01/month)
- **Highly Configurable**: Customizable schedules, cooldowns, style parameters, and timing behavior

## 🚀 Quick Start

### 1. Set Up API Keys

You'll need:
- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Twitter API Keys**: Get from [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
  - API Key & Secret (Consumer Keys)
  - Access Token & Secret (with Read and Write permissions)
  - Bearer Token

### 2. Configure GitHub Repository

1. **Fork or clone this repository**
2. **Add GitHub Secrets** (Settings → Secrets and variables → Actions):
   ```
   OPENAI_API_KEY=your_openai_api_key
   TWITTER_API_KEY=your_twitter_api_key
   TWITTER_API_SECRET=your_twitter_api_secret
   TWITTER_ACCESS_TOKEN=your_twitter_access_token
   TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
   TWITTER_BEARER_TOKEN=your_twitter_bearer_token
   ```

3. **Add GitHub Variables** (Settings → Secrets and variables → Actions → Variables):
   ```
   SITEMAP_URL=https://yourblog.com/post-sitemap.xml
   BLOG_TITLE=Your Blog Name
   BLOG_DESCRIPTION=Brief description for context
   ENABLE_DELAY=true
   ```

### 3. Test Locally (Optional)

```bash
# Clone the repository
git clone https://github.com/yourusername/tweet-my-blog.git
cd tweet-my-blog

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp env.example .env
# Edit .env with your API keys and configuration

# Test in dry-run mode
python run.py --test

# View statistics
python run.py --stats
```

## 📋 Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `SITEMAP_URL` | *required* | URL to your WordPress post sitemap |
| `BLOG_TITLE` | *required* | Your blog name for context |
| `BLOG_DESCRIPTION` | *required* | Brief description for tweet context |
| `COOLDOWN_DAYS` | `30` | Days to wait before re-tweeting a post |
| `MAX_PREVIOUS_TWEETS` | `3` | Number of previous tweets to avoid duplicating |
| `OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI model to use for tweet generation |
| `ENABLE_DELAY` | `true` | Enable 0-180 second random delay for human-like timing |

## 🎨 Style Variations

The bot automatically randomizes these style parameters:

- **Emoji Style**: None, minimal (1), moderate (2-3), or enthusiastic (3+)
- **Tone**: Professional, casual, enthusiastic, or conversational  
- **CTA Style**: Direct, question-based, intriguing, or benefit-focused
- **Length**: Concise (180 chars), medium (220 chars), or full (280 chars)
- **Hashtags**: Random inclusion of relevant hashtags

## 🤖 How It Works

1. **Fetches your sitemap** and parses all blog post URLs
2. **Checks the cache** to avoid posts tweeted within the cooldown period
3. **Randomly selects** an eligible post
4. **Scrapes post content** (title, description, excerpt) for context
5. **Generates tweet** using OpenAI with randomized style parameters
6. **Avoids redundancy** by comparing against previous tweets for the same post
7. **Posts to Twitter** with optional featured image
8. **Updates cache** to track what's been tweeted

## 📅 Human-Like Scheduling

The bot uses a sophisticated scheduling system to make tweets appear more natural and less bot-like:

### How It Works
- **11 different execution times** throughout the day (6:12am - 4:29pm PDT)
- **One random time slot chosen daily** - tweets appear at different times each day
- **Quick exit strategy** - 10 executions exit immediately, only 1 actually tweets
- **Optional random delay** of 0-180 seconds for additional human-like variability

### Time Slots (PDT/UTC)
```
06:12 AM PDT (13:12 UTC)  |  11:26 AM PDT (18:26 UTC)
07:23 AM PDT (14:23 UTC)  |  12:43 PM PDT (19:43 UTC) 
08:08 AM PDT (15:08 UTC)  |  01:17 PM PDT (20:17 UTC)
09:37 AM PDT (16:37 UTC)  |  02:33 PM PDT (21:33 UTC)
10:19 AM PDT (17:19 UTC)  |  03:11 PM PDT (22:11 UTC)
                          |  04:29 PM PDT (23:29 UTC)
```

### Customizing Time Zone & Window

To adapt for your time zone, modify the cron schedules in `.github/workflows/tweet.yaml`:

```yaml
schedule:
  # Example: For EST (UTC-5), subtract 5 hours from UTC times above
  - cron: "12 08 * * *"  # 8:12 UTC = 3:12am EST
  - cron: "23 09 * * *"  # 9:23 UTC = 4:23am EST
  # ... add your preferred times
```

**Important**: Also update the time slots in `tweet_bot/daily_scheduler.py` to match:

```python
time_slots = [
    (8, 12),   # 8:12 UTC (3:12am EST)
    (9, 23),   # 9:23 UTC (4:23am EST)
    # ... your custom times
]
```

### Random Delay Feature

The `ENABLE_DELAY` variable controls additional timing randomization:

#### When Enabled (`ENABLE_DELAY=true`, default):
- ✅ **More human-like**: Adds 0-180 seconds of random delay
- ✅ **Less predictable**: Tweets don't appear at exact scheduled times
- ⚠️ **Costs more**: Uses additional GitHub Actions minutes (up to 3 extra minutes/day)

#### When Disabled (`ENABLE_DELAY=false`):
- ✅ **Cost efficient**: Saves ~60-90 GitHub Actions minutes/month
- ✅ **Predictable timing**: Tweets at exact scheduled times
- ⚠️ **More bot-like**: Could be detected as automated

#### Set in GitHub Variables:
```
ENABLE_DELAY=true   # Enable random delay (recommended)
ENABLE_DELAY=false  # Disable for cost savings
```

### Manual Control

You can still trigger tweets manually:
- **GitHub Actions UI**: Use "Run workflow" with optional test mode
- **Local testing**: `python run.py --test` (skips scheduling)
- **Force execution**: `python run.py --force` (bypasses time check)

## 🛠️ Commands

```bash
# Run normally (respects scheduling)
python run.py

# Test mode (generate but don't post, respects scheduling)
python run.py --test

# Force execution (bypass scheduling check)
python run.py --force

# Test mode with forced execution
python run.py --test --force

# View statistics
python run.py --stats

# Clean up old cache data
python run.py --cleanup 365
```

## 📊 Cache Management

The SQLite cache (`cache.db`) tracks:
- Posts that have been tweeted and when
- Full history of tweets for redundancy avoidance
- Success/failure logs for debugging

The cache file is automatically committed back to your repository to persist between GitHub Actions runs.

## 🔧 Customization

### WordPress Compatibility

The sitemap parser is configured for standard WordPress post sitemaps. If your site uses a different structure, modify the `_is_blog_post_url()` method in `tweet_bot/sitemap_parser.py`.

### Style Parameters

Customize the style variations in `tweet_bot/config.py` by modifying the `style_variations` dictionary.

### Prompt Engineering

The AI prompts can be customized in `tweet_bot/tweet_generator.py` in the `_build_prompt()` method.

### Model Selection

Choose your OpenAI model based on your needs:

- **gpt-4.1-mini** (default): Best balance of quality and cost. Released April 2025.
- **gpt-4.1-nano**: Ultra-cheap option for maximum cost savings
- **gpt-4o-mini**: Older model, more expensive but still reliable

Set via `OPENAI_MODEL` environment variable.

## 🚨 Troubleshooting

### Common Issues

1. **"No eligible posts found"**: Check your sitemap URL and ensure it's accessible
2. **Twitter API errors**: Verify your API keys have Read and Write permissions
3. **OpenAI API errors**: Check your API key and usage limits
4. **Cache not persisting**: Ensure the GitHub Actions workflow has write permissions
5. **Scheduling issues**: See troubleshooting section below

### Scheduling Troubleshooting

**"Not scheduled to run now" messages:**
- This is normal! Most executions (10/11) will show this message
- Only 1 execution per day should proceed to tweet
- Check `daily_schedule.json` in your repo to see today's chosen time

**No tweets being posted:**
- Verify your cron schedules match your time zone
- Check if `ENABLE_DELAY` is causing longer delays than expected
- Use `python run.py --force` to bypass scheduling for testing

**Multiple tweets per day:**
- This shouldn't happen with proper configuration
- Check that `daily_schedule.json` is being committed to your repo
- Verify GitHub Actions has write permissions to commit files

**Wrong time zone:**
- Update both `.github/workflows/tweet.yaml` cron schedules
- Update `time_slots` array in `tweet_bot/daily_scheduler.py`
- Both must match for the system to work correctly

### Debug Mode

Run with `--test` flag to see what would be tweeted without actually posting:

```bash
python run.py --test
```

Check the `tweet_generator.log` file for detailed debugging information.

## 💰 Expected Costs

**Nearly free to run:**
- **OpenAI API:** ~$0.0002 per tweet with GPT-4.1 Mini (6x cheaper than GPT-4o!)
- **Twitter API:** Free tier allows plenty of tweets per month
- **GitHub Actions:** 3-4 minutes/day for human-like scheduling (90-120 minutes/month)

### GitHub Actions Usage Breakdown:
- **11 executions daily**, but only 1 actually tweets
- **10 "quick exits"** use ~1 minute total (seconds each)
- **1 full execution** uses ~2-3 minutes (tweet generation + posting)
- **Random delay** adds 0-3 minutes when enabled
- **Monthly total**: ~90-120 minutes (well under 2,000 minute free tier)

### Cost Options:
- **With delay enabled**: ~120 minutes/month GitHub Actions + $0.006/month OpenAI
- **With delay disabled**: ~90 minutes/month GitHub Actions + $0.006/month OpenAI

**Total monthly cost: ~$0.01** (essentially free)

## 📄 License

MIT License - feel free to use and modify for your own blog promotion needs!

## 🤝 Contributing

Contributions welcome! Feel free to:
- Report bugs
- Suggest features  
- Submit pull requests
- Share your customizations

---

**Happy tweeting! 🐦✨** 