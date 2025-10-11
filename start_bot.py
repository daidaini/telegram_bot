#!/usr/bin/env python3
"""
Telegram Bot Startup Script

This script provides an easy way to start the Telegram bot with proper error handling.
"""

import sys
import os
from dotenv import load_dotenv

def main():
    """Main startup function"""
    print("🤖 Starting Telegram Bot Service...")
    
    # Load environment variables
    load_dotenv()
    
    # Check required configuration
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN is required!")
        print("Please set the environment variable or add it to your .env file")
        print("Refer to .env.example for configuration format")
        sys.exit(1)
    
    # Check optional API keys and show warnings
    weather_key = os.getenv('WEATHER_API_KEY')
    if not weather_key:
        print("⚠️  Warning: WEATHER_API_KEY not configured. Weather command will not work.")
    
    news_key = os.getenv('NEWS_API_KEY')
    if not news_key:
        print("⚠️  Warning: NEWS_API_KEY not configured. News command will not work.")
    
    print("✅ Configuration validated")
    print("🚀 Starting bot server...")
    
    try:
        # Import and run the bot
        from app import TelegramBot
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()