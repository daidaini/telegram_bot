#!/usr/bin/env python3
"""
Telegram Bot Webhook Setup Script
This script helps set up and manage Telegram webhooks
"""

import os
import sys
import argparse
import requests
from dotenv import load_dotenv

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

class WebhookManager:
    def __init__(self):
        load_dotenv()
        self.config = Config()
        self.bot_token = self.config.BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def get_webhook_info(self):
        """Get current webhook information"""
        try:
            url = f"{self.api_url}/getWebhookInfo"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                return result.get('result', {})
            else:
                print(f"❌ Error getting webhook info: {result.get('description', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"❌ Error getting webhook info: {e}")
            return None

    def set_webhook(self, webhook_url, secret_token=None):
        """Set webhook for the bot"""
        try:
            url = f"{self.api_url}/setWebhook"
            data = {'url': webhook_url}

            if secret_token:
                data['secret_token'] = secret_token

            print(f"📡 Setting webhook to: {webhook_url}")
            if secret_token:
                print(f"🔐 Using secret token: {secret_token[:8]}...")

            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                print("✅ Webhook set successfully!")
                webhook_info = result.get('result', {})
                if webhook_info.get('url'):
                    print(f"   📡 URL: {webhook_info.get('url')}")
                if webhook_info.get('has_custom_certificate'):
                    print("   🔒 Custom certificate: Yes")
                if webhook_info.get('pending_update_count'):
                    print(f"   ⏳ Pending updates: {webhook_info.get('pending_update_count')}")
                return True
            else:
                print(f"❌ Failed to set webhook: {result.get('description', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"❌ Error setting webhook: {e}")
            return False

    def delete_webhook(self):
        """Delete webhook (switch back to polling)"""
        try:
            url = f"{self.api_url}/deleteWebhook"
            response = requests.post(url, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get('ok'):
                print("✅ Webhook deleted successfully!")
                print("🔄 Bot will now use polling mode")
                return True
            else:
                print(f"❌ Failed to delete webhook: {result.get('description', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"❌ Error deleting webhook: {e}")
            return False

    def test_webhook(self, webhook_url):
        """Test webhook endpoint"""
        try:
            print(f"🧪 Testing webhook endpoint: {webhook_url}")

            # Create test update
            test_update = {
                "update_id": 123456789,
                "message": {
                    "message_id": 123,
                    "from": {
                        "id": 987654321,
                        "is_bot": False,
                        "first_name": "Test",
                        "username": "test_user"
                    },
                    "chat": {
                        "id": 987654321,
                        "first_name": "Test",
                        "username": "test_user",
                        "type": "private"
                    },
                    "date": 1640995200,
                    "text": "Test webhook message"
                }
            }

            response = requests.post(
                webhook_url,
                json=test_update,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 200:
                print("✅ Webhook endpoint is accessible!")
                print(f"   📡 Response: {response.text}")
                return True
            else:
                print(f"❌ Webhook endpoint returned status {response.status_code}")
                print(f"   📄 Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error testing webhook: {e}")
            return False

    def check_ssl_certificate(self, webhook_url):
        """Check SSL certificate of webhook URL"""
        try:
            print(f"🔒 Checking SSL certificate for: {webhook_url}")

            from urllib.parse import urlparse
            import ssl
            import socket

            parsed_url = urlparse(webhook_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or 443

            context = ssl.create_default_context()

            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

                    print("✅ SSL certificate is valid!")
                    print(f"   📜 Subject: {cert.get('subject', 'Unknown')}")
                    print(f"   🏢 Issuer: {cert.get('issuer', 'Unknown')}")
                    print(f"   📅 Expires: {cert.get('notAfter', 'Unknown')}")
                    return True

        except Exception as e:
            print(f"❌ SSL certificate check failed: {e}")
            print("⚠️ Make sure your webhook URL has a valid SSL certificate")
            return False

def main():
    parser = argparse.ArgumentParser(description='Telegram Bot Webhook Manager')
    parser.add_argument('--action', choices=['info', 'set', 'delete', 'test', 'check-ssl'],
                       help='Action to perform', required=True)
    parser.add_argument('--url', help='Webhook URL (required for set action)')
    parser.add_argument('--secret', help='Secret token for webhook security')

    args = parser.parse_args()

    print("🤖 Telegram Bot Webhook Manager")
    print("=" * 40)

    manager = WebhookManager()

    if not manager.bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        print("Please add your bot token to the .env file")
        return

    if args.action == 'info':
        print("📋 Getting current webhook information...")
        webhook_info = manager.get_webhook_info()
        if webhook_info:
            print("Current Webhook Configuration:")
            print(f"   📡 URL: {webhook_info.get('url', 'Not set')}")
            print(f"   🎯 IP Addresses: {webhook_info.get('ip_address', 'Any')}")
            print(f"   🔒 Custom Certificate: {'Yes' if webhook_info.get('has_custom_certificate') else 'No'}")
            print(f"   📝 Allowed Updates: {webhook_info.get('allowed_updates', 'All')}")
            print(f"   ⏳ Pending Updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"   📅 Last Error Date: {webhook_info.get('last_error_date', 'None')}")
            print(f"   ❌ Last Error Message: {webhook_info.get('last_error_message', 'None')}")

    elif args.action == 'set':
        if not args.url:
            print("❌ --url is required for set action")
            print("Example: python setup_webhook.py --action set --url https://yourdomain.com/webhook")
            return

        # Check SSL certificate first
        if not manager.check_ssl_certificate(args.url):
            print("❌ SSL certificate check failed. Please fix SSL issues before proceeding.")
            return

        # Test webhook endpoint
        if not manager.test_webhook(args.url):
            print("❌ Webhook endpoint test failed. Please check if the URL is accessible.")
            return

        # Set webhook
        if manager.set_webhook(args.url, args.secret):
            print("\n🎉 Webhook setup complete!")
            print("Your bot will now receive updates via webhook.")

    elif args.action == 'delete':
        if manager.delete_webhook():
            print("\n🎉 Webhook deleted successfully!")
            print("Your bot will now use polling mode.")

    elif args.action == 'test':
        if not args.url:
            print("❌ --url is required for test action")
            print("Example: python setup_webhook.py --action test --url https://yourdomain.com/webhook")
            return

        manager.test_webhook(args.url)

    elif args.action == 'check-ssl':
        if not args.url:
            print("❌ --url is required for check-ssl action")
            print("Example: python setup_webhook.py --action check-ssl --url https://yourdomain.com/webhook")
            return

        manager.check_ssl_certificate(args.url)

if __name__ == '__main__':
    main()