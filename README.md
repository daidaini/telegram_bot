# Telegram Bot Service

A Flask-based Telegram bot service that provides various information services using long polling mode.

## Features

### Available Commands

1. **/list** - Display all available commands and their descriptions
2. **/rss_news** - Get latest news from RSS feeds
   - Fetches from multiple configurable RSS sources
   - Automatic deduplication prevents showing same articles
   - Uses feedparser library
3. **/news [country|topic]** - Get latest news headlines with summaries
   - Example: `/news cn` (China) or `/news us` (USA)
   - Example: `/news technology` or `/news sports` (topics)
   - Uses GNews API with summaries and original links
4. **/quote** - Get a random inspirational quote
   - Uses Quotable API

## Architecture

- **Framework**: Flask 2.3.3
- **Communication**: Telegram Bot API with long polling
- **External APIs**: GNews, Quotable
- **RSS Feeds**: Configurable RSS sources with deduplication
- **Configuration**: Environment variables with .env file support

## Installation

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd telegram_bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 3. Required API Keys

#### Telegram Bot Token
1. Create a bot with [@BotFather](https://t.me/botfather) on Telegram
2. Get your bot token
3. Add to `.env`: `TELEGRAM_BOT_TOKEN=your_bot_token_here`

#### RSS Feed Configuration (Optional)
The bot comes with default RSS feeds (BBC, Reuters, CNN), but you can configure custom feeds:

1. Edit your `.env` file
2. Add custom RSS feeds as JSON:
   ```
   RSS_FEEDS=[{"name": "Feed Name", "url": "https://example.com/rss.xml", "category": "general"}]
   ```
3. Set maximum articles per feed: `MAX_ARTICLES_PER_FEED=3`

#### News API Key (Optional)
1. Sign up at [GNews](https://gnews.io/)
2. Get your free API key
3. Add to `.env`: `GNEWS_API_KEY=your_gnews_api_key_here`

## Usage

### Testing the Features

Before running the bot, you can test the functionality:

```bash
# Test GNews integration
python test_news.py

# Test RSS feeds functionality
python test_rss.py
```

These scripts test various commands without requiring Telegram integration.

### Running the Bot

```bash
python app.py
```

The bot will:
1. Start a Flask web server on port 5000
2. Begin polling Telegram for updates in the background
3. Respond to commands from users

### Health Check

The bot provides a health check endpoint:
- **URL**: `http://localhost:5000/health`
- **Response**: `{"status": "healthy", "timestamp": "..."}`

## Project Structure

```
telegram_bot/
├── app.py              # Main Flask application and bot logic
├── config.py           # Configuration management
├── commands.py         # Command handlers for bot functionality
├── rss_handler.py      # RSS feed fetching and deduplication logic
├── test_news.py        # Test script for GNews functionality
├── test_rss.py         # Test script for RSS functionality
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── README.md          # This documentation
```

## API Integration Details

### RSS Feeds
- **Library**: feedparser
- **Sources**: Configurable RSS feeds (default: BBC, Reuters, CNN)
- **Features**: Automatic deduplication, caching, configurable limits
- **Cache**: Tracks seen articles for 7 days to prevent duplicates

### News API
- **Provider**: GNews
- **Endpoint**: Top headlines and search
- **Features**: Latest news with summaries, original links, country/topic filtering
- **Limit**: 5 articles per request
- **Languages**: Supports multiple languages including Chinese (zh)

### Quote API
- **Provider**: Quotable
- **Endpoint**: Random quotes
- **Features**: Inspirational and educational quotes
- **Fallback**: Static quote if API is unavailable

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram bot token from @BotFather |
| `GNEWS_API_KEY` | Optional | - | GNews API key |
| `RSS_FEEDS` | Optional | Default feeds | JSON array of RSS feed configurations |
| `MAX_ARTICLES_PER_FEED` | No | 3 | Maximum articles to fetch per RSS feed |
| `DEFAULT_NEWS_COUNTRY` | No | cn | Default country for news queries |
| `DEFAULT_NEWS_LANGUAGE` | No | zh | Default language for news (zh=Chinese) |

## Error Handling

The bot includes comprehensive error handling:

1. **API Failures**: Graceful fallbacks with user-friendly messages
2. **Invalid Commands**: Clear error messages with help suggestions
3. **Network Issues**: Automatic retries with timeout handling
4. **Data Parsing**: Robust parsing with validation

## Logging

The bot uses Python's logging module with:
- **Level**: INFO
- **Format**: `timestamp - name - level - message`
- **Output**: Console

## Security Considerations

1. **API Keys**: Store in environment variables, never commit to version control
2. **Input Validation**: All user inputs are validated and sanitized
3. **Error Messages**: Generic error messages to avoid information leakage
4. **Rate Limiting**: Inherent rate limiting from external APIs

## Deployment

### Development
```bash
python app.py
```

### Production (using Gunicorn)
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

## Troubleshooting

### Common Issues

1. **Bot Token Not Working**
   - Verify token with @BotFather
   - Check for extra spaces or characters
   - Ensure bot is enabled

2. **RSS Feed Errors**
   - Check RSS feed URLs are accessible
   - Verify RSS feed format is valid
   - Ensure network connectivity to feed sources

3. **News API Errors**
   - Verify GNews API key validity
   - Check country code format (2-letter codes) or topic keywords
   - Ensure API quota available

4. **Connection Issues**
   - Check internet connectivity
   - Verify firewall settings
   - Ensure ports are open

### Debug Mode

Enable debug logging by modifying `app.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is licensed under the MIT License.