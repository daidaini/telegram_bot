import feedparser
import json
import hashlib
import logging
import ssl
import re
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from config import Config

logger = logging.getLogger(__name__)

def escape_markdown(text):
    """Escape special characters for Telegram Markdown"""
    if not text:
        return text

    try:
        # 移除可能导致问题的复杂markdown格式
        # 处理链接 - 简化链接格式
        text = re.sub(r'\[([^\]]*)\]\(([^)]*)\)', r'\1: \2', text)

        # 移除所有的markdown格式符号，使用纯文本
        text = text.replace('*', '')
        text = text.replace('_', '')
        text = text.replace('`', '')
        text = text.replace('[', '')
        text = text.replace(']', '')

        # 保留emoji和基本的换行
        return text
    except Exception as e:
        logger.warning(f"Error escaping markdown: {e}")
        return text

class RSSHandler:
    """Handles RSS feed fetching and deduplication"""

    def __init__(self, config: Config):
        self.config = config
        self.cache_file = config.RSS_CACHE_FILE
        self.seen_articles = self._load_cache()

        # Configure SSL context for feedparser to handle certificate issues
        self._setup_ssl_context()

    def _setup_ssl_context(self):
        """Setup SSL context to handle certificate verification issues"""
        try:
            # Set global SSL context to ignore certificate verification
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context

            # Configure feedparser user agent
            feedparser.USER_AGENT = "RSS-Bot/1.0 (+https://github.com/example/rss-bot)"

            logger.info("SSL context configured for RSS feeds (certificate verification disabled)")
        except Exception as e:
            logger.warning(f"Failed to setup SSL context: {e}")

    def _load_cache(self) -> Dict[str, Dict]:
        """Load cache from file with new structure"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Clean old entries (older than 7 days)
            cutoff_date = datetime.now() - timedelta(days=7)
            cleaned_data = {}

            for article_hash, article_data in data.items():
                try:
                    article_date = datetime.fromisoformat(article_data.get('fetched_at', ''))
                    if article_date > cutoff_date:
                        cleaned_data[article_hash] = article_data
                except (ValueError, TypeError):
                    continue

            # Save cleaned cache
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

            return cleaned_data
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.info(f"Creating new RSS cache: {e}")
            return {}

    def _save_cache(self):
        """Save cache to file with new structure"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.seen_articles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save RSS cache: {e}")

    def _is_today(self, published_date: str) -> bool:
        """Check if article was published today"""
        if not published_date:
            return False

        today = datetime.now().date()
        today_str = today.strftime('%Y-%m-%d')

        try:
            # Try different date parsing approaches
            from dateutil import parser as date_parser
            import re

            # Method 1: Check if today's date is in the string
            if today_str in published_date:
                return True

            # Method 2: Parse with dateutil
            try:
                pub_date = date_parser.parse(published_date)
                return pub_date.date() == today
            except:
                pass

            # Method 3: Handle specific RSS date formats
            rss_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{1,2}\s+\w+\s+\d{4}',  # DD Mon YYYY
                r'\w{3},\s+\d{1,2}\s+\w{3}\s+\d{4}',  # Day, DD Mon YYYY
            ]

            for pattern in rss_patterns:
                match = re.search(pattern, published_date)
                if match:
                    date_part = match.group()
                    try:
                        parsed_date = date_parser.parse(date_part)
                        return parsed_date.date() == today
                    except:
                        continue

        except Exception as e:
            logger.debug(f"Date parsing error for '{published_date}': {e}")

        return False

    def _get_article_hash(self, article: Dict) -> str:
        """Generate a unique hash for an article based on title and link"""
        title = article.get('title', '')
        link = article.get('link', '')
        content = f"{title}{link}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _is_article_seen(self, article: Dict) -> bool:
        """Check if an article has been seen before"""
        article_hash = self._get_article_hash(article)
        return article_hash in self.seen_articles

    def _mark_article_seen(self, article: Dict, feed_name: str):
        """Mark an article as seen with additional metadata"""
        article_hash = self._get_article_hash(article)
        self.seen_articles[article_hash] = {
            'title': article.get('title', ''),
            'link': article.get('link', ''),
            'feed_name': feed_name,
            'fetched_at': datetime.now().isoformat(),
            'published_at': article.get('published', '')
        }

    def _clean_text(self, text: str) -> str:
        """Clean HTML tags and extra whitespace from text"""
        if not text:
            return ""

        # Remove HTML tags (simple approach)
        import re
        text = re.sub(r'<[^>]+>', '', text)

        # Remove extra whitespace
        text = ' '.join(text.split())

        return text

    def _truncate_text(self, text: str, max_length: int = 300) -> str:
        """Truncate text to specified length"""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0] + "..."

    def fetch_feed_single_article(self, feed_config: Dict) -> Dict:
        """Fetch a single today's article from a single RSS feed"""
        feed_url = feed_config.get('url')
        feed_name = feed_config.get('name', 'Unknown Feed')

        try:
            logger.info(f"Fetching RSS feed for single article: {feed_name} ({feed_url})")

            # Fetch RSS feed (SSL context is already configured globally)
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"RSS feed parsing warning for {feed_name}: {feed.bozo_exception}")

            if not feed.entries:
                logger.debug(f"No entries found in RSS feed: {feed_name}")
                return None

            # Sort entries by publication date (newest first)
            sorted_entries = sorted(feed.entries,
                                 key=lambda x: x.get('published', ''),
                                 reverse=True)

            # Find the first article from today that hasn't been seen
            for entry in sorted_entries:
                # Check if article is from today
                if not self._is_today(entry.get('published', '')):
                    continue

                # Skip if article has been seen before
                if self._is_article_seen(entry):
                    logger.debug(f"Article already seen: {entry.get('title', 'No title')[:50]}...")
                    continue

                # Extract article information
                article = {
                    'title': self._clean_text(entry.get('title', 'No title')),
                    'summary': self._clean_text(entry.get('summary', entry.get('description', ''))),
                    'link': entry.get('link', ''),
                    'source': feed_name,
                    'category': feed_config.get('category', 'general'),
                    'published': entry.get('published', '')
                }

                # Truncate summary
                article['summary'] = self._truncate_text(article['summary'])

                if article['title'] and article['link']:
                    # Mark as seen immediately
                    self._mark_article_seen(entry, feed_name)
                    logger.info(f"Found today's article from {feed_name}: {article['title'][:50]}...")
                    return article

            logger.debug(f"No new today's articles found in {feed_name}")
            return None

        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_name}: {e}")
            return None

    def fetch_feed(self, feed_config: Dict) -> List[Dict]:
        """Fetch articles from a single RSS feed (legacy method for compatibility)"""
        feed_url = feed_config.get('url')
        feed_name = feed_config.get('name', 'Unknown Feed')

        try:
            logger.info(f"Fetching RSS feed: {feed_name} ({feed_url})")

            # Fetch RSS feed (SSL context is already configured globally)
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"RSS feed parsing warning for {feed_name}: {feed.bozo_exception}")

            if not feed.entries:
                logger.warning(f"No entries found in RSS feed: {feed_name}")
                return []

            articles = []
            max_articles = self.config.MAX_ARTICLES_PER_FEED
            article_count = 0

            for entry in feed.entries:
                if article_count >= max_articles:
                    break

                # Skip if article has been seen before
                if self._is_article_seen(entry):
                    continue

                # Extract article information
                article = {
                    'title': self._clean_text(entry.get('title', 'No title')),
                    'summary': self._clean_text(entry.get('summary', entry.get('description', ''))),
                    'link': entry.get('link', ''),
                    'source': feed_name,
                    'category': feed_config.get('category', 'general'),
                    'published': entry.get('published', '')
                }

                # Truncate summary
                article['summary'] = self._truncate_text(article['summary'])

                if article['title'] and article['link']:
                    articles.append(article)
                    self._mark_article_seen(entry, feed_name)
                    article_count += 1
                    logger.debug(f"New article from {feed_name}: {article['title'][:50]}...")

            logger.info(f"Found {len(articles)} new articles from {feed_name}")
            return articles

        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_name}: {e}")
            return []

    def fetch_all_feeds(self) -> List[Dict]:
        """Fetch articles from all configured RSS feeds"""
        all_articles = []

        if not self.config.RSS_FEEDS:
            logger.warning("No RSS feeds configured")
            return []

        logger.info(f"Fetching from {len(self.config.RSS_FEEDS)} RSS feeds")

        for feed_config in self.config.RSS_FEEDS:
            if not isinstance(feed_config, dict) or 'url' not in feed_config:
                logger.warning(f"Invalid RSS feed configuration: {feed_config}")
                continue

            articles = self.fetch_feed(feed_config)
            all_articles.extend(articles)

        # Sort by publication date if available
        all_articles.sort(key=lambda x: x.get('published', ''), reverse=True)

        # Save updated cache
        self._save_cache()

        logger.info(f"Total new articles: {len(all_articles)}")
        return all_articles

    def format_for_channel(self, articles: List[Dict], channel_name: str = None) -> str:
        """Format RSS articles for Telegram channel posting"""
        if not articles:
            return ""  # Return empty string when no articles to prevent empty channel posts

        channel_header = f"@{channel_name}" if channel_name else "RSS新闻"

        # Format channel message
        channel_text = f"📡 *{channel_header} RSS更新*\n\n"
        channel_text += f"📊 *{len(articles)} 篇新文章*\n\n"

        for i, article in enumerate(articles, 1):
            title = article.get('title', '无标题')
            summary = article.get('summary', '')
            source = article.get('source', '未知来源')
            category = article.get('category', '综合')
            link = article.get('link', '')

            channel_text += f"🔹 **{title}**\n"
            if summary:
                channel_text += f"📝 {summary}\n"
            channel_text += f"📺 来源：{source} ({category})\n"
            if link:
                channel_text += f"🔗 [阅读全文]({link})\n"
            channel_text += "\n"

        channel_text += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        channel_text += f"🔄 *RSS机器人自动发布*"

        return escape_markdown(channel_text)

    def fetch_all_feeds_round_robin(self) -> List[Dict]:
        """Fetch one article from each RSS feed using round-robin logic"""
        if not self.config.RSS_FEEDS:
            logger.warning("No RSS feeds configured")
            return []

        articles = []
        logger.info(f"Starting round-robin fetch from {len(self.config.RSS_FEEDS)} RSS feeds")

        # Iterate through each feed and try to get one article
        for feed_config in self.config.RSS_FEEDS:
            if not isinstance(feed_config, dict) or 'url' not in feed_config:
                logger.warning(f"Invalid RSS feed configuration: {feed_config}")
                continue

            feed_name = feed_config.get('name', 'Unknown Feed')
            logger.info(f"Checking feed: {feed_name}")

            # Try to get a single article from this feed
            article = self.fetch_feed_single_article(feed_config)
            if article:
                articles.append(article)
                logger.info(f"Successfully fetched 1 article from {feed_name}")
            else:
                logger.debug(f"No new today's articles from {feed_name}")

        # Sort articles by publication date
        articles.sort(key=lambda x: x.get('published', ''), reverse=True)

        # Save updated cache
        self._save_cache()

        logger.info(f"Round-robin fetch complete: {len(articles)} articles from {len(self.config.RSS_FEEDS)} feeds")
        return articles

    def get_latest_news(self, max_total: int = 10) -> List[Dict]:
        """Get latest news from all RSS feeds using new round-robin logic"""
        try:
            articles = self.fetch_all_feeds_round_robin()

            if not articles:
                return []

            # Limit total articles
            return articles[:max_total]

        except Exception as e:
            logger.error(f"Error getting latest news: {e}")
            return []