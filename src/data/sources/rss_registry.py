"""
RSS Source Registry — CRUD operations on the YAML-based source config.

Manages the list of RSS feed sources: add, remove, enable, disable, filter.
Sources are persisted in a YAML file for portability (no DB dependency).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import structlog
import yaml
from pydantic import BaseModel, HttpUrl

logger = structlog.get_logger(__name__)

# Valid domain categories
VALID_DOMAINS = frozenset({
    "finance",
    "geopolitics",
    "law",
    "tech",
    "macro",
    "general",
    "real_estate",
    "banking",
})


class RSSSource(BaseModel):
    """A single RSS feed source definition."""

    name: str
    url: HttpUrl
    domain: str
    language: str = "vi"
    enabled: bool = True
    priority: int = 1  # 1=highest, 5=lowest

    def model_post_init(self, __context: object) -> None:
        """Validate domain after init."""
        if self.domain not in VALID_DOMAINS:
            msg = f"Invalid domain '{self.domain}'. Must be one of: {sorted(VALID_DOMAINS)}"
            raise ValueError(msg)
        if not 1 <= self.priority <= 5:
            msg = f"Priority must be 1-5, got {self.priority}"
            raise ValueError(msg)


class SourceRegistry:
    """
    Manages RSS feed sources via a YAML config file.

    Supports CRUD operations: list, add, remove, enable, disable, update.
    Changes are persisted back to the YAML file on save().

    Usage:
        registry = SourceRegistry(Path("config/sources.yaml"))
        registry.load()
        sources = registry.list_sources(domain="finance", enabled_only=True)
        registry.add_source("New Feed", "https://example.com/rss", "finance")
        registry.save()
    """

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._sources: list[RSSSource] = []

    @property
    def sources(self) -> list[RSSSource]:
        """Read-only access to loaded sources."""
        return list(self._sources)

    def load(self) -> None:
        """
        Load sources from YAML config file.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If YAML structure is invalid.
        """
        if not self._config_path.exists():
            msg = f"Sources config not found: {self._config_path}"
            raise FileNotFoundError(msg)

        raw = yaml.safe_load(self._config_path.read_text(encoding="utf-8"))
        if not raw or "sources" not in raw:
            msg = f"Invalid sources config: missing 'sources' key in {self._config_path}"
            raise ValueError(msg)

        self._sources = []
        for entry in raw["sources"]:
            try:
                source = RSSSource(**entry)
                self._sources.append(source)
            except Exception:
                logger.warning("skipping_invalid_source", entry=entry)

        logger.info("sources_loaded", count=len(self._sources), path=str(self._config_path))

    def save(self) -> None:
        """
        Persist current sources back to YAML config file.

        Creates a backup of the existing file before overwriting.
        """
        if self._config_path.exists():
            backup_path = self._config_path.with_suffix(".yaml.bak")
            shutil.copy2(self._config_path, backup_path)
            logger.debug("config_backup_created", path=str(backup_path))

        data = {
            "sources": [
                {
                    "name": s.name,
                    "url": str(s.url),
                    "domain": s.domain,
                    "language": s.language,
                    "enabled": s.enabled,
                    "priority": s.priority,
                }
                for s in self._sources
            ]
        }

        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        logger.info("sources_saved", count=len(self._sources), path=str(self._config_path))

    def list_sources(
        self,
        *,
        domain: str | None = None,
        enabled_only: bool = True,
        sort_by_priority: bool = True,
    ) -> list[RSSSource]:
        """
        List sources with optional filters.

        Args:
            domain: Filter by domain category (e.g., "finance", "tech").
            enabled_only: If True, return only enabled sources.
            sort_by_priority: If True, sort by priority (1=highest first).

        Returns:
            Filtered and sorted list of RSSSource.
        """
        result = list(self._sources)

        if enabled_only:
            result = [s for s in result if s.enabled]

        if domain:
            result = [s for s in result if s.domain == domain]

        if sort_by_priority:
            result.sort(key=lambda s: s.priority)

        return result

    def get_source(self, name: str) -> RSSSource | None:
        """Get a source by exact name. Returns None if not found."""
        for source in self._sources:
            if source.name == name:
                return source
        return None

    def add_source(
        self,
        name: str,
        url: str,
        domain: str,
        *,
        language: str = "vi",
        enabled: bool = True,
        priority: int = 1,
        auto_save: bool = True,
    ) -> RSSSource:
        """
        Add a new RSS source.

        Args:
            name: Human-readable source name.
            url: RSS feed URL.
            domain: Domain category.
            language: Content language (default: "vi").
            enabled: Whether source is active (default: True).
            priority: Fetch priority 1-5 (default: 1).
            auto_save: Persist to YAML immediately (default: True).

        Returns:
            The newly created RSSSource.

        Raises:
            ValueError: If name or URL already exists.
        """
        # Check duplicates
        for existing in self._sources:
            if existing.name == name:
                msg = f"Source with name '{name}' already exists"
                raise ValueError(msg)
            if str(existing.url) == url:
                msg = f"Source with URL '{url}' already exists (name: '{existing.name}')"
                raise ValueError(msg)

        source = RSSSource(
            name=name,
            url=url,
            domain=domain,
            language=language,
            enabled=enabled,
            priority=priority,
        )
        self._sources.append(source)
        logger.info("source_added", name=name, domain=domain, url=url)

        if auto_save:
            self.save()

        return source

    def remove_source(self, name: str, *, auto_save: bool = True) -> bool:
        """
        Remove a source by name.

        Args:
            name: Source name to remove.
            auto_save: Persist to YAML immediately (default: True).

        Returns:
            True if source was found and removed, False otherwise.
        """
        original_count = len(self._sources)
        self._sources = [s for s in self._sources if s.name != name]

        removed = len(self._sources) < original_count
        if removed:
            logger.info("source_removed", name=name)
            if auto_save:
                self.save()
        else:
            logger.warning("source_not_found", name=name)

        return removed

    def enable_source(self, name: str, *, auto_save: bool = True) -> bool:
        """Enable a source by name. Returns True if found."""
        return self._set_enabled(name, enabled=True, auto_save=auto_save)

    def disable_source(self, name: str, *, auto_save: bool = True) -> bool:
        """Disable a source by name. Returns True if found."""
        return self._set_enabled(name, enabled=False, auto_save=auto_save)

    def update_source(self, name: str, *, auto_save: bool = True, **kwargs: object) -> bool:
        """
        Update fields of an existing source.

        Args:
            name: Source name to update.
            auto_save: Persist to YAML immediately (default: True).
            **kwargs: Fields to update (url, domain, language, enabled, priority).

        Returns:
            True if source was found and updated.
        """
        for i, source in enumerate(self._sources):
            if source.name == name:
                data = source.model_dump()
                data.update(kwargs)
                self._sources[i] = RSSSource(**data)
                logger.info("source_updated", name=name, fields=list(kwargs.keys()))
                if auto_save:
                    self.save()
                return True

        logger.warning("source_not_found", name=name)
        return False

    def get_domains(self) -> list[str]:
        """Get list of all unique domains in current sources."""
        return sorted({s.domain for s in self._sources})

    def get_stats(self) -> dict[str, int]:
        """Get summary statistics about loaded sources."""
        enabled = [s for s in self._sources if s.enabled]
        return {
            "total": len(self._sources),
            "enabled": len(enabled),
            "disabled": len(self._sources) - len(enabled),
            "domains": len(self.get_domains()),
        }

    def _set_enabled(self, name: str, *, enabled: bool, auto_save: bool) -> bool:
        """Internal helper to toggle source enabled state."""
        for source in self._sources:
            if source.name == name:
                # Pydantic models are mutable when not frozen
                source.enabled = enabled
                action = "enabled" if enabled else "disabled"
                logger.info(f"source_{action}", name=name)
                if auto_save:
                    self.save()
                return True

        logger.warning("source_not_found", name=name)
        return False
