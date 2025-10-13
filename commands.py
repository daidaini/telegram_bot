import requests
import logging
import re
from datetime import datetime
from config import Config
from rss_handler import RSSHandler

logger = logging.getLogger(__name__)

def escape_markdown(text):
    """Escape special characters for Telegram Markdown"""
    if not text:
        return text

    try:
        # 移除可能导致问题的复杂markdown格式
        # Telegram对markdown格式很严格，使用简化版本

        # 处理链接 - 简化链接格式
        text = re.sub(r'\[([^\]]*)\]\(([^)]*)\)', r'\1: \2', text)

        # 移除所有的markdown格式符号，使用纯文本
        # 这样虽然失去格式，但能确保消息发送成功
        text = text.replace('*', '')
        text = text.replace('_', '')
        text = text.replace('`', '')
        text = text.replace('[', '')
        text = text.replace(']', '')

        # 但保留emoji和基本的换行
        return text
    except Exception as e:
        logger.warning(f"Error escaping markdown: {e}")
        return text

class CommandHandler:
    def __init__(self, bot_instance=None):
        self.config = Config()
        self.rss_handler = RSSHandler(self.config)
        self.bot = bot_instance  # Reference to bot instance for channel posting
        self.commands = {
            '/list': self.list_commands,
            '/help': self.list_commands,
            '/rss_news': self.get_rss_news,
            '/news': self.get_news,
            '/quote': self.get_quote
        }
    
    def list_commands(self, command, full_message, user_id):
        """List all available commands"""
        help_text = """
🤖 *机器人可用命令：*

📋 *信息命令：*
• `/list` - 显示所有可用命令
• `/help` - 显示此帮助信息

📡 *RSS新闻订阅：*
• `/rss_news` - 获取RSS源最新新闻
  从多个可配置的RSS源获取新闻
  (可自动转发到指定频道)

📰 *新闻头条：*
• `/news [国家]` - 获取指定国家最新新闻摘要
  示例：`/news cn` (中国) 或 `/news us` (美国)
• `/news [主题]` - 获取特定主题新闻
  示例：`/news technology` 或 `/news sports`

💭 *励志名言：*
• `/quote` - 获取随机励志名言

*使用提示：*
• RSS源自动去重，避免重复内容
• 使用国家代码查询新闻 (cn, us, uk 等) 或主题关键词
• 所有命令不区分大小写
• RSS新闻和GNews都包含摘要和原文链接
        """
        return escape_markdown(help_text.strip()) + "\n\n#bot_help"
    
    def get_rss_news(self, command, full_message, user_id):
        """Get latest news from RSS feeds with optional channel forwarding"""
        try:
            logger.info(f"Fetching RSS news for user {user_id}")

            # Get latest articles from RSS feeds
            articles = self.rss_handler.get_latest_news(max_total=10)

            # Format user response
            if not articles:
                user_response = """
📡 *RSS新闻更新*

🔍 *未发现新文章*

这可能意味着您已经看过所有最新文章，或者您的RSS源中没有新文章。

*配置的RSS源数量：* {} 个
*下次检查：* 几分钟后重试以获取新内容

🕐 *更新时间：* {}
                """.format(
                    len(self.config.RSS_FEEDS),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ).strip()
            else:
                # Format RSS news response for user
                user_response = f"📡 *最新RSS新闻*\n\n"
                user_response += f"📊 *发现 {len(articles)} 篇新文章*\n\n"

                for i, article in enumerate(articles, 1):
                    title = article.get('title', '无标题')
                    summary = article.get('summary', '')
                    source = article.get('source', '未知来源')
                    link = article.get('link', '')
                    category = article.get('category', '综合')
                    published = article.get('published', '')

                    user_response += f"{i}. **{title}**\n"
                    if summary:
                        user_response += f"   📝 *{summary}*\n"
                    user_response += f"   📺 *来源：{source} ({category})*\n"
                    if link:
                        user_response += f"   🔗 [阅读全文]({link})\n"
                    if published:
                        user_response += f"   📅 *{published}*\n"
                    user_response += "\n"

                user_response += f"🕐 *更新时间：* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                user_response += f"\n🔄 *文章已自动去重*"

            # Handle channel forwarding if enabled and only if there are new articles
            if (self.config.ENABLE_RSS_FORWARDING and
                self.config.RSS_FORWARD_TO_CHANNEL and
                self.bot and
                articles):  # Only forward if there are new articles
                try:
                    channel_message = self.rss_handler.format_for_channel(
                        articles,
                        self.config.RSS_FORWARD_TO_CHANNEL
                    )

                    logger.info(f"Forwarding RSS news to channel: @{self.config.RSS_FORWARD_TO_CHANNEL}")
                    forward_result = self.bot.send_message_to_channel(
                        self.config.RSS_FORWARD_TO_CHANNEL,
                        channel_message
                    )

                    if forward_result:
                        logger.info(f"Successfully forwarded RSS news to channel @{self.config.RSS_FORWARD_TO_CHANNEL}")
                        user_response += f"\n\n✅ *内容已转发到 @{self.config.RSS_FORWARD_TO_CHANNEL}*"
                    else:
                        logger.warning(f"Failed to forward RSS news to channel @{self.config.RSS_FORWARD_TO_CHANNEL}")
                        user_response += f"\n\n⚠️ *频道转发失败*"

                except Exception as e:
                    logger.error(f"Error forwarding RSS news to channel: {e}")
                    user_response += f"\n\n⚠️ *频道转发错误：* {str(e)}"

            return escape_markdown(user_response.strip()) + "\n\n#rss_news"

        except Exception as e:
            logger.error(f"Unexpected error in RSS news command: {e}")
            return "❌ 获取RSS新闻时发生错误，请稍后重试。\n\n#error"
    
    def get_news(self, command, full_message, user_id):
        """Get latest news headlines with summaries using GNews API"""
        try:
            # Parse country/topic from command
            parts = full_message.strip().split()
            if len(parts) > 1:
                query = parts[1].lower()
            else:
                query = self.config.DEFAULT_NEWS_COUNTRY

            if not self.config.NEWS_API_KEY:
                return "⚠️ 未配置GNews API密钥，请设置GNEWS_API_KEY环境变量。\n\n#config_error"

            # Determine if query is a country code or topic
            country_codes = ['cn', 'us', 'uk', 'ca', 'au', 'in', 'de', 'fr', 'it', 'jp', 'kr', 'ru', 'br', 'mx']

            # Make API request
            params = {
                'apikey': self.config.NEWS_API_KEY,
                'lang': self.config.DEFAULT_NEWS_LANGUAGE,
                'max': 5,  # Number of articles
                'expand': 'content'  # Include full content for better summaries
            }

            if query in country_codes:
                # Query is a country code
                params['country'] = query.upper()
                location_name = query.upper()
            else:
                # Query is a topic/keyword
                params['q'] = query
                location_name = query

            response = requests.get(self.config.NEWS_API_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'articles' not in data:
                return f"❌ 获取 '{location_name}' 新闻失败，请尝试其他查询。\n\n#api_error"

            articles = data.get('articles', [])

            if not articles:
                return f"📰 未找到 '{location_name}' 的相关新闻。\n\n#no_results"

            # Format news response
            news_text = f"📰 *最新新闻头条 ({location_name})*\n\n"

            for i, article in enumerate(articles, 1):
                title = article.get('title', '无标题')
                description = article.get('description', '')
                source = article.get('source', {}).get('name', '未知来源')
                url = article.get('url', '')
                published_date = article.get('publishedAt', '')

                # Create summary from description, truncate if too long
                summary = description[:200] + "..." if len(description) > 200 else description
                if not summary:
                    summary = "暂无摘要"

                news_text += f"{i}. **{title}**\n"
                news_text += f"   📝 *{summary}*\n"
                news_text += f"   📺 *来源：{source}*\n"
                if url:
                    news_text += f"   🔗 [阅读全文]({url})\n"
                if published_date:
                    # Format date nicely
                    try:
                        pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                        formatted_date = pub_date.strftime('%Y-%m-%d %H:%M')
                        news_text += f"   📅 *{formatted_date}*\n"
                    except:
                        pass
                news_text += "\n"

            news_text += f"🕐 *更新时间：* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            news_text += f"\n📊 *数据来源：GNews.io*"

            return escape_markdown(news_text.strip()) + "\n\n#news_headlines"

        except requests.exceptions.RequestException as e:
            logger.error(f"GNews API error: {e}")
            return "❌ 获取新闻失败，请稍后重试。\n\n#network_error"
        except Exception as e:
            logger.error(f"Unexpected error in news command: {e}")
            return "❌ 获取新闻时发生错误。\n\n#error"
    
    def get_quote(self, command, full_message, user_id):
        """Get a random inspirational quote"""
        try:
            # Make API request
            response = requests.get(self.config.QUOTE_API_URL, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            quote_text = data.get('content', '')
            author = data.get('author', 'Unknown')
            
            if not quote_text:
                return "❌ 获取名言失败，请稍后重试。\n\n#api_error"

            # Format quote response
            formatted_quote = f"""
💭 **今日名言：**

_"{quote_text}"_

🖋️ — {author}

🕐 *{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
            """.strip()

            return escape_markdown(formatted_quote.strip()) + "\n\n#daily_quote"

        except requests.exceptions.RequestException as e:
            logger.error(f"Quote API error: {e}")
            # Fallback to a static quote if API fails
            return """
💭 **今日名言：**

_"成就伟大事业的唯一方法是热爱你所做的工作。"_

🖋️ — 史蒂夫·乔布斯

🕐 *备用名言 - API暂时不可用*
            """.strip() + "\n\n#daily_quote"
        except Exception as e:
            logger.error(f"Unexpected error in quote command: {e}")
            return "❌ 获取名言时发生错误。\n\n#error"
    
    def handle_command(self, command, full_message, user_id):
        """Handle incoming commands"""
        command = command.lower()

        if command in self.commands:
            try:
                return self.commands[command](command, full_message, user_id)
            except Exception as e:
                logger.error(f"Error executing command {command}: {e}")
                return f"❌ 处理命令 '{command}' 时发生错误。\n\n#command_error"
        else:
            return f"❌ 未知命令 '{command}'，请使用 /list 查看可用命令。\n\n#unknown_command"