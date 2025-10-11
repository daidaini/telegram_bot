import requests
import logging
from datetime import datetime
from config import Config
from rss_handler import RSSHandler

logger = logging.getLogger(__name__)

class CommandHandler:
    def __init__(self, bot_instance=None):
        self.config = Config()
        self.rss_handler = RSSHandler(self.config)
        self.bot = bot_instance  # Reference to bot instance for channel posting
        self.commands = {
            '/list': self.list_commands,
            '/help': self.list_commands,
            '/rss_news': self.get_rss_news,
            '/news': self.get_news,
            '/quote': self.get_quote
        }
    
    def list_commands(self, command, full_message, user_id):
        """List all available commands"""
        help_text = """
🤖 *Telegram Bot Commands:*

📋 *Information Commands:*
• `/list` - Show all available commands
• `/help` - Show this help message

📡 *RSS News Feeds:*
• `/rss_news` - Get latest news from RSS feeds
  Fetches from multiple configurable RSS sources
  (Can auto-forward to configured channel)

📰 *News Headlines:*
• `/news [country]` - Get latest news headlines with summaries
  Example: `/news cn` (China) or `/news us` (USA)
• `/news [topic]` - Get news about specific topic
  Example: `/news technology` or `/news sports`

💭 *Inspirational Quotes:*
• `/quote` - Get a random inspirational quote

*Tips:*
• RSS feeds are automatically deduplicated to prevent duplicates
• Use country codes for news (cn, us, uk, etc.) or topic keywords
• All commands are case-insensitive
• RSS news and GNews both include summaries and original source links
        """
        return help_text.strip()
    
    def get_rss_news(self, command, full_message, user_id):
        """Get latest news from RSS feeds with optional channel forwarding"""
        try:
            logger.info(f"Fetching RSS news for user {user_id}")

            # Get latest articles from RSS feeds
            articles = self.rss_handler.get_latest_news(max_total=10)

            # Format user response
            if not articles:
                user_response = """
📡 *RSS News Update*

🔍 *No new articles found*

This means you've already seen all recent articles, or there are no new articles from your RSS feeds.

*Configured RSS sources:* {} feeds
*Next check:* Try again in a few minutes for new content

🕐 *Updated at:* {}
                """.format(
                    len(self.config.RSS_FEEDS),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ).strip()
            else:
                # Format RSS news response for user
                user_response = f"📡 *Latest RSS News*\n\n"
                user_response += f"📊 *Found {len(articles)} new articles*\n\n"

                for i, article in enumerate(articles, 1):
                    title = article.get('title', 'No title')
                    summary = article.get('summary', '')
                    source = article.get('source', 'Unknown')
                    link = article.get('link', '')
                    category = article.get('category', 'general')
                    published = article.get('published', '')

                    user_response += f"{i}. **{title}**\n"
                    if summary:
                        user_response += f"   📝 *{summary}*\n"
                    user_response += f"   📺 *Source: {source} ({category})*\n"
                    if link:
                        user_response += f"   🔗 [Read full article]({link})\n"
                    if published:
                        user_response += f"   📅 *{published}*\n"
                    user_response += "\n"

                user_response += f"🕐 *Updated at:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                user_response += f"\n🔄 *Articles are deduplicated across all feeds*"

            # Handle channel forwarding if enabled
            if self.config.ENABLE_RSS_FORWARDING and self.config.RSS_FORWARD_TO_CHANNEL and self.bot:
                try:
                    channel_message = self.rss_handler.format_for_channel(
                        articles,
                        self.config.RSS_FORWARD_TO_CHANNEL
                    )

                    logger.info(f"Forwarding RSS news to channel: @{self.config.RSS_FORWARD_TO_CHANNEL}")
                    forward_result = self.bot.send_message_to_channel(
                        self.config.RSS_FORWARD_TO_CHANNEL,
                        channel_message
                    )

                    if forward_result:
                        logger.info(f"Successfully forwarded RSS news to channel @{self.config.RSS_FORWARD_TO_CHANNEL}")
                        user_response += f"\n\n✅ *Content also forwarded to @{self.config.RSS_FORWARD_TO_CHANNEL}*"
                    else:
                        logger.warning(f"Failed to forward RSS news to channel @{self.config.RSS_FORWARD_TO_CHANNEL}")
                        user_response += f"\n\n⚠️ *Channel forwarding failed*"

                except Exception as e:
                    logger.error(f"Error forwarding RSS news to channel: {e}")
                    user_response += f"\n\n⚠️ *Channel forwarding error:* {str(e)}"

            return user_response.strip()

        except Exception as e:
            logger.error(f"Unexpected error in RSS news command: {e}")
            return "❌ An error occurred while fetching RSS news. Please try again later."
    
    def get_news(self, command, full_message, user_id):
        """Get latest news headlines with summaries using GNews API"""
        try:
            # Parse country/topic from command
            parts = full_message.strip().split()
            if len(parts) > 1:
                query = parts[1].lower()
            else:
                query = self.config.DEFAULT_NEWS_COUNTRY

            if not self.config.NEWS_API_KEY:
                return "⚠️ GNews API key not configured. Please set GNEWS_API_KEY environment variable."

            # Determine if query is a country code or topic
            country_codes = ['cn', 'us', 'uk', 'ca', 'au', 'in', 'de', 'fr', 'it', 'jp', 'kr', 'ru', 'br', 'mx']

            # Make API request
            params = {
                'apikey': self.config.NEWS_API_KEY,
                'lang': self.config.DEFAULT_NEWS_LANGUAGE,
                'max': 5,  # Number of articles
                'expand': 'content'  # Include full content for better summaries
            }

            if query in country_codes:
                # Query is a country code
                params['country'] = query.upper()
                location_name = query.upper()
            else:
                # Query is a topic/keyword
                params['q'] = query
                location_name = query

            response = requests.get(self.config.NEWS_API_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'articles' not in data:
                return f"❌ Failed to fetch news for '{location_name}'. Please try a different query."

            articles = data.get('articles', [])

            if not articles:
                return f"📰 No news found for '{location_name}'."

            # Format news response
            news_text = f"📰 *Latest News Headlines ({location_name})*\n\n"

            for i, article in enumerate(articles, 1):
                title = article.get('title', 'No title')
                description = article.get('description', '')
                source = article.get('source', {}).get('name', 'Unknown')
                url = article.get('url', '')
                published_date = article.get('publishedAt', '')

                # Create summary from description, truncate if too long
                summary = description[:200] + "..." if len(description) > 200 else description
                if not summary:
                    summary = "No summary available"

                news_text += f"{i}. **{title}**\n"
                news_text += f"   📝 *{summary}*\n"
                news_text += f"   📺 *Source: {source}*\n"
                if url:
                    news_text += f"   🔗 [Read full article]({url})\n"
                if published_date:
                    # Format date nicely
                    try:
                        pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                        formatted_date = pub_date.strftime('%Y-%m-%d %H:%M')
                        news_text += f"   📅 *{formatted_date}*\n"
                    except:
                        pass
                news_text += "\n"

            news_text += f"🕐 *Updated at:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            news_text += f"\n📊 *Source: GNews.io*"

            return news_text.strip()

        except requests.exceptions.RequestException as e:
            logger.error(f"GNews API error: {e}")
            return "❌ Failed to fetch news. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error in news command: {e}")
            return "❌ An error occurred while fetching news."
    
    def get_quote(self, command, full_message, user_id):
        """Get a random inspirational quote"""
        try:
            # Make API request
            response = requests.get(self.config.QUOTE_API_URL, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            quote_text = data.get('content', '')
            author = data.get('author', 'Unknown')
            
            if not quote_text:
                return "❌ Failed to fetch a quote. Please try again."
            
            # Format quote response
            formatted_quote = f"""
💭 **Quote of the Day:**

_"{quote_text}"_

🖋️ — {author}

🕐 *{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
            """.strip()
            
            return formatted_quote
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Quote API error: {e}")
            # Fallback to a static quote if API fails
            return """
💭 **Quote of the Day:**

_"The only way to do great work is to love what you do."_

🖋️ — Steve Jobs

🕐 *Fallback quote - API unavailable*
            """.strip()
        except Exception as e:
            logger.error(f"Unexpected error in quote command: {e}")
            return "❌ An error occurred while fetching a quote."
    
    def handle_command(self, command, full_message, user_id):
        """Handle incoming commands"""
        command = command.lower()
        
        if command in self.commands:
            try:
                return self.commands[command](command, full_message, user_id)
            except Exception as e:
                logger.error(f"Error executing command {command}: {e}")
                return f"❌ An error occurred while processing the command '{command}'."
        else:
            return f"❌ Unknown command '{command}'. Use /list to see available commands."