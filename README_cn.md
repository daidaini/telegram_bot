# Telegram 机器人服务

一个基于 Flask 的 Telegram 机器人服务，提供多种信息服务，使用长轮询模式运行。

## 功能特性

### 可用命令

1. **/list** - 显示所有可用命令及其描述
2. **/rss_news** - 从 RSS 源获取最新新闻
   - 使用轮询逻辑从多个可配置的 RSS 源获取内容
   - **今日内容**：仅获取今天发布的文章
   - **每源一条**：每个 RSS 源每次最多获取一篇文章
   - **自动去重**：防止显示重复文章
   - 使用 feedparser 库进行增强的日期解析
   - 可自动将内容转发到配置的 Telegram 频道
   - 智能转发：仅在有新内容时转发
3. **/news [国家|主题]** - 获取带摘要的最新新闻标题
   - 示例：`/news cn` (中国) 或 `/news us` (美国)
   - 示例：`/news technology` 或 `/news sports` (主题)
   - 使用 GNews API 提供摘要和原始链接
4. **/quote** - 获取 AI 生成的励志名言及深度分析
   - 使用 OpenAI API 生成具有深度哲学分析的原创名言
   - 包含作者背景、历史背景、现代意义和实际应用
   - 可自动将内容转发到配置的 Telegram 频道
   - 智能转发：自动与频道社区分享智慧

## 技术架构

- **框架**：Flask 2.3.3
- **通信**：Telegram Bot API 长轮询模式
- **外部 API**：GNews、OpenAI（用于 AI 生成名言）
- **RSS 源**：可配置的 RSS 源，带去重功能
- **AI 集成**：智能内容生成与上下文管理
- **配置**：支持 .env 文件的环境变量配置

## 安装指南

### 1. 克隆并设置项目

```bash
# 克隆仓库
git clone <repository-url>
cd telegram_bot

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制示例环境文件
cp .env.example .env

# 编辑 .env 文件进行配置
nano .env
```

### 3. 必需的 API 密钥

