import requests
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class CommandHandler:
    def __init__(self):
        self.config = Config()
        self.commands = {
            '/list': self.list_commands,
            '/help': self.list_commands,
            '/weather': self.get_weather,
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

🌤️ *Weather Information:*
• `/weather [city]` - Get current weather for a city
  Example: `/weather Beijing` or `/weather London`

📰 *News Headlines:*
• `/news [country]` - Get latest news headlines with summaries
  Example: `/news cn` (China) or `/news us` (USA)
• `/news [topic]` - Get news about specific topic
  Example: `/news technology` or `/news sports`

💭 *Inspirational Quotes:*
• `/quote` - Get a random inspirational quote

*Tips:*
• Use city names in English for weather
• Use country codes for news (cn, us, uk, etc.) or topic keywords
• All commands are case-insensitive
• News includes summaries and original source links
        """
        return help_text.strip()
    
    def get_weather(self, command, full_message, user_id):
        """Get weather information for a city"""
        try:
            # Parse city from command
            parts = full_message.strip().split()
            if len(parts) > 1:
                city = ' '.join(parts[1:])
            else:
                city = self.config.DEFAULT_CITY
            
            if not self.config.WEATHER_API_KEY:
                return "⚠️ Weather API key not configured. Please set WEATHER_API_KEY environment variable."
            
            # Make API request
            params = {
                'q': city,
                'appid': self.config.WEATHER_API_KEY,
                'units': 'metric',  # Celsius
                'lang': 'en'
            }
            
            response = requests.get(self.config.WEATHER_API_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('cod') != 200:
                return f"❌ Weather information not found for '{city}'. Please check the city name."
            
            # Extract weather information
            weather = data['weather'][0]
            main = data['main']
            wind = data.get('wind', {})
            
            # Format weather response
            weather_text = f"""
🌤️ *Weather in {data['name']}, {data['sys']['country']}*

🌡️ **Temperature:** {main['temp']}°C (feels like {main['feels_like']}°C)
☁️ **Condition:** {weather['main']} - {weather['description'].title()}
💧 **Humidity:** {main['humidity']}%
🌬️ **Wind:** {wind.get('speed', 0)} m/s
📊 **Pressure:** {main['pressure']} hPa

🕐 *Updated at:* {datetime.now().strftime('%H:%M:%S')}
            """.strip()
            
            return weather_text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Weather API error: {e}")
            return "❌ Failed to fetch weather information. Please try again later."
        except KeyError as e:
            logger.error(f"Weather data parsing error: {e}")
            return "❌ Invalid weather data received."
        except Exception as e:
            logger.error(f"Unexpected error in weather command: {e}")
            return "❌ An error occurred while fetching weather information."
    
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