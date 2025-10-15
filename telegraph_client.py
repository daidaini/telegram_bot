#!/usr/bin/env python3
"""
Telegraph API Client

This module provides integration with Telegraph API for creating and publishing
articles from Markdown content.
"""

import requests
import logging
import json
import re
from typing import Optional, Dict, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

class TelegraphClient:
    """Client for interacting with Telegraph API"""

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize Telegraph client

        Args:
            access_token: Telegraph access token (if None, will create a new account)
        """
        self.access_token = access_token
        self.base_url = "https://api.telegra.ph"
        self.session = requests.Session()

    def create_account(self, short_name: str = "HN AI Bot", author_name: str = "Hacker News AI Bot") -> Optional[Dict]:
        """
        Create a new Telegraph account

        Args:
            short_name: Short name for the account
            author_name: Author name for the account

        Returns:
            Account information including access token
        """
        try:
            url = f"{self.base_url}/createAccount"
            data = {
                "short_name": short_name,
                "author_name": author_name
            }

            response = self.session.post(url, json=data, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                self.access_token = result["result"]["access_token"]
                logger.info("✅ Telegraph account created successfully")
                return result["result"]
            else:
                logger.error(f"❌ Failed to create Telegraph account: {result.get('error', 'Unknown error')}")
                return None

        except Exception as e:
            logger.error(f"❌ Error creating Telegraph account: {e}")
            return None

    def create_page(self, title: str, content: str, author_name: str = None, author_url: str = None) -> Optional[Dict]:
        """
        Create a Telegraph page

        Args:
            title: Page title
            content: Page content (Markdown or HTML)
            author_name: Author name
            author_url: Author URL

        Returns:
            Page information including URL
        """
        try:
            if not self.access_token:
                logger.error("❌ No access token available")
                return None

            url = f"{self.base_url}/createPage"
            data = {
                "access_token": self.access_token,
                "title": title,
                "content": self._format_content_for_telegraph(content),
                "return_content": True
            }

            if author_name:
                data["author_name"] = author_name
            if author_url:
                data["author_url"] = author_url

            response = self.session.post(url, json=data, timeout=15)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                page_info = result["result"]
                logger.info(f"✅ Telegraph page created: {page_info['url']}")
                return page_info
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ Failed to create Telegraph page: {error_msg}")
                return None

        except Exception as e:
            logger.error(f"❌ Error creating Telegraph page: {e}")
            return None

    def _format_content_for_telegraph(self, content: str) -> str:
        """
        Format content for Telegraph API

        Args:
            content: Original content (Markdown)

        Returns:
            Formatted content suitable for Telegraph
        """
        try:
            # Convert Markdown to Telegraph format (array of nodes)
            lines = content.split('\n')
            nodes = []

            current_paragraph = []

            for line in lines:
                line = line.rstrip()

                # Handle headers
                if line.startswith('#'):
                    # Save any accumulated paragraph
                    if current_paragraph:
                        nodes.append({
                            "tag": "p",
                            "children": [' '.join(current_paragraph)]
                        })
                        current_paragraph = []

                    # Count header level
                    header_level = len(line) - len(line.lstrip('#'))
                    header_text = line.lstrip('#').strip()

                    if header_level == 1:
                        nodes.append({
                            "tag": "h3",
                            "children": [header_text]
                        })
                    elif header_level == 2:
                        nodes.append({
                            "tag": "h4",
                            "children": [header_text]
                        })
                    else:
                        nodes.append({
                            "tag": "p",
                            "children": [header_text]
                        })

                # Handle empty lines (paragraph breaks)
                elif not line:
                    if current_paragraph:
                        nodes.append({
                            "tag": "p",
                            "children": [' '.join(current_paragraph)]
                        })
                        current_paragraph = []

                # Handle list items
                elif line.strip().startswith(('•', '-', '*')):
                    # Save any accumulated paragraph
                    if current_paragraph:
                        nodes.append({
                            "tag": "p",
                            "children": [' '.join(current_paragraph)]
                        })
                        current_paragraph = []

                    list_text = line.strip().lstrip('•-* ').strip()
                    nodes.append({
                        "tag": "li",
                        "children": [list_text]
                    })

                # Handle regular text
                else:
                    current_paragraph.append(line)

            # Add final paragraph if exists
            if current_paragraph:
                nodes.append({
                    "tag": "p",
                    "children": [' '.join(current_paragraph)]
                })

            # Convert to JSON array format
            return json.dumps(nodes)

        except Exception as e:
            logger.error(f"❌ Error formatting content for Telegraph: {e}")
            # Fallback to simple format
            return json.dumps([{"tag": "p", "children": [content]}])

    def edit_page(self, path: str, title: str = None, content: str = None) -> Optional[Dict]:
        """
        Edit an existing Telegraph page

        Args:
            path: Page path
            title: New title
            content: New content

        Returns:
            Updated page information
        """
        try:
            if not self.access_token:
                logger.error("❌ No access token available")
                return None

            url = f"{self.base_url}/editPage"
            data = {
                "access_token": self.access_token,
                "path": path,
                "return_content": True
            }

            if title:
                data["title"] = title
            if content:
                data["content"] = self._format_content_for_telegraph(content)

            response = self.session.post(url, json=data, timeout=15)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                logger.info(f"✅ Telegraph page edited: {result['result']['url']}")
                return result["result"]
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ Failed to edit Telegraph page: {error_msg}")
                return None

        except Exception as e:
            logger.error(f"❌ Error editing Telegraph page: {e}")
            return None

    def get_page(self, path: str) -> Optional[Dict]:
        """
        Get page information

        Args:
            path: Page path

        Returns:
            Page information
        """
        try:
            url = f"{self.base_url}/getPage/{path}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                return result["result"]
            else:
                logger.error(f"❌ Failed to get Telegraph page: {result.get('error', 'Unknown error')}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting Telegraph page: {e}")
            return None

    def get_account_info(self) -> Optional[Dict]:
        """
        Get account information

        Returns:
            Account information
        """
        try:
            if not self.access_token:
                logger.error("❌ No access token available")
                return None

            url = f"{self.base_url}/getAccountInfo"
            data = {
                "access_token": self.access_token,
                "fields": ["short_name", "author_name", "author_url", "page_count"]
            }

            response = self.session.post(url, json=data, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                return result["result"]
            else:
                logger.error(f"❌ Failed to get account info: {result.get('error', 'Unknown error')}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting account info: {e}")
            return None

    def create_telegraph_page_from_markdown(self, title: str, markdown_content: str, author_name: str = None) -> Optional[Dict]:
        """
        Convenience method to create a Telegraph page from Markdown content

        Args:
            title: Page title
            markdown_content: Markdown content
            author_name: Author name

        Returns:
            Page information including URL
        """
        # Clean up the markdown content
        cleaned_content = self._clean_markdown_content(markdown_content)

        # Create the page
        return self.create_page(
            title=title,
            content=cleaned_content,
            author_name=author_name or "Hacker News AI Bot"
        )

    def _clean_markdown_content(self, content: str) -> str:
        """
        Clean and optimize Markdown content for Telegraph

        Args:
            content: Original Markdown content

        Returns:
            Cleaned Markdown content
        """
        try:
            # Remove excessive newlines
            content = re.sub(r'\n{3,}', '\n\n', content)

            # Fix common Telegram markdown issues
            # Remove telegram-style bold/italic that might not work well
            content = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', content)

            # Ensure proper list formatting
            content = re.sub(r'^[-*•]\s*', '• ', content, flags=re.MULTILINE)

            # Clean up any remaining formatting issues
            content = content.strip()

            return content

        except Exception as e:
            logger.error(f"❌ Error cleaning Markdown content: {e}")
            return content

def create_telegraph_client(access_token: Optional[str] = None) -> TelegraphClient:
    """
    Create a configured Telegraph client

    Args:
        access_token: Optional access token

    Returns:
        TelegraphClient instance
    """
    return TelegraphClient(access_token=access_token)