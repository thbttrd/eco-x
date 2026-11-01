"""News article parser with multiple parsing strategies.

Supports:
1. RSS/Atom feeds (preferred when available)
2. CSS selectors (default for configured parse_selector)
3. XPath expressions (prefix with 'xpath:')
4. Link extraction fallback (extract all links from main content)
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import feedparser  # type: ignore[import-untyped]
import structlog
from bs4 import BeautifulSoup
from lxml import etree  # type: ignore[import-untyped]

logger = structlog.get_logger()


@dataclass
class ParsedArticle:
    """An article extracted from a news source."""

    title: str
    url: str
    published_at: datetime | None = None


class NewsParser:
    """Parser for extracting articles from news source pages."""

    # Common RSS/Atom feed paths to check
    COMMON_FEED_PATHS = [
        "/feed",
        "/rss",
        "/feed.xml",
        "/rss.xml",
        "/atom.xml",
        "/feeds/posts/default",
        "/index.xml",
    ]

    def __init__(self) -> None:
        """Initialize the parser."""
        pass

    async def parse(
        self,
        html: str,
        source_url: str,
        parse_selector: str | None = None,
    ) -> list[ParsedArticle]:
        """Parse articles from HTML content.

        Strategy (in priority order):
        1. Try to detect and parse RSS/Atom feed (always preferred)
        2. Use configured parse_selector (CSS or XPath)
        3. Fall back to extracting main content links

        Args:
            html: Raw HTML content of the page
            source_url: Base URL of the source (for resolving relative URLs)
            parse_selector: Optional CSS selector or 'xpath:...' expression

        Returns:
            List of ParsedArticle objects
        """
        # 1. Try RSS detection first (preferred)
        rss_url = self._detect_rss_feed(html, source_url)
        if rss_url:
            articles = await self._parse_rss(rss_url)
            if articles:
                logger.debug(
                    "Parsed articles from RSS",
                    source=source_url,
                    rss_url=rss_url,
                    count=len(articles),
                )
                return articles

        # 2. Use configured selector
        if parse_selector:
            if parse_selector.startswith("xpath:"):
                xpath_expr = parse_selector[6:].strip()
                articles = self._parse_xpath(html, xpath_expr, source_url)
            else:
                articles = self._parse_css(html, parse_selector, source_url)

            if articles:
                logger.debug(
                    "Parsed articles with selector",
                    source=source_url,
                    selector=parse_selector[:50],
                    count=len(articles),
                )
                return articles

        # 3. Fallback: extract main content links
        articles = self._parse_main_content(html, source_url)
        logger.debug(
            "Parsed articles from main content",
            source=source_url,
            count=len(articles),
        )
        return articles

    def _detect_rss_feed(self, html: str, base_url: str) -> str | None:
        """Detect RSS/Atom feed URL from HTML or common paths.

        Checks:
        1. <link rel="alternate" type="application/rss+xml">
        2. <link rel="alternate" type="application/atom+xml">
        3. Common feed paths (/feed, /rss, etc.)
        """
        soup = BeautifulSoup(html, "lxml")

        # Check for RSS link tags
        for link_type in ["application/rss+xml", "application/atom+xml"]:
            link = soup.find("link", rel="alternate", type=link_type)
            if link and link.get("href"):
                return urljoin(base_url, str(link["href"]))

        # Check for common feed paths in the HTML
        for path in self.COMMON_FEED_PATHS:
            # Check if there's a link pointing to this path
            for a in soup.find_all("a", href=True):
                href = str(a["href"])
                if path in href.lower() or "rss" in href.lower() or "feed" in href.lower():
                    return urljoin(base_url, href)

        return None

    async def _parse_rss(self, feed_url: str) -> list[ParsedArticle]:
        """Parse articles from an RSS/Atom feed."""
        try:
            # Run feedparser in thread pool to avoid blocking the event loop
            feed = await asyncio.to_thread(feedparser.parse, feed_url)

            if feed.bozo and not feed.entries:
                logger.warning(
                    "Failed to parse RSS feed", url=feed_url, error=str(feed.bozo_exception)
                )
                return []

            articles = []
            for entry in feed.entries:
                # feedparser lacks type stubs - entry.get() returns strings, not FeedParserDict
                title = entry.get("title", "").strip()  # type: ignore[union-attr]
                link = entry.get("link", "")

                if not title or not link:
                    continue

                # Parse publication date
                published_at = None
                for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
                    if date_tuple := entry.get(date_field):
                        try:
                            # date_tuple is a time.struct_time (9-tuple of ints)
                            published_at = datetime(*date_tuple[:6])  # type: ignore[arg-type]
                            break
                        except (ValueError, TypeError):
                            continue

                articles.append(
                    ParsedArticle(
                        title=title,
                        url=link,  # type: ignore[arg-type]
                        published_at=published_at,
                    )
                )

            return articles

        except Exception as e:
            logger.warning("RSS parsing error", url=feed_url, error=str(e))
            return []

    def _parse_css(
        self,
        html: str,
        selector: str,
        base_url: str,
    ) -> list[ParsedArticle]:
        """Parse articles using CSS selector."""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        try:
            elements = soup.select(selector)

            for element in elements:
                # Try to extract link and title
                article = self._extract_article_from_element(element, base_url)
                if article:
                    articles.append(article)

        except Exception as e:
            logger.warning("CSS selector parsing error", selector=selector, error=str(e))

        return self._deduplicate_articles(articles)

    def _parse_xpath(
        self,
        html: str,
        xpath_expr: str,
        base_url: str,
    ) -> list[ParsedArticle]:
        """Parse articles using XPath expression."""
        articles = []

        try:
            tree = etree.HTML(html)
            if tree is None:
                return []

            elements = tree.xpath(xpath_expr)

            for element in elements:
                article = self._extract_article_from_lxml_element(element, base_url)
                if article:
                    articles.append(article)

        except Exception as e:
            logger.warning("XPath parsing error", xpath=xpath_expr, error=str(e))

        return self._deduplicate_articles(articles)

    def _parse_main_content(
        self,
        html: str,
        base_url: str,
    ) -> list[ParsedArticle]:
        """Extract articles from main content area as fallback."""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # Try to find main content area
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id="content")
            or soup.find(class_="content")
            or soup.find("div", class_="main")
            or soup.body
        )

        if not main_content:
            return []

        # Extract all links with meaningful text
        for a in main_content.find_all("a", href=True):
            href = str(a["href"])
            text = a.get_text(strip=True)

            # Filter out navigation/footer links
            if not self._is_article_link(href, text, base_url):
                continue

            url = urljoin(base_url, href)
            articles.append(ParsedArticle(title=text, url=url))

        return self._deduplicate_articles(articles)

    def _extract_article_from_element(
        self,
        element: Any,
        base_url: str,
    ) -> ParsedArticle | None:
        """Extract article info from a BeautifulSoup element."""
        # If element is an <a> tag
        if element.name == "a":
            href = element.get("href")
            text = element.get_text(strip=True)
            if href and text:
                return ParsedArticle(
                    title=text,
                    url=urljoin(base_url, str(href)),
                )

        # Look for <a> tag inside element
        a_tag = element.find("a", href=True)
        if a_tag:
            href = a_tag.get("href")
            # Try to get title from heading or link text
            title = None
            for heading in element.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                title = heading.get_text(strip=True)
                if title:
                    break

            if not title:
                title = a_tag.get_text(strip=True)

            if href and title:
                return ParsedArticle(
                    title=title,
                    url=urljoin(base_url, str(href)),
                )

        return None

    def _extract_article_from_lxml_element(
        self,
        element: Any,
        base_url: str,
    ) -> ParsedArticle | None:
        """Extract article info from an lxml element."""
        try:
            # If element is an <a> tag
            if hasattr(element, "tag") and element.tag == "a":
                href = element.get("href")
                text = "".join(element.itertext()).strip()
                if href and text:
                    return ParsedArticle(
                        title=text,
                        url=urljoin(base_url, str(href)),
                    )

            # Look for <a> tag inside element
            a_tags = element.xpath(".//a[@href]")
            if a_tags:
                a_tag = a_tags[0]
                href = a_tag.get("href")

                # Try to get title from heading or link text
                title = None
                for heading_tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    headings = element.xpath(f".//{heading_tag}")
                    if headings:
                        title = "".join(headings[0].itertext()).strip()
                        if title:
                            break

                if not title:
                    title = "".join(a_tag.itertext()).strip()

                if href and title:
                    return ParsedArticle(
                        title=title,
                        url=urljoin(base_url, str(href)),
                    )

        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to extract article from lxml element", error=str(e))

        return None

    def _is_article_link(self, href: str, text: str, base_url: str) -> bool:
        """Check if a link is likely an article link."""
        # Skip empty or very short text
        if not text or len(text) < 10:
            return False

        # Skip anchors and javascript
        if href.startswith("#") or href.startswith("javascript:"):
            return False

        # Skip common navigation patterns
        skip_patterns = [
            "login",
            "sign",
            "register",
            "contact",
            "about",
            "privacy",
            "terms",
            "cookie",
            "subscribe",
            "twitter",
            "facebook",
            "linkedin",
            "youtube",
            "instagram",
        ]
        href_lower = href.lower()
        text_lower = text.lower()
        for pattern in skip_patterns:
            if pattern in href_lower or pattern in text_lower:
                return False

        # Prefer links that stay on the same domain
        parsed_base = urlparse(base_url)
        parsed_href = urlparse(urljoin(base_url, href))
        if parsed_href.netloc and parsed_href.netloc != parsed_base.netloc:
            return False

        return True

    def _deduplicate_articles(
        self,
        articles: list[ParsedArticle],
    ) -> list[ParsedArticle]:
        """Remove duplicate articles by URL."""
        seen_urls: set[str] = set()
        unique_articles: list[ParsedArticle] = []

        for article in articles:
            # Normalize URL for comparison
            normalized = self._normalize_url(article.url)
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                unique_articles.append(article)

        return unique_articles

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        parsed = urlparse(url)
        # Remove trailing slashes, lowercase
        path = parsed.path.rstrip("/").lower()
        return f"{parsed.netloc}{path}"
