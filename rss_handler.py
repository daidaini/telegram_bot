import feedparser
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from config import Config

logger = logging.getLogger(__name__)

class RSSHandler:
    """Handles RSS feed fetching and deduplication"""

    def __init__(self, config: Config):
        self.config = config
        self.cache_file = config.RSS_CACHE_FILE
        self.seen_articles = self._load_cache()

    def _load_cache(self) -> Set[str]:
        """Load seen article URLs from cache file"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Clean old entries (older than 7 days)
                cutoff_date = datetime.now() - timedelta(days=7)
                cleaned_data = {
                    url: timestamp for url, timestamp in data.items()
                    if datetime.fromisoformat(timestamp) > cutoff_date
                }

                # Save cleaned cache
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

                return set(cleaned_data.keys())
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.info(f"Creating new RSS cache: {e}")
            return set()

    def _save_cache(self):
        """Save seen article URLs to cache file"""
        try:
            data = {
                url: datetime.now().isoformat()
                for url in self.seen_articles
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save RSS cache: {e}")

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

    def _mark_article_seen(self, article: Dict):
        """Mark an article as seen"""
        article_hash = self._get_article_hash(article)
        self.seen_articles.add(article_hash)

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

    def fetch_feed(self, feed_config: Dict) -> List[Dict]:
        """Fetch articles from a single RSS feed"""
        feed_url = feed_config.get('url')
        feed_name = feed_config.get('name', 'Unknown Feed')

        try:
            logger.info(f"Fetching RSS feed: {feed_name} ({feed_url})")

            # Fetch RSS feed
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
                    self._mark_article_seen(entry)
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

        channel_header = f"@{channel_name}" if channel_name else "RSS News"

        # Format channel message
        channel_text = f"📡 *{channel_header} RSS Update*\n\n"
        channel_text += f"📊 *{len(articles)} New Articles*\n\n"

        for i, article in enumerate(articles, 1):
            title = article.get('title', 'No title')
            summary = article.get('summary', '')
            source = article.get('source', 'Unknown')
            category = article.get('category', 'general')
            link = article.get('link', '')

            channel_text += f"🔹 **{title}**\n"
            if summary:
                channel_text += f"📝 {summary}\n"
            channel_text += f"📺 Source: {source} ({category})\n"
            if link:
                channel_text += f"🔗 [Read more]({link})\n"
            channel_text += "\n"

        channel_text += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        channel_text += f"🔄 *Auto-posted via RSS Bot*"

        return channel_text

    def get_latest_news(self, max_total: int = 10) -> List[Dict]:
        """Get latest news from all RSS feeds"""
        try:
            articles = self.fetch_all_feeds()

            if not articles:
                return []

            # Limit total articles
            return articles[:max_total]

        except Exception as e:
            logger.error(f"Error getting latest news: {e}")
            return []