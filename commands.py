import requests
import logging
import re
import sys
import os
from datetime import datetime
from config import Config
from rss_handler import RSSHandler
from hackernews_handler import HackerNewsHandler

# Add content_generator path for import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from content_generator import (
    OpenAIClient,
    parse_user_intent,
    generate_final_content,
    ContextManager,
    generate_inspirational_quote,
    format_quote_response,
    format_quote_for_channel
)

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
        self.hackernews_handler = HackerNewsHandler()
        self.bot = bot_instance  # Reference to bot instance for channel posting
        self.commands = {
            '/list': self.list_commands,
            '/help': self.list_commands,
            '/rss_news': self.get_rss_news,
            '/news': self.get_news,
            '/quote': self.get_quote,
            '/ask': self.ask_question,
            '/hacker_news': self.get_hacker_news
        }
    
    def list_commands(self, command, full_message, user_id):
        """List all available commands"""
        help_text = """
🤖 机器人可用命令：

📋 信息命令：
• `/list` - 显示所有可用命令
• `/help` - 显示此帮助信息

📡 RSS新闻订阅：
• `/rss_news` - 获取RSS源最新新闻
  从多个可配置的RSS源获取新闻
  (可自动转发到指定频道)

📰 新闻头条：
• `/news [国家]` - 获取指定国家最新新闻摘要
  示例：`/news cn` (中国) 或 `/news us` (美国)
• `/news [主题]` - 获取特定主题新闻
  示例：`/news technology` 或 `/news sports`

💭 AI智慧名言：
• `/quote` - 获取AI生成的励志名言及深度解读
  (可自动转发到指定频道)

🤖 AI问答：
• `/ask [问题]` - 向AI助手提问
  示例：`/ask 今天天气如何？` 或 `/ask 请解释量子计算`

🔥 Hacker News AI精选：
• `/hacker_news` - 获取Hacker News当日AI主题文章
  自动搜索当天最新的AI相关文章并进行深度分析
  (可自动转发到指定频道)

使用提示：
• RSS源自动去重，避免重复内容
• 使用国家代码查询新闻 (cn, us, uk 等) 或主题关键词
• 所有命令不区分大小写
• RSS新闻、GNews、Hacker News和智慧名言可自动转发到配置的频道
        """
        return escape_markdown(help_text.strip())
    
    def get_rss_news(self, command, full_message, user_id):
        """Get latest news from RSS feeds with optional channel forwarding"""
        try:
            logger.info(f"Fetching RSS news for user {user_id}")

            # Get latest articles from RSS feeds
            articles = self.rss_handler.get_latest_news(max_total=10)

            # Format user response
            if not articles:
                user_response = """
📡 RSS新闻更新

🔍 未发现新文章

这可能意味着您已经看过所有最新文章，或者您的RSS源中没有新文章。

配置的RSS源数量： {} 个
下次检查： 几分钟后重试以获取新内容

🕐 更新时间： {}
                """.format(
                    len(self.config.RSS_FEEDS),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ).strip()
            else:
                # Format RSS news response for user
                user_response = f"📊 发布 {len(articles)} 篇新文章\n\n"

                for i, article in enumerate(articles, 1):
                    title = article.get('title', '无标题')
                    summary = article.get('summary', '')
                    source = article.get('source', '未知来源')
                    link = article.get('link', '')
                    category = article.get('category', '综合')
                    published = article.get('published', '')

                    user_response += f"{i}. {title}\n"
                    user_response += f"   📺 来源：{source} ({category})\n"
                    if summary:
                        user_response += f"   📝 {summary}\n"
                    if link:
                        user_response += f"   🔗 [阅读全文]({link})\n"
                    if published:
                        user_response += f"   📅 {published}\n"
                    user_response += f"#{category} #rss\n\n"

                #user_response += f"🕐 更新时间： {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

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
                        #user_response += f"\n\n✅ 内容已转发到 @{self.config.RSS_FORWARD_TO_CHANNEL}"
                    else:
                        logger.warning(f"Failed to forward RSS news to channel @{self.config.RSS_FORWARD_TO_CHANNEL}")
                        #user_response += f"\n\n⚠️ 频道转发失败"

                except Exception as e:
                    logger.error(f"Error forwarding RSS news to channel: {e}")
                    #user_response += f"\n\n⚠️ 频道转发错误： {str(e)}"

            return escape_markdown(user_response.strip())

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
            news_text = f"📰 最新新闻头条 ({location_name})\n\n"

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

                news_text += f"{i}. {title}\n"
                news_text += f"   📝 {summary}\n"
                news_text += f"   📺 来源：{source}\n"
                if url:
                    news_text += f"   🔗 [阅读全文]({url})\n"
                if published_date:
                    # Format date nicely
                    try:
                        pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                        formatted_date = pub_date.strftime('%Y-%m-%d %H:%M')
                        news_text += f"   📅 {formatted_date}\n"
                    except:
                        pass
                news_text += "\n"

            #return escape_markdown(news_text.strip()) + "\n\n#news_headlines"
            return news_text.strip()

        except requests.exceptions.RequestException as e:
            logger.error(f"GNews API error: {e}")
            return "❌ 获取新闻失败，请稍后重试。\n\n#network_error"
        except Exception as e:
            logger.error(f"Unexpected error in news command: {e}")
            return "❌ 获取新闻时发生错误。\n\n#error"
    
    def get_quote(self, command, full_message, user_id):
        """Get an AI-generated inspirational quote with detailed analysis"""
        try:
            logger.info(f"Generating AI quote for user {user_id}")

            # Check OpenAI API configuration
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                # Fallback to basic quote if OpenAI not configured
                logger.warning("OpenAI API key not configured, using fallback quote")
                return self._get_fallback_quote()

            base_url = os.getenv('OPENAI_BASE_URL')
            default_model = os.getenv('DEFAULT_MODEL', 'gpt-3.5-turbo')

            # Initialize OpenAI client
            openai_client = OpenAIClient(api_key, base_url)

            # Generate quote and analysis
            quote_data = generate_inspirational_quote(openai_client, default_model)

            # Format response for user
            formatted_response = format_quote_response(quote_data)

            # Handle channel forwarding if enabled
            if (self.config.ENABLE_RSS_FORWARDING and
                self.config.RSS_FORWARD_TO_CHANNEL and
                self.bot):
                try:
                    channel_message = format_quote_for_channel(
                        quote_data,
                        self.config.RSS_FORWARD_TO_CHANNEL
                    )

                    logger.info(f"Forwarding quote to channel: @{self.config.RSS_FORWARD_TO_CHANNEL}")
                    forward_result = self.bot.send_message_to_channel(
                        self.config.RSS_FORWARD_TO_CHANNEL,
                        channel_message
                    )

                    if forward_result:
                        logger.info(f"Successfully forwarded quote to channel @{self.config.RSS_FORWARD_TO_CHANNEL}")
                    else:
                        logger.warning(f"Failed to forward quote to channel @{self.config.RSS_FORWARD_TO_CHANNEL}")

                except Exception as e:
                    logger.error(f"Error forwarding quote to channel: {e}")

            return escape_markdown(formatted_response.strip())

        except Exception as e:
            logger.error(f"Error in AI quote command: {e}")
            return self._get_fallback_quote()

    def _get_fallback_quote(self):
        return """
💭 今日名言：

_"成就伟大事业的唯一方法是热爱你所做的工作。"_

🖋️ — 史蒂夫·乔布斯
        """.strip() + "\n\n#daily_quote"
    

    def ask_question(self, command, full_message, user_id):
        """Ask AI assistant a question using content_generator"""
        try:
            # Parse question from command
            parts = full_message.strip().split(maxsplit=1)
            if len(parts) < 2:
                return "❌ 请提供问题内容。用法：`/ask [您的问题]`\n\n#usage_error"

            question = parts[1].strip()
            logger.info(f"User {user_id} asks: {question[:100]}...")

            # Check OpenAI API configuration
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return "⚠️ 未配置OpenAI API密钥，请设置OPENAI_API_KEY环境变量。\n\n#config_error"

            base_url = os.getenv('OPENAI_BASE_URL')
            default_model = os.getenv('DEFAULT_MODEL', 'gpt-3.5-turbo')

            # Initialize OpenAI client
            openai_client = OpenAIClient(api_key, base_url)

            # Initialize context manager
            context_manager = ContextManager()

            # System prompt for AI assistant
            system_prompt = """你是一个专业的AI助手，擅长回答各种问题并提供有用的信息。
请确保回答：
1. 内容准确、逻辑清晰
2. 语言流畅、表达自然
3. 回答简洁明了，重点突出
4. 具有实用价值"""

            # Step 1: Parse user intent
            intent = parse_user_intent(openai_client, question, default_model)

            # Step 2: Save intent to context
            context_manager.add_context(intent)

            # Step 3: Get latest contexts
            latest_contexts = context_manager.get_latest_contexts(3)

            # Step 4: Generate final response
            response = generate_final_content(openai_client, question, latest_contexts, system_prompt, default_model)

            # Format response for Telegram
            formatted_response = response

            return escape_markdown(formatted_response.strip())

        except Exception as e:
            logger.error(f"Error in ask command: {e}")
            return f"❌ 处理问题时发生错误：{str(e)}\n\n请稍后重试或检查API配置。\n\n#error"

    def get_hacker_news(self, command, full_message, user_id):
        """Get latest AI-related article from Hacker News with AI analysis"""
        try:
            logger.info(f"Fetching Hacker News AI article for user {user_id}")

            # Check OpenAI API configuration
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return "⚠️ 未配置OpenAI API密钥，请设置OPENAI_API_KEY环境变量。\n\n#config_error"

            base_url = os.getenv('OPENAI_BASE_URL')
            default_model = os.getenv('DEFAULT_MODEL', 'gpt-3.5-turbo')

            # Initialize OpenAI client
            openai_client = OpenAIClient(api_key, base_url)

            # Find AI-related article from today
            article = self.hackernews_handler.find_ai_article_today()
            if not article:
                return """
🔍 *Hacker News AI 搜索*

📅 当天未找到AI相关文章

今天 Hacker News 上可能没有发布新的AI主题文章，或者相关文章已被错过。

🔍 **搜索范围：**
• 当天发布的最新文章
• 包含 AI、机器学习、深度学习等关键词
• 技术文章和讨论

⏰ **下次检查：** 几分钟后重试
💡 **建议：** 可以稍后再次尝试此命令

🤖 *Hacker News AI 机器人*
                """.strip()

            # Get article URL
            article_url = article.get('url')
            if not article_url:
                # If no URL, it might be a text-only post
                title = article.get('title', 'No title')
                text = article.get('text', '')

                user_response = f"""🤖 *Hacker News AI 文章分析*

📰 **标题：** {title}

⚠️ *此文章没有外部链接，可能是文本讨论*

"""
                if text:
                    # Use text content directly for analysis
                    analysis = self.hackernews_handler.analyze_article_with_ai(
                        article, text, openai_client, default_model
                    )
                    if analysis:
                        user_response += f"📝 **AI 分析结果：**\n\n{analysis}"
                    else:
                        user_response += "❌ AI 分析失败，请稍后重试"
                else:
                    user_response += "📝 **内容：** 无可用文本内容"

                user_response += f"\n\n🤖 *由 HN AI 机器人自动分析*\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                return escape_markdown(user_response)

            # Fetch article content
            content = self.hackernews_handler.fetch_article_content(article_url)
            if not content:
                return f"""🤖 *Hacker News AI 文章分析*

📰 **标题：** {article.get('title', 'No title')}

🔗 **链接：** [阅读原文]({article_url})

❌ **内容获取失败**

无法获取文章内容进行分析，可能是：
• 网站访问受限
• 文章链接已失效
• 网络连接问题

🔗 您可以直接点击链接查看原文：
{article_url}

🤖 *Hacker News AI 机器人*
                """

            # Analyze article with AI
            analysis = self.hackernews_handler.analyze_article_with_ai(
                article, content, openai_client, default_model
            )

            if not analysis:
                return f"""🤖 *Hacker News AI 文章分析*

📰 **标题：** {article.get('title', 'No title')}

🔗 **链接：** [阅读原文]({article_url})

❌ **AI 分析失败**

AI 分析服务暂时不可用，请稍后重试。

🔗 直接查看原文：
{article_url}

🤖 *Hacker News AI 机器人*
                """

            # Format response for user
            user_response = self.hackernews_handler.format_analysis_for_telegram(article, analysis)

            # Handle channel forwarding if enabled
            if (self.config.ENABLE_RSS_FORWARDING and
                self.config.RSS_FORWARD_TO_CHANNEL and
                self.bot):
                try:
                    channel_message = self.hackernews_handler.format_analysis_for_channel(
                        article, analysis, self.config.RSS_FORWARD_TO_CHANNEL
                    )

                    logger.info(f"Forwarding Hacker News analysis to channel: @{self.config.RSS_FORWARD_TO_CHANNEL}")
                    forward_result = self.bot.send_message_to_channel(
                        self.config.RSS_FORWARD_TO_CHANNEL,
                        channel_message
                    )

                    if forward_result:
                        logger.info(f"Successfully forwarded Hacker News analysis to channel @{self.config.RSS_FORWARD_TO_CHANNEL}")
                    else:
                        logger.warning(f"Failed to forward Hacker News analysis to channel @{self.config.RSS_FORWARD_TO_CHANNEL}")

                except Exception as e:
                    logger.error(f"Error forwarding Hacker News analysis to channel: {e}")

            return escape_markdown(user_response)

        except Exception as e:
            logger.error(f"Error in Hacker News command: {e}")
            return "❌ 获取Hacker News文章时发生错误，请稍后重试。\n\n#error"

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