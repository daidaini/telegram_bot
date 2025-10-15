from flask import Flask
import threading
import time
import requests
import json
import os
from datetime import datetime
import logging

from config import Config
from commands import CommandHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.app = Flask(__name__)
        self.config = Config()
        self.command_handler = CommandHandler(bot_instance=self)
        self.bot_token = self.config.BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.offset = 0
        self.running = False
        
        # Register Flask routes (for health check)
        self.app.route('/')(self.index)
        self.app.route('/health')(self.health_check)
    
    def index(self):
        return "Telegram Bot is running!"
    
    def health_check(self):
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    def send_message(self, chat_id, text, parse_mode=None):
        """Send message to Telegram chat"""
        url = f"{self.api_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }

        try:
            if not text:
                logger.warning("No message to send.")
                return None
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            logger.info(f"Message sent to chat {chat_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            # 获取详细错误信息
            error_details = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    error_details = error_json.get('description', 'No description')
                    logger.error(f"Telegram API error: {error_details}")
                except:
                    error_details = str(e.response.text)
                    logger.error(f"Telegram API response: {error_details}")

            logger.error(f"Failed to send message to chat {chat_id}: {e}")

            # 如果是Markdown格式错误，尝试不使用Markdown重新发送
            if "can't parse entities" in str(error_details).lower() or "bad request" in str(e).lower():
                logger.info("Retrying without Markdown format...")
                return self.send_message(chat_id, text, parse_mode=None)

            return None

    def send_message_to_channel(self, channel_username, text, parse_mode=None):
        """Send message to Telegram channel"""
        # Remove @ if present and format correctly
        channel_name = channel_username.lstrip('@')
        chat_id = f"@{channel_name}"

        url = f"{self.api_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            logger.info(f"Message sent to channel {chat_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            # 获取详细错误信息
            error_details = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    error_details = error_json.get('description', 'No description')
                    logger.error(f"Telegram API error for channel: {error_details}")
                except:
                    error_details = str(e.response.text)
                    logger.error(f"Telegram API response for channel: {error_details}")

            logger.error(f"Failed to send message to channel {chat_id}: {e}")

            # 如果是Markdown格式错误，尝试不使用Markdown重新发送
            if "can't parse entities" in str(error_details).lower() or "bad request" in str(e).lower():
                logger.info("Retrying channel message without Markdown format...")
                return self.send_message_to_channel(channel_username, text, parse_mode=None)

            return None
    
    def get_updates(self):
        """Get updates from Telegram API using long polling"""
        url = f"{self.api_url}/getUpdates"
        params = {
            'offset': self.offset,
            'timeout': 30,  # Long polling timeout
            'allowed_updates': ['message']
        }
        
        try:
            response = requests.get(url, params=params, timeout=35)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get updates: {e}")
            return None
    
    def handle_message(self, message):
        """Handle incoming message"""
        chat_id = message['chat']['id']
        text = message.get('text', '')
        user_id = message['from']['id']
        username = message['from'].get('username', 'Unknown')

        logger.info(f"Received message from {username} (ID: {user_id}): {text}")

        # Handle commands
        if text.startswith('/'):
            command = text.lower().split()[0]
            response = self.command_handler.handle_command(command, text, user_id)
        else:
            response = "我只能理解命令。请使用 /list 查看可用命令。\n\n#invalid_input"

        self.send_message(chat_id, response)
    
    def start_polling(self):
        """Start long polling for updates"""
        logger.info("Starting Telegram bot polling...")
        self.running = True
        
        while self.running:
            try:
                updates = self.get_updates()
                
                if updates and updates.get('ok'):
                    result = updates.get('result', [])
                    
                    for update in result:
                        # Update offset to mark as processed
                        self.offset = update['update_id'] + 1
                        
                        # Handle message
                        if 'message' in update:
                            self.handle_message(update['message'])
                
                # Small delay to prevent overwhelming
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping bot...")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def stop_polling(self):
        """Stop the polling loop"""
        self.running = False
        logger.info("Bot polling stopped.")
    
    def run(self):
        """Run the Flask app and start bot polling in background"""
        if not self.bot_token:
            logger.error("未配置BOT_TOKEN!")
            return
        
        # Start polling in background thread
        polling_thread = threading.Thread(target=self.start_polling, daemon=True)
        polling_thread.start()
        
        # Run Flask app
        logger.info("Starting Flask web server...")
        self.app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    bot = TelegramBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop_polling()
        logger.info("Bot shutdown complete.")