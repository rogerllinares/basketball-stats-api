"""Resumable scrape state (D2.5-08).

`ScrapeState` persists a JSON file at `data/raw/basquethero/<slug>-<season>/
.scrape-state.json`. The file tracks which resources (typically URLs or
relative paths) have been fetched successfully and which failed (with
their error message), so a re-run can skip completed work and retry
failures.

Writes are atomic: write to a `.tmp` sibling + rename. Avoids leaving
half-written JSON if the process crashes mid-fetch.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ScrapeStateData:
    completed_resources: set[str] = field(default_factory=set)
    failed_resources: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "completed_resources": sorted(self.completed_resources),
            "failed_resources": self.failed_resources,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> ScrapeStateData:
        completed_raw = raw.get("completed_resources") or []
        failed_raw = raw.get("failed_resources") or {}
        if not isinstance(completed_raw, list):
            raise TypeError("completed_resources must be a list")
        if not isinstance(failed_raw, dict):
            raise TypeError("failed_resources must be a dict")
        return cls(
            completed_resources={str(r) for r in completed_raw},
            failed_resources={str(k): str(v) for k, v in failed_raw.items()},
        )


class ScrapeState:
    """File-backed wrapper around `ScrapeStateData`. Atomic writes."""

    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self._data: ScrapeStateData | None = None

    def load(self) -> ScrapeStateData:
        if self._data is not None:
            return self._data
        if not self.state_path.is_file():
            self._data = ScrapeStateData()
            return self._data
        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError(f"state file must contain a JSON object, got {type(raw).__name__}")
        self._data = ScrapeStateData.from_dict(raw)
        return self._data

    def _write(self) -> None:
        assert self._data is not None
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(self._data.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp_path, self.state_path)

    def mark_completed(self, resource: str) -> None:
        data = self.load()
        data.completed_resources.add(resource)
        data.failed_resources.pop(resource, None)
        self._write()
        logger.debug("state: completed %s", resource)

    def mark_failed(self, resource: str, error: str) -> None:
        data = self.load()
        data.failed_resources[resource] = error
        self._write()
        logger.debug("state: failed %s err=%s", resource, error)

    def is_completed(self, resource: str) -> bool:
        return resource in self.load().completed_resources

    def retry_failed(self) -> Iterator[str]:
        yield from list(self.load().failed_resources.keys())
