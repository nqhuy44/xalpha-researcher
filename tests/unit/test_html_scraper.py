"""
Unit tests for the HTML Scraper.
"""

from __future__ import annotations

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.data.sources.html_scraper import HTMLScraper, MAX_ARTICLE_CHARS
from src.models.news import NewsArticleDTO
from datetime import datetime, timezone


@pytest.fixture
def mock_article():
    return NewsArticleDTO(
        article_id="123",
        content_hash="abc",
        url="https://example.com/news/1",
        title="Test Article",
        description="Short summary",
        content="Short summary",
        source_name="Test Source",
        domain="tech",
        language="vi",
        published_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc)
    )


class TestHTMLScraper:
    
    @pytest.mark.asyncio
    @patch("src.data.sources.html_scraper.trafilatura.extract")
    async def test_fetch_and_clean_success(self, mock_extract):
        """Test successful fetch and extraction."""
        mock_extract.return_value = "Cleaned article text."
        
        # Mock httpx response
        mock_response = MagicMock()
        mock_response.text = "<html><body>Cleaned article text.</body></html>"
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        scraper = HTMLScraper()
        result = await scraper.fetch_and_clean("https://example.com/news/1", mock_client)
        
        assert result == "Cleaned article text."
        mock_client.get.assert_called_once_with("https://example.com/news/1", follow_redirects=True)
        mock_extract.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.data.sources.html_scraper.trafilatura.extract")
    async def test_fetch_and_clean_truncation(self, mock_extract):
        """Test that extremely long articles are truncated."""
        long_text = "A" * (MAX_ARTICLE_CHARS + 1000)
        mock_extract.return_value = long_text
        
        mock_response = MagicMock()
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        scraper = HTMLScraper()
        result = await scraper.fetch_and_clean("https://example.com/news/2", mock_client)
        
        assert result is not None
        assert len(result) > MAX_ARTICLE_CHARS
        assert result.endswith("[...Bài viết đã được cắt bớt để tối ưu...]")
        assert result.startswith("A" * MAX_ARTICLE_CHARS)

    @pytest.mark.asyncio
    async def test_fetch_and_clean_http_error(self):
        """Test graceful handling of HTTP errors."""
        mock_client = AsyncMock()
        
        # Simulate a 404 Not Found error
        request = httpx.Request("GET", "https://example.com/404")
        response = httpx.Response(status_code=404, request=request)
        error = httpx.HTTPStatusError("Not Found", request=request, response=response)
        
        mock_client.get.side_effect = error
        
        scraper = HTMLScraper()
        result = await scraper.fetch_and_clean("https://example.com/404", mock_client)
        
        assert result is None

    @pytest.mark.asyncio
    @patch("src.data.sources.html_scraper.trafilatura.extract")
    async def test_enrich_articles_success(self, mock_extract, mock_article):
        """Test enriching articles overwrites content on success."""
        mock_extract.return_value = "This is the full lengthy article."
        
        # Mock the internal fetch_and_clean to avoid mocking httpx ContextManagers directly inside enrich_articles
        scraper = HTMLScraper()
        with patch.object(scraper, 'fetch_and_clean', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "This is the full lengthy article."
            
            articles = [mock_article]
            
            assert articles[0].content == "Short summary"
            result = await scraper.enrich_articles(articles)
            
            assert len(result) == 1
            assert result[0].content == "This is the full lengthy article."
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrich_articles_failure_retains_original(self, mock_article):
        """Test enriching articles retains the original summary on failure."""
        scraper = HTMLScraper()
        with patch.object(scraper, 'fetch_and_clean', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None  # Simulating a failure to extract or download
            
            articles = [mock_article]
            
            assert articles[0].content == "Short summary"
            result = await scraper.enrich_articles(articles)
            
            assert len(result) == 1
            # Content should remain the short summary because fetch returned None
            assert result[0].content == "Short summary"
