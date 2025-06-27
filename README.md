# 🐦 Tweet My Blog

Automatically promote your WordPress blog posts on Twitter using AI-generated tweets. This serverless solution runs entirely on GitHub Actions and uses OpenAI to create engaging, varied tweets that promote your content without sounding repetitive or robotic.

## ✨ Features

- **WordPress Integration**: Parses your `post-sitemap.xml` to discover blog posts
- **AI-Powered Tweets**: Uses OpenAI GPT-4.1 Mini (April 2025) to generate engaging, human-sounding tweets
- **Smart Caching**: SQLite-based system prevents re-tweeting too frequently and avoids redundant content
- **Style Variations**: Randomizes emoji usage, tone, CTA style, and length for natural variety
- **Featured Image Support**: Automatically includes featured images from your WordPress posts
- **Zero Cost**: Runs on GitHub Actions free tier with free-tier API usage
- **Configurable**: Customizable cooldown periods, tweet frequency, and style parameters

## 🚀 Quick Start

### 1. Set Up API Keys

You'll need:
- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Twitter API Keys**: Get from [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
  - API Key & Secret
  - Access Token & Secret (with Read and Write permissions)

### 2. Configure GitHub Repository

1. **Fork or clone this repository**
2. **Add GitHub Secrets** (Settings → Secrets and variables → Actions):
   ```
   OPENAI_API_KEY=your_openai_api_key
   TWITTER_API_KEY=your_twitter_api_key
   TWITTER_API_SECRET=your_twitter_api_secret
   TWITTER_ACCESS_TOKEN=your_twitter_access_token
   TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
   ```

3. **Add GitHub Variables** (Settings → Secrets and variables → Actions → Variables):
   ```
   SITEMAP_URL=https://yourblog.com/post-sitemap.xml
   BLOG_TITLE=Your Blog Name
   BLOG_DESCRIPTION=Brief description for context
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
| `TWEET_FREQUENCY` | `daily` | How often to tweet (for reference) |
| `OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI model to use for tweet generation |

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

## 📅 Scheduling

The GitHub Actions workflow runs:
- **Daily at 9 AM UTC** (customize in `.github/workflows/tweet.yaml`)
- **Manual trigger** via GitHub Actions UI (with optional test mode)

## 🛠️ Commands

```bash
# Run normally (posts tweets)
python run.py

# Test mode (generate but don't post)
python run.py --test

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
- **GitHub Actions:** Free tier provides 2,000 minutes/month

**Daily tweeting costs roughly $0.006/month** in OpenAI usage.

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