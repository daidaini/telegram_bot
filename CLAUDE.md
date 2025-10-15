# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Flask-based Telegram bot service that provides various information services using long polling mode, with optional webhook support. The bot delivers RSS news, AI-powered content generation, news headlines, and inspirational quotes with sophisticated caching and channel forwarding capabilities.

## Architecture & Structure

### Core Components
- **Flask Application** (`app.py`) - Main bot logic with dual operation modes (polling/webhook)
- **Command Handler** (`commands.py`) - Processes bot commands and orchestrates functionality
- **RSS Handler** (`rss_handler.py`) - RSS feed fetching with round-robin logic and deduplication
- **Hacker News Handler** (`hackernews_handler.py`) - AI article discovery from Hacker News with intelligent content extraction
- **Content Fetcher** (`content_fetcher.py`) - BeautifulSoup-based web content extraction with smart detection
- **Telegraph Client** (`telegraph_client.py`) - Telegraph API integration for publishing AI analysis results
- **Content Generator** (`content_generator.py`) - AI-powered content generation with intent analysis
- **Configuration** (`config.py`) - Environment-based configuration management

### Bot Operation Modes
The bot supports two operational modes controlled by environment variables:

1. **Polling Mode** (default) - Uses long polling via `start_polling()` in `app.py:149`
2. **Webhook Mode** - Uses Telegram webhooks for real-time updates (requires webhook setup)

### RSS System Architecture
- **Round-Robin Logic**: Fetches maximum one article per RSS feed per request via `fetch_all_feeds_round_robin()` in `rss_handler.py:359`
- **Today-Only Filtering**: Only retrieves articles published on the current day via `_is_today()` in `rss_handler.py:96`
- **Deduplication**: Uses MD5 hashing of title+link to prevent duplicate content via `_get_article_hash()` in `rss_handler.py:142`
- **Smart Caching**: 7-day cache retention with metadata (feed name, fetch time) in `_load_cache()` at `rss_handler.py:61`
- **Channel Forwarding**: Automatic forwarding to configured Telegram channels via `send_message_to_channel()` in `app.py:75`

### Command System
Commands are registered in `CommandHandler` class and processed via `handle_command()` method in `commands.py:388`:
- `/list` or `/help` - Display all available commands
- `/rss_news` - Get latest news from RSS feeds with optional channel forwarding
- `/news [country|topic]` - Get news headlines via GNews API
- `/hacker_news` - Get AI-related articles from Hacker News with intelligent analysis and content extraction
- `/quote` - Get AI-generated inspirational quotes with detailed analysis
- `/ask [question]` - Ask AI assistant a question using OpenAI API

### Hacker News Integration
- **AI Article Discovery**: Searches Hacker News for today's AI-related articles using keyword matching via `find_ai_article_today()` in `hackernews_handler.py:72`
- **Intelligent Content Extraction**: Uses BeautifulSoup-based `ContentFetcher` to extract main content from web pages
- **Multi-Strategy Extraction**: Implements 4-tier content detection (common selectors, largest text block, article tags, heuristics)
- **Professional AI Analysis**: Uses specialized tech journalist persona for in-depth article analysis
- **Telegraph Publishing**: Automatically publishes AI analysis results to Telegraph for permanent, shareable links
- **Selective Channel Forwarding**: Forwards only Telegraph links to channels (not full analysis), channel users get clean links to detailed content

### AI Content Generation
- **OpenAI Integration**: `content_generator.py` provides AI-powered content generation with intent analysis
- **Context Management**: Maintains conversation history in `user_context.md` via `ContextManager` class
- **Custom API Support**: Works with OpenAI-compatible APIs (Deepseek, local models) via `OpenAIClient` wrapper
- **Multi-language Support**: Chinese and English content generation

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv venv && source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Running the Bot
```bash
# Standard startup (recommended)
python app.py

# Test AI content generation directly (requires OpenAI API key)
python content_generator.py "Your question here"

# System status check
python system_status.py
```

### Testing Commands
All tests are located in the `Test/` directory. Run tests from the Test directory:

```bash
# Run all tests
cd Test && python3 run_all_tests.py

# Run individual tests
cd Test
python3 test_ask_command.py          # Test AI Q&A functionality
python3 test_rss.py                  # Test RSS functionality
python3 test_channel_forwarding.py   # Test channel forwarding
python3 test_news.py                 # Test GNews integration
python3 test_hackernews.py           # Test Hacker News functionality
python3 test_hackernews_command.py  # Test Hacker News command integration
python3 test_content_fetcher.py      # Test BeautifulSoup content extraction
python3 test_telegraph_integration.py # Test Telegraph publishing functionality
python3 test_hackernews_channel_only_telegraph.py # Test channel-only Telegraph forwarding
python3 test_round_robin_rss.py       # Test round-robin RSS logic
python3 test_message_send.py         # Test message sending functionality
python3 test_webhook_integration.py  # Test webhook integration
python3 demo_command_parsing.py      # Demo command parsing process
```

