import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    """Configuration class for Telegram Bot"""
    
    # Bot Token from environment variable or .env file
    BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # Weather API key (OpenWeatherMap)
    WEATHER_API_KEY: str = os.getenv('WEATHER_API_KEY', '')
    WEATHER_API_URL: str = 'http://api.openweathermap.org/data/2.5/weather'
    
    # News API key (GNews)
    NEWS_API_KEY: str = os.getenv('GNEWS_API_KEY', '')
    NEWS_API_URL: str = 'https://gnews.io/api/v4/top-headlines'
    
    # Quote API settings
    QUOTE_API_URL: str = 'https://api.quotable.io/random'
    
    # Default city for weather
    DEFAULT_CITY: str = 'Beijing'
    
    # Default country/region for news (GNews uses country codes)
    DEFAULT_NEWS_COUNTRY: str = 'cn'
    # Default language for news
    DEFAULT_NEWS_LANGUAGE: str = 'zh'
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.BOT_TOKEN:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is required! "
                "Set it as environment variable or in .env file"
            )
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables"""
        return cls()