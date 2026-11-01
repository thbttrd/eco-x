"""Unit tests for NewsParser.

Tests cover:
- RSS feed detection and parsing
- CSS selector parsing
- XPath parsing
- Main content fallback parsing
- Article deduplication
- URL normalization
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ecox_platform.news.parser import NewsParser, ParsedArticle


class TestNewsParser:
    """Tests for NewsParser."""

    @pytest.fixture
    def parser(self) -> NewsParser:
        """Create parser instance."""
        return NewsParser()

    def test_deduplicate_articles_removes_duplicates(self, parser: NewsParser) -> None:
        """Test that duplicate articles are removed based on URL."""
        articles = [
            ParsedArticle(title="Article 1", url="https://example.com/article1"),
            ParsedArticle(title="Article 1 Copy", url="https://example.com/article1"),
            ParsedArticle(title="Article 2", url="https://example.com/article2"),
        ]

        unique = parser._deduplicate_articles(articles)

        assert len(unique) == 2
        assert unique[0].title == "Article 1"
        assert unique[1].title == "Article 2"

    def test_normalize_url_removes_trailing_slashes(self, parser: NewsParser) -> None:
        """Test URL normalization."""
        url = "https://example.com/article/"
        normalized = parser._normalize_url(url)

        assert normalized == "example.com/article"

    def test_is_article_link_filters_navigation_links(self, parser: NewsParser) -> None:
        """Test that navigation/social links are filtered out."""
        base_url = "https://example.com"

        # Should be filtered
        assert not parser._is_article_link("#section", "Jump to", base_url)
        assert not parser._is_article_link("javascript:void(0)", "Click", base_url)
        assert not parser._is_article_link("/login", "Login Now", base_url)
        assert not parser._is_article_link("https://twitter.com/share", "Share", base_url)

        # Short text should be filtered
        assert not parser._is_article_link("/valid", "Hi", base_url)

    def test_is_article_link_accepts_valid_links(self, parser: NewsParser) -> None:
        """Test that valid article links are accepted."""
        base_url = "https://example.com"

        assert parser._is_article_link(
            "/news/article-title",
            "This is a valid article headline",
            base_url,
        )

    def test_is_article_link_filters_external_domains(self, parser: NewsParser) -> None:
        """Test that links to different domains are filtered."""
        base_url = "https://example.com"

        assert not parser._is_article_link(
            "https://other-site.com/article",
            "Article on another site here",
            base_url,
        )

    def test_detect_rss_feed_from_link_tag(self, parser: NewsParser) -> None:
        """Test RSS feed detection from link tag."""
        html = """
        <html>
        <head>
            <link rel="alternate" type="application/rss+xml" href="/feed.xml">
        </head>
        <body></body>
        </html>
        """

        rss_url = parser._detect_rss_feed(html, "https://example.com")

        assert rss_url == "https://example.com/feed.xml"

    def test_detect_rss_feed_from_atom_link(self, parser: NewsParser) -> None:
        """Test Atom feed detection from link tag."""
        html = """
        <html>
        <head>
            <link rel="alternate" type="application/atom+xml" href="/atom.xml">
        </head>
        <body></body>
        </html>
        """

        rss_url = parser._detect_rss_feed(html, "https://example.com")

        assert rss_url == "https://example.com/atom.xml"

    def test_detect_rss_feed_returns_none_when_not_found(self, parser: NewsParser) -> None:
        """Test that None is returned when no RSS feed is found."""
        html = "<html><head></head><body></body></html>"

        rss_url = parser._detect_rss_feed(html, "https://example.com")

        assert rss_url is None

    @pytest.mark.asyncio
    async def test_parse_rss_success(self, parser: NewsParser) -> None:
        """Test RSS parsing with valid feed."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                "title": "Article 1",
                "link": "https://example.com/article1",
                "published_parsed": (2024, 1, 15, 10, 30, 0, 0, 0, 0),
            },
            {
                "title": "Article 2",
                "link": "https://example.com/article2",
            },
        ]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_feed

            articles = await parser._parse_rss("https://example.com/feed.xml")

        assert len(articles) == 2
        assert articles[0].title == "Article 1"
        assert articles[0].url == "https://example.com/article1"
        assert articles[1].title == "Article 2"

    @pytest.mark.asyncio
    async def test_parse_rss_handles_bozo_error(self, parser: NewsParser) -> None:
        """Test RSS parsing handles invalid feed gracefully."""
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.entries = []
        mock_feed.bozo_exception = Exception("Parse error")

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_feed

            articles = await parser._parse_rss("https://example.com/bad-feed.xml")

        assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_parse_rss_handles_exception(self, parser: NewsParser) -> None:
        """Test RSS parsing handles exceptions."""
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("Network error")

            articles = await parser._parse_rss("https://example.com/feed.xml")

        assert len(articles) == 0

    def test_parse_css_extracts_articles(self, parser: NewsParser) -> None:
        """Test CSS selector parsing."""
        html = """
        <html>
        <body>
            <div class="article">
                <a href="/article1">First Article Title</a>
            </div>
            <div class="article">
                <a href="/article2">Second Article Title</a>
            </div>
        </body>
        </html>
        """

        articles = parser._parse_css(html, "div.article", "https://example.com")

        assert len(articles) == 2
        assert articles[0].title == "First Article Title"
        assert articles[0].url == "https://example.com/article1"

    def test_parse_css_extracts_from_heading(self, parser: NewsParser) -> None:
        """Test CSS selector parsing extracts title from heading."""
        html = """
        <html>
        <body>
            <div class="article">
                <h2>Article Headline</h2>
                <a href="/article1">Read more</a>
            </div>
        </body>
        </html>
        """

        articles = parser._parse_css(html, "div.article", "https://example.com")

        assert len(articles) == 1
        assert articles[0].title == "Article Headline"

    def test_parse_xpath_extracts_articles(self, parser: NewsParser) -> None:
        """Test XPath parsing."""
        html = """
        <html>
        <body>
            <div class="article">
                <a href="/article1">First Article</a>
            </div>
            <div class="article">
                <a href="/article2">Second Article</a>
            </div>
        </body>
        </html>
        """

        articles = parser._parse_xpath(html, "//div[@class='article']", "https://example.com")

        assert len(articles) == 2
        assert articles[0].title == "First Article"

    def test_parse_main_content_fallback(self, parser: NewsParser) -> None:
        """Test main content fallback parsing."""
        html = """
        <html>
        <body>
            <main>
                <a href="/news/article1">This is a news article headline</a>
                <a href="/news/article2">Another news article headline here</a>
            </main>
        </body>
        </html>
        """

        articles = parser._parse_main_content(html, "https://example.com")

        assert len(articles) == 2

    @pytest.mark.asyncio
    async def test_parse_uses_rss_when_available(self, parser: NewsParser) -> None:
        """Test that RSS is preferred when detected."""
        html = """
        <html>
        <head>
            <link rel="alternate" type="application/rss+xml" href="/feed.xml">
        </head>
        <body>
            <div class="article">
                <a href="/html-article">HTML Article</a>
            </div>
        </body>
        </html>
        """

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {"title": "RSS Article", "link": "https://example.com/rss-article"},
        ]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_feed

            articles = await parser.parse(html, "https://example.com")

        assert len(articles) == 1
        assert articles[0].title == "RSS Article"

    @pytest.mark.asyncio
    async def test_parse_falls_back_to_selector(self, parser: NewsParser) -> None:
        """Test that CSS selector is used when RSS not available."""
        html = """
        <html>
        <body>
            <div class="article">
                <a href="/article1">Article from selector</a>
            </div>
        </body>
        </html>
        """

        articles = await parser.parse(html, "https://example.com", parse_selector="div.article")

        assert len(articles) == 1
        assert articles[0].title == "Article from selector"