### Production Deployment
```bash
# Production with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Configuration Management

### Required Environment Variables
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather (required for bot operation)

### Optional API Keys
- `GNEWS_API_KEY` - GNews API key for news headlines
- `OPENAI_API_KEY` - OpenAI API key for AI content generation
- `OPENAI_BASE_URL` - Custom API base URL for OpenAI-compatible APIs
- `DEFAULT_MODEL` - Default model to use (e.g., gpt-3.5-turbo, gpt-4, deepseek-chat)

### RSS Configuration
- `RSS_FEEDS` - JSON array of RSS feed configurations
- `MAX_ARTICLES_PER_FEED` - Maximum articles per feed (default: 3)
- `RSS_FORWARD_TO_CHANNEL` - Channel username for auto-forwarding
- `ENABLE_RSS_FORWARDING` - Enable/disable channel forwarding

### Webhook Configuration (Optional)
- `BOT_MODE` - 'polling' (default) or 'webhook'
- `WEBHOOK_URL` - Your webhook URL for webhook mode
- `WEBHOOK_SECRET_TOKEN` - Secret token for webhook security
- `WEBHOOK_PORT` - Port for webhook server (default: 5000)

## Key Implementation Details

### RSS Feed Processing
- Uses `feedparser` library with SSL context configuration to handle certificate issues in `_setup_ssl_context()` at `rss_handler.py:47`
- Implements date parsing with `python-dateutil` for flexible date format handling in `_is_today()` at `rss_handler.py:96`
- Cache structure includes metadata: `{'title': '', 'link': '', 'feed_name': '', 'fetched_at': '', 'published_at': ''}`
- Round-robin fetching ensures balanced content distribution across feeds
- Channel message formatting with automatic markdown escaping via `escape_markdown()` in `rss_handler.py:13`

### Bot Message Handling
- Long polling with configurable timeout (30 seconds default) in `get_updates()` at `app.py:114`
- Background threading for non-blocking operation in polling mode via `start_polling()` at `app.py:149`
- Flask routes for health checks (`/health`) and webhook endpoint (`/webhook`)
- Markdown formatting for all bot responses with fallback to plain text
- Command parsing uses `split(maxsplit=1)` to separate commands from parameters

### Content Fetching Architecture
- **BeautifulSoup Integration**: Uses `content_fetcher.py` for intelligent web content extraction
- **Multi-Strategy Detection**: 4-tier content detection algorithm (common selectors → largest text block → article tags → heuristics)
- **Content Cleaning**: Automatic removal of ads, navigation, comments, and metadata artifacts
- **Smart Headers**: Realistic browser headers to avoid blocking and rate limiting
- **Fallback Mechanisms**: Graceful degradation when content extraction fails

### Telegraph Integration
- **Account Management**: Automatic Telegraph account creation and token management
- **Markdown Publishing**: Converts AI analysis Markdown to Telegraph-compatible format
- **Content Formatting**: Intelligent conversion of structured analysis to Telegraph pages
- **URL Generation**: Provides permanent, shareable links for published analysis
- **Error Handling**: Graceful fallback when Telegraph publishing fails

### AI Integration Architecture
- Content generation via `OpenAIClient` wrapper with custom base URL support
- Intent analysis and context management for conversational AI responses
- Context persistence in `user_context.md` file for conversation history
- Multi-step content generation: intent parsing → context retrieval → response generation
- Enhanced quote generation with comprehensive analysis including author background, historical context, and modern relevance
- **Professional Analysis**: Specialized tech journalist persona for Hacker News article analysis with structured output format

### Error Handling Patterns
- Graceful degradation for API failures (static quotes fallback)
- Comprehensive logging with structured format
- User-friendly error messages with actionable suggestions
- Network timeout handling (10 seconds for external APIs)
- Markdown format error recovery with automatic fallback to plain text

## Common Development Tasks

### Adding New Bot Commands
1. Add command method to `CommandHandler` class in `commands.py`
2. Register command in `self.commands` dictionary in `__init__()` method
3. Implement command logic with proper error handling
4. Update help text in `list_commands()` method
5. Add tests in `Test/test_new_command.py`

### Modifying RSS Feeds
1. Update `RSS_FEEDS` environment variable or modify `_get_default_rss_feeds()` in `config.py:58`
2. Test feed accessibility: `python -c "import feedparser; print(feedparser.parse('URL'))"`
3. Clear cache if needed: `rm rss_cache.json`
4. Test with: `cd Test && python3 test_rss.py`

### Testing AI Features
1. Ensure `OPENAI_API_KEY` is configured in `.env`
2. Test directly: `python content_generator.py "test question"`
3. Test bot integration: `cd Test && python3 test_ask_command.py`
4. Verify context management: Check `user_context.md` file

### Testing Hacker News Features
1. Test API integration: `cd Test && python3 test_hackernews.py`
2. Test content extraction: `cd Test && python3 test_content_fetcher.py`
3. Test command integration: `cd Test && python3 test_hackernews_command.py`
4. Test Telegraph publishing: `cd Test && python3 test_telegraph_integration.py`
5. Verify AI analysis: Check that analysis includes structured sections (新闻概要, 技术解析, etc.)
6. Verify Telegraph links: Ensure Telegraph URLs are generated and included in responses

### Debugging Common Issues

#### 409 Conflict Error
Occurs when bot is simultaneously configured for webhook and polling modes:
```bash
# Check webhook status
curl -X GET "https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
# Delete webhook to use polling
curl -X POST "https://api.telegram.org/bot{TOKEN}/deleteWebhook"
```

#### SSL Certificate Issues with RSS
The bot automatically configures SSL context to handle certificate verification problems in `_setup_ssl_context()`.

#### Channel Forwarding Failures
- Ensure bot is added as administrator to target channel
- Verify channel username is correct (without @ symbol)
- Check `ENABLE_RSS_FORWARDING=true` in environment variables

#### OpenAI API Issues
- Verify `OPENAI_API_KEY` is valid and active
- Check `OPENAI_BASE_URL` if using custom API endpoints
- Ensure sufficient API credits/quota available

#### Content Fetching Issues
- Some websites may block automated requests (handled by realistic headers)
- Content extraction may fail on heavily JavaScript-rendered pages
- Rate limiting may occur on frequent requests to same domains

#### Telegraph Publishing Issues
- Telegraph API may have rate limits for page creation
- Account creation may fail if Telegraph service is unavailable
- Markdown formatting issues may affect page appearance
- URL generation may fail if page creation encounters errors

## Test Organization

All test code is centralized in the `Test/` directory with the following structure:
- **Core functionality tests**: `test_ask_command.py`, `test_rss.py`, `test_news.py`
- **Hacker News tests**: `test_hackernews.py`, `test_hackernews_command.py`, `test_content_fetcher.py`
- **Telegraph tests**: `test_telegraph_integration.py`, `test_hackernews_channel_only_telegraph.py`
- **Logic tests**: `test_round_robin_logic.py`, `test_round_robin_rss.py`
- **Integration tests**: `test_channel_forwarding.py`, `test_message_send.py`, `test_webhook_integration.py`
- **Demos**: `demo_command_parsing.py`
- **Test utilities**: `run_all_tests.py` (batch test runner), `update_imports.py` (path updater)

Test files use parent directory imports: `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`

## Hacker News AI Analysis Workflow

The `/hacker_news` command implements a sophisticated content analysis pipeline:

1. **Article Discovery**: Searches Hacker News API for today's AI-related articles using keyword matching
2. **Content Extraction**: Uses intelligent BeautifulSoup-based extraction to get clean article content
3. **Professional Analysis**: Applies tech journalist persona with structured output format:
   - 📰 新闻概要 (News Summary)
   - 🔑 关键信息 (Key Information)
   - 🔬 技术解析 (Technical Analysis)
   - 📊 影响分析 (Impact Analysis)
   - 🔮 趋势洞察 (Trend Insights)
   - 💭 专业评价 (Professional Evaluation)
4. **Telegraph Publishing**: Automatically publishes analysis results to Telegraph for permanent sharing
5. **Dual Messaging**:
   - **User Response**: Full analysis + Telegraph link
   - **Channel Forwarding**: Only Telegraph link (clean, minimal content)

## Dependencies

### Core Python Libraries
- `Flask==2.3.3` - Web framework
- `requests==2.31.0` - HTTP client
- `python-dotenv==1.0.0` - Environment management
- `beautifulsoup4==4.13.4` - HTML parsing and content extraction
- `lxml==5.4.0` - XML/HTML parser
- `html5lib==1.1` - HTML5 parsing
- `PySocks>=1.7.1` - SOCKS proxy support
- `openai>=1.0.0` - AI API integration
- `feedparser==6.0.10` - RSS feed parsing
- `python-dateutil==2.8.2` - Date parsing utilities

### External Services
- **Telegram Bot API** - Bot messaging platform
- **Hacker News API** - Article discovery
- **OpenAI API** - AI content analysis (optional)
- **GNews API** - News headlines (optional)
- to memorize