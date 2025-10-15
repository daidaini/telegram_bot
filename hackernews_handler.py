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
from telegraph_client import TelegraphClient, create_telegraph_client

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
        # Initialize Telegraph client
        self.telegraph_client = create_telegraph_client()

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

            system_prompt = """# 角色
你是一位资深的科技新闻分析师和科普作者。你拥有：
- **身份**：在科技媒体行业工作10年以上，对AI、互联网、硬件、软件等领域有深入理解
- **能力**：
  - 快速抓取科技新闻的核心信息和技术要点
  - 洞察技术发展趋势和商业影响
  - 将复杂的技术概念转化为普通人能理解的语言
  - 识别新闻中的炒作与实质，保持客观中立的分析视角

# 任务
当用户提供一篇科技新闻（链接、标题或全文）时，你需要：

**目标**：
1. 提炼新闻的核心信息和关键技术点
2. 分析这条新闻的技术意义、商业影响和行业趋势
3. 用通俗易懂的语言解释相关技术概念
4. 给出客观的评价和未来展望

**约束**：
- 保持客观中立，避免过度炒作或贬低
- 区分事实与观点，明确标注推测性内容
- 如涉及专业术语，必须提供通俗解释
- 如信息不足，明确指出而非臆测

**流程**：
1. **信息提取**：总结新闻的5W1H（何人、何事、何时、何地、为何、如何）
2. **技术解析**：解释涉及的核心技术和原理
3. **影响分析**：分析对行业、用户、竞争格局的影响
4. **趋势洞察**：结合行业背景，预测可能的发展方向
5. **关键评价**：给出你的专业判断和建议

# 输出要求

**格式**：
```
## 📰 新闻概要
[用2-3句话概括新闻核心内容]

## 🔑 关键信息
- **主角**：[涉及的公司/人物/产品]
- **事件**：[发生了什么]
- **时间**：[何时发生]
- **背景**：[为什么重要]

## 🔬 技术解析
[解释涉及的核心技术，用类比或例子帮助理解]

## 📊 影响分析
- **对行业**：[对整个行业的影响]
- **对用户**：[对普通用户的影响]
- **对竞争**：[对竞争格局的影响]

## 🔮 趋势洞察
[基于这条新闻，分析可能的发展趋势]

## 💭 专业评价
[你的客观评价：这是真突破还是营销炒作？值得关注的点是什么？]
```
"""

            user_message = f"""
标题：{title}
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

        message = f"""*Hacker News 文章分析*

📰 **标题：** {title}

🔗 **链接：** [阅读原文]({url})

{analysis}
"""

        return message

    def publish_to_telegraph(self, title: str, analysis: str, article_url: str) -> Optional[str]:
        """
        Publish analysis to Telegraph

        Args:
            title: Article title
            analysis: AI analysis result (Markdown)
            article_url: Original article URL

        Returns:
            Telegraph URL or None if failed
        """
        try:
            # Ensure Telegraph client has access token
            if not self.telegraph_client.access_token:
                logger.info("Creating Telegraph account...")
                account = self.telegraph_client.create_account(
                    short_name="HN_AI_Bot",
                    author_name="Hacker News Bot"
                )
                if not account:
                    logger.error("Failed to create Telegraph account")
                    return None

            # Create content for Telegraph page
            telegraph_content = f"""

{analysis}

---

**Original Article**: {article_url}
"""

            # Create Telegraph page
            page_info = self.telegraph_client.create_telegraph_page_from_markdown(
                title=f"{title}",
                markdown_content=telegraph_content,
                author_name="Hacker News Bot"
            )

            if page_info:
                telegraph_url = page_info.get('url')
                logger.info(f"✅ Successfully published to Telegraph: {telegraph_url}")
                return telegraph_url
            else:
                logger.error("Failed to create Telegraph page")
                return None

        except Exception as e:
            logger.error(f"Error publishing to Telegraph: {e}")
            return None

    def format_analysis_for_channel(self, article_data: Dict, analysis: str, channel_name: str, telegraph_url: str = None) -> str:
        """Format the analysis for Telegram channel posting"""
        if telegraph_url:
            # Only send Telegraph link
            message = telegraph_url
        else:
            # Fallback if Telegraph URL is not available
            message = ""

        return message