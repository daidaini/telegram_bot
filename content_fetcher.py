#!/usr/bin/env python3
"""
Web Content Fetcher using BeautifulSoup

This module provides robust web content extraction using BeautifulSoup
with intelligent content detection and cleaning.
"""

import requests
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Comment
import html5lib

logger = logging.getLogger(__name__)

class ContentFetcher:
    """Robust web content fetcher using BeautifulSoup"""

    def __init__(self, timeout: int = 20):
        """
        Initialize content fetcher

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()

        # Set realistic headers to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def fetch_content(self, url: str, max_length: int = 15000) -> Optional[str]:
        """
        Fetch and extract main content from a URL

        Args:
            url: URL to fetch
            max_length: Maximum content length

        Returns:
            Extracted text content or None if failed
        """
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                logger.error(f"Invalid URL: {url}")
                return None

            logger.info(f"Fetching content from: {url}")

            # Make HTTP request
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                logger.warning(f"Non-HTML content type: {content_type}")
                # For non-HTML, try to return as text
                return response.text[:max_length]

            # Parse HTML and extract content
            content = self._extract_main_content(response.text, url)

            if content:
                # Limit content length
                if len(content) > max_length:
                    content = content[:max_length] + "...[truncated]"

                logger.info(f"Successfully extracted {len(content)} characters")
                return content
            else:
                logger.warning("No content extracted from page")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    def _extract_main_content(self, html: str, url: str) -> Optional[str]:
        """
        Extract main content from HTML using intelligent detection

        Args:
            html: HTML content
            url: Source URL for reference

        Returns:
            Extracted text content
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(html, 'html5lib')

            # Remove unwanted elements
            self._remove_unwanted_elements(soup)

            # Try to find main content using various strategies
            content = self._find_main_content(soup)

            # Clean and format the content
            if content:
                return self._clean_text(content)
            else:
                # Fallback to body text
                return self._clean_text(soup.get_text())

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return None

    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove unwanted elements from the page"""
        # Tags to remove completely
        unwanted_tags = [
            'script', 'style', 'noscript', 'iframe', 'embed', 'object',
            'nav', 'header', 'footer', 'aside', 'advertisement'
        ]

        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove elements with common ad/class identifiers
        unwanted_classes = [
            'ad', 'advertisement', 'ads', 'sidebar', 'menu', 'navigation',
            'footer', 'header', 'social', 'share', 'comments', 'popup'
        ]

        for class_name in unwanted_classes:
            for element in soup.find_all(class_=re.compile(class_name, re.I)):
                element.decompose()

    def _find_main_content(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Find main content using various strategies
        """
        strategies = [
            self._content_by_common_selectors,
            self._content_by_largest_text_block,
            self._content_by_article_tag,
            self._content_by_heuristics
        ]

        for strategy in strategies:
            try:
                content = strategy(soup)
                if content and len(content.strip()) > 100:  # Minimum content length
                    return content
            except Exception as e:
                logger.debug(f"Content strategy failed: {e}")
                continue

        return None

    def _content_by_common_selectors(self, soup: BeautifulSoup) -> Optional[str]:
        """Find content using common content selectors"""
        selectors = [
            'article', 'main', '[role="main"]', '.content', '.post-content',
            '.entry-content', '.article-content', '.story-body', '.post-body'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text()

        return None

    def _content_by_largest_text_block(self, soup: BeautifulSoup) -> Optional[str]:
        """Find the largest text block"""
        text_blocks = []

        # Common text container tags
        for tag in ['p', 'div', 'section']:
            for element in soup.find_all(tag):
                text = element.get_text(strip=True)
                if len(text) > 200:  # Only consider substantial blocks
                    text_blocks.append((len(text), text))

        if text_blocks:
            # Return the largest text block
            text_blocks.sort(key=lambda x: x[0], reverse=True)
            return text_blocks[0][1]

        return None

    def _content_by_article_tag(self, soup: BeautifulSoup) -> Optional[str]:
        """Find content within article tags"""
        article = soup.find('article')
        if article:
            return article.get_text()
        return None

    def _content_by_heuristics(self, soup: BeautifulSoup) -> Optional[str]:
        """Use heuristics to find content"""
        # Look for elements with high text-to-HTML ratio
        best_element = None
        best_ratio = 0

        for element in soup.find_all(['div', 'section', 'p']):
            text = element.get_text(strip=True)
            html = str(element)

            if len(text) > 100 and len(html) > 0:
                ratio = len(text) / len(html)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_element = element

        if best_element and best_ratio > 0.3:  # Reasonable text ratio threshold
            return best_element.get_text()

        return None

    def _clean_text(self, text: str) -> str:
        """
        Clean and format extracted text
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove excessive newlines (keep reasonable paragraphs)
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)

        # Join with double newlines for paragraphs
        result = '\n\n'.join(cleaned_lines)

        # Remove common artifacts
        artifacts = [
            r'Share this article.*?$',
            r'Related articles.*?$',
            r'Leave a comment.*?$',
            r'Advertisement.*?$',
            r'\[.*?\]',  # Remove bracketed text (often metadata)
        ]

        for artifact in artifacts:
            result = re.sub(artifact, '', result, flags=re.I | re.MULTILINE)

        return result.strip()

    def test_fetch(self, url: str) -> bool:
        """
        Test if content fetching works for a URL

        Args:
            url: Test URL

        Returns:
            True if successful, False otherwise
        """
        try:
            content = self.fetch_content(url, max_length=500)
            return content is not None and len(content) > 50
        except Exception as e:
            logger.error(f"Test fetch failed: {e}")
            return False

def create_content_fetcher() -> ContentFetcher:
    """
    Create a configured content fetcher instance

    Returns:
        ContentFetcher instance
    """
    return ContentFetcher()