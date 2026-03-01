"""
Unit tests for the News Collection Agent.

Tests SourceRegistry CRUD, ArticleProcessor dedup, and RSSCollector parsing.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from src.data.processing.article_processor import ArticleProcessor
from src.data.sources.rss_collector import RawArticle
from src.data.sources.rss_registry import RSSSource, SourceRegistry


# =============================================================================
# SourceRegistry Tests
# =============================================================================


class TestSourceRegistry:
    """Tests for YAML-based source registry."""

    def _create_registry(self, tmp_path: Path, sources: list[dict] | None = None) -> SourceRegistry:
        """Helper: create a registry with a temp YAML file."""
        config_path = tmp_path / "sources.yaml"
        data = {"sources": sources or []}
        config_path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        registry = SourceRegistry(config_path)
        registry.load()
        return registry

    def test_load_empty(self, tmp_path: Path) -> None:
        """Load an empty sources file."""
        registry = self._create_registry(tmp_path, [])
        assert len(registry.sources) == 0

    def test_load_sources(self, tmp_path: Path) -> None:
        """Load sources from YAML."""
        sources = [
            {"name": "Test Feed", "url": "https://example.com/rss", "domain": "finance"},
            {"name": "Test Feed 2", "url": "https://example2.com/rss", "domain": "tech"},
        ]
        registry = self._create_registry(tmp_path, sources)
        assert len(registry.sources) == 2
        assert registry.sources[0].name == "Test Feed"
        assert registry.sources[1].domain == "tech"

    def test_load_file_not_found(self, tmp_path: Path) -> None:
        """Raise FileNotFoundError for missing config."""
        registry = SourceRegistry(tmp_path / "nonexistent.yaml")
        with pytest.raises(FileNotFoundError):
            registry.load()

    def test_add_source(self, tmp_path: Path) -> None:
        """Add a new source and verify persistence."""
        registry = self._create_registry(tmp_path, [])
        source = registry.add_source("New Feed", "https://new.com/rss", "finance")

        assert source.name == "New Feed"
        assert len(registry.sources) == 1

        # Verify persisted to YAML
        reloaded = SourceRegistry(tmp_path / "sources.yaml")
        reloaded.load()
        assert len(reloaded.sources) == 1
        assert reloaded.sources[0].name == "New Feed"

    def test_add_duplicate_name(self, tmp_path: Path) -> None:
        """Reject duplicate source name."""
        registry = self._create_registry(tmp_path, [
            {"name": "Existing", "url": "https://existing.com/rss", "domain": "finance"},
        ])
        with pytest.raises(ValueError, match="already exists"):
            registry.add_source("Existing", "https://other.com/rss", "tech")

    def test_add_duplicate_url(self, tmp_path: Path) -> None:
        """Reject duplicate source URL."""
        registry = self._create_registry(tmp_path, [
            {"name": "Existing", "url": "https://existing.com/rss", "domain": "finance"},
        ])
        with pytest.raises(ValueError, match="already exists"):
            registry.add_source("Different Name", "https://existing.com/rss", "tech")

    def test_remove_source(self, tmp_path: Path) -> None:
        """Remove a source by name."""
        registry = self._create_registry(tmp_path, [
            {"name": "To Remove", "url": "https://remove.com/rss", "domain": "finance"},
            {"name": "To Keep", "url": "https://keep.com/rss", "domain": "tech"},
        ])
        result = registry.remove_source("To Remove")
        assert result is True
        assert len(registry.sources) == 1
        assert registry.sources[0].name == "To Keep"

    def test_remove_nonexistent(self, tmp_path: Path) -> None:
        """Remove nonexistent source returns False."""
        registry = self._create_registry(tmp_path, [])
        result = registry.remove_source("Ghost")
        assert result is False

    def test_enable_disable_source(self, tmp_path: Path) -> None:
        """Toggle source enabled state."""
        registry = self._create_registry(tmp_path, [
            {"name": "Feed", "url": "https://feed.com/rss", "domain": "finance", "enabled": True},
        ])

        registry.disable_source("Feed")
        assert registry.get_source("Feed").enabled is False

        registry.enable_source("Feed")
        assert registry.get_source("Feed").enabled is True

    def test_list_by_domain(self, tmp_path: Path) -> None:
        """Filter sources by domain."""
        registry = self._create_registry(tmp_path, [
            {"name": "Finance 1", "url": "https://f1.com/rss", "domain": "finance"},
            {"name": "Tech 1", "url": "https://t1.com/rss", "domain": "tech"},
            {"name": "Finance 2", "url": "https://f2.com/rss", "domain": "finance"},
        ])
        finance = registry.list_sources(domain="finance")
        assert len(finance) == 2
        assert all(s.domain == "finance" for s in finance)

    def test_list_enabled_only(self, tmp_path: Path) -> None:
        """Filter out disabled sources."""
        registry = self._create_registry(tmp_path, [
            {"name": "Active", "url": "https://active.com/rss", "domain": "finance", "enabled": True},
            {"name": "Inactive", "url": "https://inactive.com/rss", "domain": "finance", "enabled": False},
        ])
        enabled = registry.list_sources(enabled_only=True)
        assert len(enabled) == 1
        assert enabled[0].name == "Active"

    def test_list_sorted_by_priority(self, tmp_path: Path) -> None:
        """Sources sorted by priority (1=highest first)."""
        registry = self._create_registry(tmp_path, [
            {"name": "Low", "url": "https://low.com/rss", "domain": "finance", "priority": 3},
            {"name": "High", "url": "https://high.com/rss", "domain": "finance", "priority": 1},
            {"name": "Mid", "url": "https://mid.com/rss", "domain": "finance", "priority": 2},
        ])
        sources = registry.list_sources(sort_by_priority=True)
        assert [s.name for s in sources] == ["High", "Mid", "Low"]

    def test_update_source(self, tmp_path: Path) -> None:
        """Update source fields."""
        registry = self._create_registry(tmp_path, [
            {"name": "Feed", "url": "https://feed.com/rss", "domain": "finance", "priority": 3},
        ])
        registry.update_source("Feed", priority=1, domain="tech")
        source = registry.get_source("Feed")
        assert source.priority == 1
        assert source.domain == "tech"

    def test_get_stats(self, tmp_path: Path) -> None:
        """Get registry statistics."""
        registry = self._create_registry(tmp_path, [
            {"name": "A", "url": "https://a.com/rss", "domain": "finance", "enabled": True},
            {"name": "B", "url": "https://b.com/rss", "domain": "tech", "enabled": True},
            {"name": "C", "url": "https://c.com/rss", "domain": "finance", "enabled": False},
        ])
        stats = registry.get_stats()
        assert stats["total"] == 3
        assert stats["enabled"] == 2
        assert stats["disabled"] == 1
        assert stats["domains"] == 2

    def test_invalid_domain(self, tmp_path: Path) -> None:
        """Reject invalid domain."""
        registry = self._create_registry(tmp_path, [])
        with pytest.raises(ValueError, match="Invalid domain"):
            registry.add_source("Bad", "https://bad.com/rss", "invalid_domain")

    def test_invalid_priority(self, tmp_path: Path) -> None:
        """Reject invalid priority."""
        registry = self._create_registry(tmp_path, [])
        with pytest.raises(ValueError, match="Priority must be 1-5"):
            registry.add_source("Bad", "https://bad.com/rss", "finance", priority=10)


# =============================================================================
# ArticleProcessor Tests
# =============================================================================


class TestArticleProcessor:
    """Tests for article normalization and deduplication."""

    def _make_raw(
        self,
        title: str = "Test Article",
        link: str = "https://example.com/article",
        summary: str = "Test summary",
        content: str = "",
        domain: str = "finance",
        published_at: datetime | None = None,
    ) -> RawArticle:
        """Helper: create a RawArticle."""
        return RawArticle(
            source_name="Test Source",
            source_url="https://example.com/rss",
            title=title,
            link=link,
            summary=summary,
            content=content,
            published_at=published_at or datetime.now(tz=timezone.utc),
            domain=domain,
            language="vi",
        )

    def test_process_single(self) -> None:
        """Process a single article."""
        processor = ArticleProcessor()
        result = processor.process([self._make_raw()])
        assert result.total_input == 1
        assert result.total_output == 1
        assert result.duplicates_removed == 0
        assert len(result.articles) == 1

    def test_process_empty(self) -> None:
        """Process empty list."""
        processor = ArticleProcessor()
        result = processor.process([])
        assert result.total_output == 0

    def test_dedup_same_title_link(self) -> None:
        """Deduplicate articles with same title and link."""
        processor = ArticleProcessor()
        articles = [
            self._make_raw(title="Same Title", link="https://same.com/article"),
            self._make_raw(title="Same Title", link="https://same.com/article"),
        ]
        result = processor.process(articles)
        assert result.total_output == 1
        assert result.duplicates_removed == 1

    def test_different_articles_kept(self) -> None:
        """Keep articles with different titles or links."""
        processor = ArticleProcessor()
        articles = [
            self._make_raw(title="Article A", link="https://a.com"),
            self._make_raw(title="Article B", link="https://b.com"),
        ]
        result = processor.process(articles)
        assert result.total_output == 2

    def test_html_cleanup(self) -> None:
        """Strip HTML tags from content."""
        processor = ArticleProcessor()
        raw = self._make_raw(
            title="<b>Bold Title</b>",
            summary="<p>Paragraph with <a href='#'>link</a></p>",
            content="<div>Content</div>",
        )
        result = processor.process([raw])
        article = result.articles[0]
        assert "<" not in article.title
        assert "Bold Title" in article.title
        assert "<" not in article.description

    def test_html_entity_unescape(self) -> None:
        """Unescape HTML entities."""
        processor = ArticleProcessor()
        raw = self._make_raw(title="AT&amp;T &lt;news&gt;")
        result = processor.process([raw])
        assert "AT&T" in result.articles[0].title
        assert "<news>" in result.articles[0].title

    def test_cross_batch_dedup(self) -> None:
        """Known hashes prevent re-processing across batches."""
        processor = ArticleProcessor()

        # First batch
        batch1 = [self._make_raw(title="Repeated", link="https://repeated.com")]
        result1 = processor.process(batch1)
        assert result1.total_output == 1

        # Second batch with same article
        batch2 = [self._make_raw(title="Repeated", link="https://repeated.com")]
        result2 = processor.process(batch2)
        assert result2.total_output == 0
        assert result2.duplicates_removed == 1

    def test_known_hashes_init(self) -> None:
        """Initialize with pre-existing hashes."""
        # Compute hash for "test|https://test.com"
        import hashlib

        known = hashlib.sha256("test|https://test.com".encode()).hexdigest()[:16]
        processor = ArticleProcessor(known_hashes={known})

        raw = self._make_raw(title="Test", link="https://test.com")
        result = processor.process([raw])
        # Note: hash is based on lowercase title, so "test" matches "Test"
        assert result.total_output == 0

    def test_content_fallback_to_summary(self) -> None:
        """Use summary as content when content is empty."""
        processor = ArticleProcessor()
        raw = self._make_raw(content="", summary="Summary text here")
        result = processor.process([raw])
        assert result.articles[0].content == "Summary text here"

    def test_article_has_uuid(self) -> None:
        """Each processed article gets a UUID."""
        processor = ArticleProcessor()
        result = processor.process([self._make_raw()])
        article = result.articles[0]
        assert len(article.article_id) == 36  # UUID format

    def test_ingested_at_set(self) -> None:
        """ingested_at timestamp is set on processing."""
        processor = ArticleProcessor()
        result = processor.process([self._make_raw()])
        assert result.articles[0].ingested_at is not None


# =============================================================================
# RSSSource Model Tests
# =============================================================================


class TestRSSSource:
    """Tests for the RSSSource Pydantic model."""

    def test_valid_source(self) -> None:
        """Create a valid source."""
        source = RSSSource(
            name="Test",
            url="https://example.com/rss",
            domain="finance",
        )
        assert source.enabled is True
        assert source.priority == 1
        assert source.language == "vi"

    def test_invalid_domain_raises(self) -> None:
        """Invalid domain raises ValueError."""
        with pytest.raises(ValueError):
            RSSSource(name="Bad", url="https://bad.com", domain="invalid")

    def test_invalid_priority_raises(self) -> None:
        """Priority out of range raises ValueError."""
        with pytest.raises(ValueError):
            RSSSource(name="Bad", url="https://bad.com", domain="finance", priority=0)
