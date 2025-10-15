# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Flask-based Telegram bot service that provides various information services using long polling mode, with optional webhook support.

## Architecture & Structure

### Core Components
- **Flask Application** (`app.py`) - Main bot logic with dual operation modes (polling/webhook)
- **Command Handler** (`commands.py`) - Processes bot commands and orchestrates functionality
- **RSS Handler** (`rss_handler.py`) - RSS feed fetching with round-robin logic and deduplication
- **Configuration** (`config.py`) - Environment-based configuration management

### Bot Operation Modes
The bot supports two operational modes controlled by `BOT_MODE` environment variable:

1. **Polling Mode** (`BOT_MODE=polling`) - Default mode using long polling
2. **Webhook Mode** (`BOT_MODE=webhook`) - Uses Telegram webhooks for real-time updates

### RSS System Architecture
- **Round-Robin Logic**: Fetches maximum one article per RSS feed per request
- **Today-Only Filtering**: Only retrieves articles published on the current day
- **Deduplication**: Uses MD5 hashing of title+link to prevent duplicate content
- **Smart Caching**: 7-day cache retention with metadata (feed name, fetch time)
- **Channel Forwarding**: Automatic forwarding to configured Telegram channels

### Command System
Commands are registered in `CommandHandler` class and processed via `handle_command()` method:
- `/list` or `/help` - Display all available commands
- `/rss_news` - Get latest news from RSS feeds with optional channel forwarding
- `/news [country|topic]` - Get news headlines via GNews API
- `/quote` - Get AI-generated inspirational quotes with detailed analysis (author info, historical background, modern relevance, related references, and practical applications)
- `/ask [question]` - Ask AI assistant a question using OpenAI API

### AI Content Generation
- **OpenAI Integration**: `content_generator.py` provides AI-powered content generation with intent analysis
- **Context Management**: Maintains conversation history in `user_context.md`
- **Custom API Support**: Works with OpenAI-compatible APIs (Deepseek, local models)
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
python start_bot.py

# Direct Flask app
python app.py

# Production with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
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
python3 test_round_robin_rss.py       # Test round-robin RSS logic
python3 test_message_send.py         # Test message sending functionality
python3 test_webhook_integration.py  # Test webhook integration
python3 test_round_robin_logic.py    # Test round-robin algorithm
python3 demo_command_parsing.py      # Demo command parsing process

# System status (run from root)
python system_status.py              # System status check

# Test AI content generation directly (requires OpenAI API key)
python content_generator.py "Your question here"
```

### Webhook Management
```bash
# Check webhook status
curl -X GET "https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"

# Set webhook (requires publicly accessible HTTPS URL)
curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://yourdomain.com/webhook", "secret_token": "your_secret"}'

# Delete webhook (switch back to polling)
curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
```

## Configuration Management

### Required Environment Variables
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather

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

### Webhook Configuration
- `BOT_MODE` - 'polling' (default) or 'webhook'
- `WEBHOOK_URL` - Your webhook URL for webhook mode
- `WEBHOOK_SECRET_TOKEN` - Secret token for webhook security
- `WEBHOOK_PORT` - Port for webhook server (default: 5000)

## Key Implementation Details

### RSS Feed Processing
- Uses `feedparser` library with SSL context configuration to handle certificate issues
- Implements date parsing with `python-dateutil` for flexible date format handling
- Cache structure includes metadata: `{'title': '', 'link': '', 'feed_name': '', 'fetched_at': '', 'published_at': ''}`
- Round-robin fetching ensures balanced content distribution across feeds
- Channel message formatting with automatic markdown escaping

### Bot Message Handling
- Long polling with configurable timeout (30 seconds default)
- Background threading for non-blocking operation in polling mode
- Flask routes for health checks (`/health`) and webhook endpoint (`/webhook`)
- Markdown formatting for all bot responses with fallback to plain text
- Command parsing uses `split(maxsplit=1)` to separate commands from parameters

### AI Integration Architecture
- Content generation via `OpenAIClient` wrapper with custom base URL support
- Intent analysis and context management for conversational AI responses
- Context persistence in `user_context.md` file for conversation history
- Multi-step content generation: intent parsing → context retrieval → response generation
- **Enhanced Quote System**: AI-generated inspirational quotes with comprehensive analysis including:
  - Deep philosophical interpretation of quotes
  - Historical context and author background
  - Modern relevance and practical applications
  - Related references from historical and contemporary figures
  - Smart JSON parsing with markdown code block handling
  - Robust fallback mechanisms for API failures

### Error Handling Patterns
- Graceful degradation for API failures (static quotes fallback)
- Comprehensive logging with structured format
- User-friendly error messages with actionable suggestions
- Network timeout handling (10 seconds for external APIs)
- Markdown format error recovery with automatic fallback to plain text
- Multi-language error messages (Chinese/English)

## Troubleshooting Common Issues

### 409 Conflict Error
Occurs when bot is simultaneously configured for webhook and polling modes:
```bash
# Check webhook status
curl -X GET "https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
# Delete webhook to use polling
curl -X POST "https://api.telegram.org/bot{TOKEN}/deleteWebhook"
```

### SSL Certificate Issues with RSS
The bot automatically configures SSL context to handle certificate verification problems with RSS feeds.

### Channel Forwarding Failures
- Ensure bot is added as administrator to target channel
- Verify channel username is correct (without @ symbol)
- Check `ENABLE_RSS_FORWARDING=true` in environment variables

### OpenAI API Issues
- Verify `OPENAI_API_KEY` is valid and active
- Check `OPENAI_BASE_URL` if using custom API endpoints
- Ensure sufficient API credits/quota available
- Verify model compatibility with chosen API provider

## Test Organization

All test code is centralized in the `Test/` directory with the following structure:
- **Core functionality tests**: `test_ask_command.py`, `test_rss.py`, `test_news.py`
- **Logic tests**: `test_round_robin_logic.py`, `test_round_robin_rss.py`
- **Integration tests**: `test_channel_forwarding.py`, `test_message_send.py`, `test_webhook_integration.py`
- **Demos**: `demo_command_parsing.py`
- **Test utilities**: `run_all_tests.py` (batch test runner), `update_imports.py` (path updater)

Test files use parent directory imports: `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`