#### Telegram Bot 令牌
1. 在 Telegram 上与 [@BotFather](https://t.me/botfather) 创建机器人
2. 获取机器人令牌
3. 添加到 `.env` 文件：`TELEGRAM_BOT_TOKEN=your_bot_token_here`

#### RSS 源配置（可选）
机器人默认包含 RSS 源（BBC、Reuters、CNN），但您可以配置自定义源：

1. 编辑您的 `.env` 文件
2. 添加自定义 RSS 源作为 JSON：
   ```
   RSS_FEEDS=[{"name": "源名称", "url": "https://example.com/rss.xml", "category": "general"}]
   ```
3. 设置每个源的最大文章数：`MAX_ARTICLES_PER_FEED=3`

#### RSS 频道转发（可选）
当调用 `/rss_news` 时自动将 RSS 新闻转发到 Telegram 频道：

1. 将机器人添加到目标频道作为管理员
2. 编辑您的 `.env` 文件：
   ```
   RSS_FORWARD_TO_CHANNEL=cangshuing
   ENABLE_RSS_FORWARDING=true
   ```
3. 机器人将自动发布格式化的 RSS 内容到频道

#### 新闻 API 密钥（可选）
1. 在 [GNews](https://gnews.io/) 注册
2. 获取免费 API 密钥
3. 添加到 `.env` 文件：`GNEWS_API_KEY=your_gnews_api_key_here`

#### OpenAI API 密钥（AI 名言功能）
1. 从 [OpenAI Platform](https://platform.openai.com/) 获取您的 OpenAI API 密钥
2. 添加到 `.env` 文件：`OPENAI_API_KEY=your_openai_api_key_here`
3. 可选：自定义 API 基础 URL：`OPENAI_BASE_URL=https://api.example.com/v1`
4. 可选：默认模型：`DEFAULT_MODEL=gpt-3.5-turbo`

## 使用方法

### 测试功能

在运行机器人之前，您可以测试功能：

```bash
# 测试 GNews 集成
python test_news.py

# 测试 RSS 源功能
python test_rss.py

# 测试频道转发
python test_channel_forwarding.py

# 测试轮询 RSS 逻辑
python test_round_robin_logic.py

# 测试新逻辑的 RSS 源
python test_round_robin_rss.py

# 系统状态检查
python system_status.py
```

这些脚本测试各种命令，无需 Telegram 集成。

### 运行机器人

```bash
python app.py
```

机器人将：
1. 在端口 5000 上启动 Flask Web 服务器
2. 在后台开始轮询 Telegram 更新
3. 响应用户的命令

### 健康检查

机器人提供健康检查端点：
- **URL**：`http://localhost:5000/health`
- **响应**：`{"status": "healthy", "timestamp": "..."}`

## 项目结构

```
telegram_bot/
├── app.py              # 主 Flask 应用程序和机器人逻辑
├── config.py           # 配置管理
├── commands.py         # 机器人功能的命令处理器
├── rss_handler.py      # RSS 源获取和去重逻辑
├── content_generator.py # AI 内容生成和上下文管理
├── test_news.py        # GNews 功能测试脚本
├── test_rss.py         # RSS 功能测试脚本
├── test_channel_forwarding.py  # 频道转发测试脚本
├── test_round_robin_logic.py   # 轮询 RSS 逻辑测试脚本
├── test_round_robin_rss.py     # 新逻辑 RSS 源测试脚本
├── system_status.py    # 系统状态检查脚本
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量模板
├── README.md           # 英文文档
└── README_cn.md        # 中文文档（本文件）
```

## API 集成详情

### RSS 源
- **库**：feedparser 配合 python-dateutil 进行增强的日期解析
- **源**：可配置的 RSS 源（默认：BBC、Reuters、CNN）
- **功能**：
  - **轮询获取**：每次请求每个源获取一篇文章
  - **今日过滤**：仅获取今天发布的文章
  - **自动去重**：防止显示相同文章
  - **智能缓存**：带元数据的增强缓存（7天保留）
  - **频道转发**：启用时自动发布到 Telegram 频道
  - **智能转发**：仅在有新内容时转发到频道

### 新闻 API
- **提供商**：GNews
- **端点**：头条新闻和搜索
- **功能**：带摘要和原始链接的最新新闻，国家/主题过滤
- **限制**：每次请求 5 篇文章
- **语言**：支持多种语言，包括中文（zh）

### AI 名言生成
- **提供商**：OpenAI API（GPT 模型）
- **功能**：
  - 具有深度哲学分析的原创励志名言
  - 作者背景和历史背景
  - 现代意义和实际应用
  - 历史人物的相关引用
  - 带标记处理的智能 JSON 解析
  - 健壮的降级机制
- **降级**：如果 AI 不可用，使用外部名言 API 或静态名言

## 配置选项

### 环境变量

| 变量 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `TELEGRAM_BOT_TOKEN` | 是 | - | 来自 @BotFather 的 Telegram 机器人令牌 |
| `GNEWS_API_KEY` | 可选 | - | GNews API 密钥 |
| `OPENAI_API_KEY` | 可选 | - | AI 名言生成的 OpenAI API 密钥 |
| `OPENAI_BASE_URL` | 可选 | - | OpenAI 兼容 API 的自定义 API 基础 URL |
| `DEFAULT_MODEL` | 可选 | gpt-3.5-turbo | AI 内容生成的默认模型 |
| `RSS_FEEDS` | 可选 | 默认源 | RSS 源配置的 JSON 数组 |
| `MAX_ARTICLES_PER_FEED` | 否 | 3 | 每个 RSS 源获取的最大文章数 |
| `RSS_FORWARD_TO_CHANNEL` | 可选 | - | 自动转发的频道用户名 |
| `ENABLE_RSS_FORWARDING` | 否 | false | 启用/禁用频道转发 |
| `DEFAULT_NEWS_COUNTRY` | 否 | cn | 新闻查询的默认国家 |
| `DEFAULT_NEWS_LANGUAGE` | 否 | zh | 新闻的默认语言（zh=中文） |

## 错误处理

机器人包含全面的错误处理：

1. **API 失败**：使用用户友好消息的优雅降级
2. **无效命令**：清晰的错误消息和帮助建议
3. **网络问题**：自动重试和超时处理
4. **数据解析**：带验证的健壮解析

## 日志记录

机器人使用 Python 的日志模块，具有：
- **级别**：INFO
- **格式**：`timestamp - name - level - message`
- **输出**：控制台

## 安全考虑

1. **API 密钥**：存储在环境变量中，永远不要提交到版本控制
2. **输入验证**：所有用户输入都经过验证和清理
3. **错误消息**：通用错误消息以避免信息泄露
4. **速率限制**：外部 API 的固有速率限制

## 部署

### 开发环境
```bash
python app.py
```

### 生产环境（使用 Gunicorn）
```bash
# 安装 gunicorn
pip install gunicorn

# 使用 gunicorn 运行
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

## 故障排除

### 常见问题

1. **机器人令牌不工作**
   - 使用 @BotFather 验证令牌
   - 检查额外的空格或字符
   - 确保机器人已启用

2. **RSS 源错误**
   - 检查 RSS 源 URL 是否可访问
   - 验证 RSS 源格式是否有效
   - 确保到源的网络连接

3. **频道转发错误**
   - 确保机器人已添加到目标频道作为管理员
   - 验证频道用户名是否正确（不带 @ 符号）
   - 检查机器人在频道中是否有发布权限

4. **新闻 API 错误**
   - 验证 GNews API 密钥有效性
   - 检查国家代码格式（2字母代码）或主题关键词
   - 确保 API 配额可用

5. **连接问题**
   - 检查互联网连接
   - 验证防火墙设置
   - 确保端口开放

### 调试模式

通过修改 `app.py` 启用调试日志：
```python
logging.basicConfig(level=logging.DEBUG)
```

## 贡献

1. Fork 仓库
2. 创建功能分支
3. 为新功能添加测试
4. 提交 Pull Request

## 许可证

本项目采用 MIT 许可证。

---

## 测试目录

所有测试代码都位于 `Test/` 目录中，包含：

### 核心功能测试
- `test_ask_command.py` - 测试 AI 问答命令功能
- `test_rss.py` - 测试 RSS 新闻功能
- `test_news.py` - 测试 GNews API 集成
- `test_enhanced_quote.py` - 测试增强的 AI 名言功能

### 逻辑测试
- `test_round_robin_logic.py` - 测试轮询逻辑
- `test_round_robin_rss.py` - 测试 RSS 轮询获取

### 集成测试
- `test_channel_forwarding.py` - 测试 RSS 频道转发功能
- `test_quote_channel_forwarding.py` - 测试名言频道转发功能
- `test_message_send.py` - 测试消息发送功能
- `test_webhook_integration.py` - 测试 Webhook 集成

### 演示脚本
- `demo_command_parsing.py` - 演示 Telegram 命令解析过程

### 工具脚本
- `run_all_tests.py` - 批量运行所有测试
- `update_imports.py` - 批量更新测试文件的导入路径

### 运行测试
```bash
# 进入测试目录
cd Test

# 运行所有测试
python3 run_all_tests.py

# 运行单个测试
python3 test_rss.py
python3 test_enhanced_quote.py
```

### 注意事项
- 测试需要配置相应的环境变量
- 部分测试需要网络连接访问外部 API
- 频道转发测试需要将机器人添加到测试频道作为管理员