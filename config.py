import os
import json
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    """Configuration class for Telegram Bot"""
    
    # Bot Token from environment variable or .env file
    BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # News API key (GNews)
    NEWS_API_KEY: str = os.getenv('GNEWS_API_KEY', '')
    NEWS_API_URL: str = 'https://gnews.io/api/v4/top-headlines'
    
    # Quote API settings
    QUOTE_API_URL: str = 'https://api.quotable.io/random'
    
    # Default city for weather (legacy)
    DEFAULT_CITY: str = 'Beijing'

    # Default country/region for news (GNews uses country codes)
    DEFAULT_NEWS_COUNTRY: str = 'cn'
    # Default language for news
    DEFAULT_NEWS_LANGUAGE: str = 'zh'

    # RSS Feed Configuration
    RSS_FEEDS: list = None
    RSS_CACHE_FILE: str = 'rss_cache.json'
    MAX_ARTICLES_PER_FEED: int = 3

    # Channel Forwarding Configuration
    RSS_FORWARD_TO_CHANNEL: str = ''
    ENABLE_RSS_FORWARDING: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.BOT_TOKEN:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is required! "
                "Set it as environment variable or in .env file"
            )

        # Initialize RSS feeds from environment variable or use defaults
        if self.RSS_FEEDS is None:
            rss_feeds_env = os.getenv('RSS_FEEDS')
            if rss_feeds_env:
                try:
                    self.RSS_FEEDS = json.loads(rss_feeds_env)
                except json.JSONDecodeError:
                    print("Warning: RSS_FEEDS environment variable is not valid JSON. Using default feeds.")
                    self.RSS_FEEDS = self._get_default_rss_feeds()
            else:
                self.RSS_FEEDS = self._get_default_rss_feeds()

        # Initialize channel forwarding settings
        self.RSS_FORWARD_TO_CHANNEL = os.getenv('RSS_FORWARD_TO_CHANNEL', '')
        self.ENABLE_RSS_FORWARDING = os.getenv('ENABLE_RSS_FORWARDING', 'false').lower() == 'true'

    def _get_default_rss_feeds(self):
        """Get default RSS feeds"""
        return [
            {
                "name": "BBC News",
                "url": "http://feeds.bbci.co.uk/news/rss.xml",
                "category": "general"
            },
            {
                "name": "Reuters",
                "url": "https://www.reuters.com/rssFeed/worldNews",
                "category": "world"
            },
            {
                "name": "CNN",
                "url": "http://rss.cnn.com/rss/edition.rss",
                "category": "general"
            }
        ]
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables"""
        return cls()