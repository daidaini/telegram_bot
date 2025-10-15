#!/usr/bin/env python3
"""
Hacker News API Handler for AI-related articles

This module handles fetching AI-related articles from Hacker News,
fetching their content using MCP fetch server, and analyzing with AI.
"""

import requests
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse
import time
from content_fetcher import ContentFetcher

logger = logging.getLogger(__name__)

class HackerNewsHandler:
    """Handles Hacker News API integration and AI article processing"""

    def __init__(self):
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.ai_keywords = [
            'AI', 'artificial intelligence', 'machine learning', 'deep learning',
            'neural network', 'GPT', 'LLM', 'large language model', 'ChatGPT',
            'OpenAI', 'transformer', 'automation', 'robotics', 'computer vision',
            'natural language processing', 'NLP', 'data science', 'algorithm'
        ]
        # Initialize content fetcher
        self.content_fetcher = ContentFetcher()

    def get_new_stories(self, limit: int = 500) -> List[int]:
        """Get latest story IDs from Hacker News"""
        try:
            url = f"{self.base_url}/newstories.json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            story_ids = response.json()
            return story_ids[:limit]
        except Exception as e:
            logger.error(f"Error fetching new stories: {e}")
            return []

    def get_story_details(self, story_id: int) -> Optional[Dict]:
        """Get detailed information about a specific story"""
        try:
            url = f"{self.base_url}/item/{story_id}.json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching story {story_id}: {e}")
            return None

    def is_today(self, timestamp: int) -> bool:
        """Check if timestamp is from today"""
        story_date = datetime.fromtimestamp(timestamp)
        today = datetime.now().date()
        return story_date.date() == today

    def is_ai_related(self, text: str) -> bool:
        """Check if text contains AI-related keywords"""
        if not text:
            return False

        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.ai_keywords)

    def find_ai_article_today(self) -> Optional[Dict]:
        """Find the latest AI-related article from today"""
        logger.info("Searching for AI-related articles from today...")

        # Get latest stories
        story_ids = self.get_new_stories(200)
        if not story_ids:
            logger.warning("No stories fetched from Hacker News")
            return None

        logger.info(f"Checking {len(story_ids)} stories for AI-related content...")

        # Check each story
        for story_id in story_ids:
            story = self.get_story_details(story_id)
            if not story:
                continue

            # Skip if not from today
            if not self.is_today(story.get('time', 0)):
                continue

            # Skip if not a story (might be a comment or job)
            if story.get('type') != 'story':
                continue

            # Check if AI-related
            title = story.get('title', '')
            text = story.get('text', '')

            if self.is_ai_related(title) or self.is_ai_related(text):
                logger.info(f"Found AI article: {title[:50]}...")
                return story

        logger.info("No AI-related articles found from today")
        return None

    def fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch article content using BeautifulSoup-based content fetcher"""
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                logger.error(f"Invalid URL: {url}")
                return None

            logger.info(f"Fetching content from: {url}")

            # Use the content fetcher with intelligent extraction
            content = self.content_fetcher.fetch_content(
                url=url,
                max_length=15000  # Allow sufficient content for AI analysis
            )

            if content:
                logger.info(f"✅ Successfully extracted {len(content)} characters")
                return content
            else:
                logger.warning("Content extraction returned empty result")
                return None

        except Exception as e:
            logger.error(f"Error fetching article content: {e}")
            return None

    def analyze_article_with_ai(self, article_data: Dict, content: str, openai_client, model: str) -> Optional[str]:
        """Analyze article content using AI"""
        try:
            title = article_data.get('title', 'No title')
            url = article_data.get('url', '')

            system_prompt = """你是一个专业的AI领域分析师，擅长分析技术文章并提供深度见解。

请分析以下AI相关的文章，并提供：

1. **核心内容总结** - 用2-3句话概括文章的核心观点和主要内容
2. **技术要点分析** - 提取文章中涉及的关键技术、方法或创新点
3. **行业影响评估** - 分析这项技术或观点对AI行业可能产生的影响
4. **个人观点** - 提供你对这个话题的独立见解和评价

请用中文回复，保持专业、客观的语调，避免过于技术性的术语，让广大技术爱好者都能理解。

文章内容如下："""

            user_message = f"""
标题：{title}

链接：{url}

内容：
{content}
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            response = openai_client.chat_completion(messages, model)
            return response

        except Exception as e:
            logger.error(f"Error analyzing article with AI: {e}")
            return None

    def format_analysis_for_telegram(self, article_data: Dict, analysis: str) -> str:
        """Format the analysis for Telegram message"""
        title = article_data.get('title', 'No title')
        url = article_data.get('url', '')
        score = article_data.get('score', 0)
        comments = article_data.get('descendants', 0)

        message = f"""🤖 *Hacker News AI 文章分析*

📰 **标题：** {title}

🔗 **链接：** [阅读原文]({url})

📊 **Hacker Stats：** {score} points | {comments} comments

📝 **AI 分析结果：**

{analysis}

---
*🤖 由 HN AI 机器人自动分析*
*📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}*"""

        return message

    def format_analysis_for_channel(self, article_data: Dict, analysis: str, channel_name: str) -> str:
        """Format the analysis for Telegram channel posting"""
        title = article_data.get('title', 'No title')
        url = article_data.get('url', '')
        score = article_data.get('score', 0)

        message = f"""🤖 @{channel_name} Hacker News AI 精选

🔥 **今日热文：** {title}

📊 Hacker News: {score} points

📝 **深度分析：**

{analysis}

🔗 [阅读原文]({url})

---
*🤖 AI 自动分析 | {datetime.now().strftime('%Y-%m-%d %H:%M')}*"""

        return message