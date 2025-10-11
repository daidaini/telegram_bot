from flask import Flask, request, abort
import threading
import time
import requests
import json
import os
import hashlib
import hmac
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
        
        # Register Flask routes
        self.app.route('/')(self.index)
        self.app.route('/health')(self.health_check)
        self.app.route('/webhook', methods=['POST'])(self.webhook)
        self.app.route('/setup_webhook')(self.setup_webhook_page)
    
    def index(self):
        return "Telegram Bot is running!"
    
    def health_check(self):
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    def send_message(self, chat_id, text, parse_mode='Markdown'):
        """Send message to Telegram chat"""
        url = f"{self.api_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            logger.info(f"Message sent to chat {chat_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message: {e}")
            return None

    def send_message_to_channel(self, channel_username, text, parse_mode='Markdown'):
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
            logger.error(f"Failed to send message to channel {chat_id}: {e}")
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
            response = "I can only understand commands. Use /list to see available commands."
        
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

    def verify_webhook_signature(self, payload, signature):
        """Verify webhook signature if secret token is set"""
        if not self.config.WEBHOOK_SECRET_TOKEN:
            return True  # Skip verification if no secret token

        try:
            # Calculate expected signature
            expected_signature = hmac.new(
                self.config.WEBHOOK_SECRET_TOKEN.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Compare signatures (remove 'sha256=' prefix if present)
            if signature.startswith('sha256='):
                signature = signature[7:]

            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Webhook signature verification error: {e}")
            return False

    def webhook(self):
        """Handle incoming webhook updates from Telegram"""
        # Get request data
        payload = request.get_data(as_text=True)
        signature = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')

        # Verify webhook signature
        if not self.verify_webhook_signature(payload, signature):
            logger.warning("Invalid webhook signature")
            abort(403)

        try:
            # Parse JSON data
            update = request.get_json()

            if not update:
                logger.warning("Empty webhook payload")
                return "ok"

            logger.info(f"Received webhook update: {update}")

            # Handle message update
            if 'message' in update:
                self.handle_message(update['message'])
            elif 'channel_post' in update:
                # Handle channel posts if needed
                logger.info("Received channel post via webhook")

            return "ok"  # Telegram expects "ok" response

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return "ok"  # Still return "ok" to avoid Telegram retrying

    def setup_webhook_page(self):
        """Webhook setup page"""
        mode = self.config.BOT_MODE
        webhook_url = self.config.WEBHOOK_URL

        if mode == 'webhook':
            return f"""
🤖 Telegram Bot Webhook Status
==================================

✅ **Bot Mode**: {mode.upper()}
📡 **Webhook URL**: {webhook_url or 'Not configured'}
🔐 **Secret Token**: {'Configured' if self.config.WEBHOOK_SECRET_TOKEN else 'Not configured'}

📋 **Current Configuration**:
• Bot Token: {'✅ Configured' if self.config.BOT_TOKEN else '❌ Missing'}
• RSS Feeds: {len(self.config.RSS_FEEDS)} configured
• Channel Forwarding: {self.config.RSS_FORWARD_TO_CHANNEL or 'Disabled'}

📡 **Webhook Setup Commands**:
```bash
# Set webhook
curl -X POST "https://api.telegram.org/bot{self.config.BOT_TOKEN}/setWebhook" \\
     -H "Content-Type: application/json" \\
     -d '{{"url": "{webhook_url or "YOUR_WEBHOOK_URL"}", "secret_token": "your_secret_token"}}'

# Get webhook info
curl -X GET "https://api.telegram.org/bot{self.config.BOT_TOKEN}/getWebhookInfo"

# Delete webhook (switch back to polling)
curl -X POST "https://api.telegram.org/bot{self.config.BOT_TOKEN}/deleteWebhook"
```

⚠️ **Important Notes**:
• Your webhook URL must be publicly accessible
• Use HTTPS for webhook URL
• Configure firewall to allow Telegram servers
• Make sure your web server is running on the specified port

🔄 **To switch to polling mode**, set BOT_MODE=polling in your .env file
        """
        else:
            return f"""
🤖 Telegram Bot Status
==================================

📡 **Bot Mode**: {mode.upper()} (Polling)
🔄 **Webhook Mode**: Not enabled

📋 **Current Configuration**:
• Bot Token: {'✅ Configured' if self.config.BOT_TOKEN else '❌ Missing'}
• RSS Feeds: {len(self.config.RSS_FEEDS)} configured
• Channel Forwarding: {self.config.RSS_FORWARD_TO_CHANNEL or 'Disabled'}

🔄 **To switch to webhook mode**, update your .env file:
```bash
BOT_MODE=webhook
WEBHOOK_URL=https://yourdomain.com/webhook
WEBHOOK_SECRET_TOKEN=your_secret_token
WEBHOOK_PORT=8443  # Your desired port
```

✅ **Bot is running in polling mode**
        """

    def setup_webhook(self):
        """Setup webhook with Telegram API"""
        if not self.config.WEBHOOK_URL:
            logger.error("WEBHOOK_URL not configured")
            return False

        try:
            url = f"{self.api_url}/setWebhook"
            data = {
                'url': self.config.WEBHOOK_URL,
                'secret_token': self.config.WEBHOOK_SECRET_TOKEN
            }

            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                logger.info(f"Webhook set successfully: {self.config.WEBHOOK_URL}")
                return True
            else:
                logger.error(f"Failed to set webhook: {result.get('description', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False

    def delete_webhook(self):
        """Delete webhook (switch back to polling)"""
        try:
            url = f"{self.api_url}/deleteWebhook"
            response = requests.post(url, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                logger.info("Webhook deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete webhook: {result.get('description', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False

    def run(self):
        """Run the Flask app with appropriate mode"""
        if not self.bot_token:
            logger.error("BOT_TOKEN not configured!")
            return

        mode = self.config.BOT_MODE
        logger.info(f"Starting Telegram bot in {mode} mode")

        if mode == 'webhook':
            # Webhook mode: setup webhook and run Flask app
            logger.info(f"Webhook URL: {self.config.WEBHOOK_URL}")

            # Setup webhook
            if self.config.WEBHOOK_URL:
                self.setup_webhook()

            # Run Flask app
            logger.info(f"Starting Flask web server on port {self.config.WEBHOOK_PORT}...")
            self.app.run(
                host='0.0.0.0',
                port=self.config.WEBHOOK_PORT,
                debug=False
            )
        else:
            # Polling mode: start polling in background thread
            logger.info("Starting long polling...")
            polling_thread = threading.Thread(target=self.start_polling, daemon=True)
            polling_thread.start()

            # Run Flask app (for health checks and webhook setup page)
            logger.info("Starting Flask web server...")
            self.app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    bot = TelegramBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop_polling()
        logger.info("Bot shutdown complete.")