#!/usr/bin/env python3
"""
AI Content Generator with Intent Analysis and Context Management

This script uses OpenAI's API to generate content based on user input.
It analyzes user intent, maintains context history, and generates responses.

Usage:
    python content_generator.py "Your question or prompt here"
"""

import os
import re
import argparse
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI


class OpenAIClient:
    """Wrapper class for OpenAI API interactions"""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """Initialize OpenAI client with optional custom base_url"""
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)

    def chat_completion(self, messages: List[dict], model: str = "gpt-3.5-turbo") -> str:
        """Send chat completion request to OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024*16
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {str(e)}")


class ContextManager:
    """Manages context storage and retrieval from user_context.md"""

    def __init__(self, context_file: str = "user_context.md"):
        self.context_file = context_file
        self._ensure_context_file_exists()

    def _ensure_context_file_exists(self):
        """Create context file if it doesn't exist"""
        if not os.path.exists(self.context_file):
            with open(self.context_file, 'w', encoding='utf-8') as f:
                f.write("# User Context History\n\n")

    def add_context(self, intent: str) -> int:
        """Add new intent to context file with sequential numbering"""
        try:
            # Read existing content
            with open(self.context_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find the highest existing number
            numbers = re.findall(r'^# (\d+)$', content, re.MULTILINE)
            next_number = max([int(n) for n in numbers] + [0]) + 1

            # Append new context
            with open(self.context_file, 'a', encoding='utf-8') as f:
                f.write(f"# {next_number}\n{intent}\n\n")

            return next_number
        except Exception as e:
            raise Exception(f"Failed to add context: {str(e)}")

    def get_latest_contexts(self, count: int = 3) -> List[str]:
        """Get the latest 'count' contexts from the file"""
        try:
            with open(self.context_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all context entries
            pattern = r'^# (\d+)\n(.*?)(?=\n# |\Z)'
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)

            # Sort by number and get latest
            matches.sort(key=lambda x: int(x[0]))
            latest_matches = matches[-count:] if len(matches) >= count else matches

            # Extract just the intent content
            return [match[1].strip() for match in latest_matches]
        except Exception as e:
            raise Exception(f"Failed to get contexts: {str(e)}")


def parse_user_intent(openai_client: OpenAIClient, user_input: str, model: str) -> str:
    """Parse user intent using AI with thinking capability"""
    system_prompt = """你是一个专业的意图分析助手。请分析用户输入的文本，准确识别并提取用户的核心意图和需求。

分析要求：
1. 识别用户想要完成的具体任务
2. 提取关键信息和需求点
3. 简洁明确地描述用户意图
4. 保持原意的完整性

重要：请直接返回用户意图的描述，不要包含"用户意图："、"分析结果："等任何前缀，只需返回纯净的意图内容。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"用户输入：{user_input}"}
    ]

    intent = openai_client.chat_completion(messages, model)

    # 清理可能的格式化前缀
    intent = intent.strip()
    if intent.startswith("用户意图："):
        intent = intent[5:].strip()
    elif intent.startswith("用户意图:"):
        intent = intent[4:].strip()
    elif intent.startswith("分析结果："):
        intent = intent[5:].strip()
    elif intent.startswith("分析结果:"):
        intent = intent[4:].strip()

    return intent


def generate_final_content(openai_client: OpenAIClient, user_input: str, contexts: List[str], system_prompt: str, model: str) -> str:
    """Generate final content based on user input, context, and system prompt"""
    context_text = "\n".join([f"上下文 {i+1}: {ctx}" for i, ctx in enumerate(contexts)])
    context_text = context_text if context_text else "暂无上下文信息。"

    full_prompt = f"""系统要求：{system_prompt}

用户输入：{user_input}

历史上下文：
{context_text}

请基于以上信息生成合适的内容回复。"""

    messages = [
        {"role": "system", "content": "你是一个专业的内容生成助手，善于根据系统要求、用户输入和历史上下文生成高质量的回复。"},
        {"role": "user", "content": full_prompt}
    ]

    return openai_client.chat_completion(messages, model)


def main():
    """Main function to orchestrate the content generation process"""
    parser = argparse.ArgumentParser(description='AI Content Generator with Context Management')
    parser.add_argument('user_input', help='User input text or question')
    parser.add_argument('--model', help='Model to use (overrides environment variable)')
    parser.add_argument('--system-prompt', help='System prompt to guide content generation')
    parser.add_argument('--context-file', default='user_context.md', help='Context file path (default: user_context.md)')
    parser.add_argument('--base-url', help='Custom API base URL (overrides environment variable)')

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = args.base_url or os.getenv('OPENAI_BASE_URL')
    default_model = os.getenv('DEFAULT_MODEL', 'gpt-3.5-turbo')
    model = args.model or default_model

    if not api_key:
        print("错误：未找到 OPENAI_API_KEY 环境变量")
        print("请在 .env 文件中设置 OPENAI_API_KEY=your_api_key")
        return 1

    if base_url:
        print(f"🔗 使用自定义API地址: {base_url}")

    print(f"🤖 使用模型: {model}")

    # Default system prompt
    system_prompt = args.system_prompt or """你是一个专业的内容创作助手，擅长根据用户需求生成高质量的文本内容。
请确保生成的内容：
1. 内容准确、逻辑清晰
2. 语言流畅、表达自然
3. 符合用户的具体需求
4. 具有实用价值和可读性"""

    try:
        # Initialize components
        openai_client = OpenAIClient(api_key, base_url)
        context_manager = ContextManager(args.context_file)

        print("🤖 正在分析用户意图...")

        # Step 1: Parse user intent
        intent = parse_user_intent(openai_client, args.user_input, model)
        print(f"✅ 用户意图分析完成：{intent[:100]}...")

        # Step 2: Save intent to context
        context_number = context_manager.add_context(intent)
        print(f"💾 意图已保存到上下文文件，编号：{context_number}")

        # Step 3: Get latest contexts
        latest_contexts = context_manager.get_latest_contexts(3)
        print(f"📚 已获取最新 {len(latest_contexts)} 条上下文")

        # Step 4: Generate final content
        print("🔄 正在生成最终内容...")
        final_content = generate_final_content(openai_client, args.user_input, latest_contexts, system_prompt, model)

        print("\n" + "="*60)
        print("🎯 生成的内容：")
        print("="*60)
        print(final_content)
        print("="*60)

        return 0

    except Exception as e:
        print(f"❌ 错误：{str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())