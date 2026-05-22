"""Unit tests for ScrapeState — atomic write round-trip + schema."""

from __future__ import annotations

from pathlib import Path

import pytest

from basketball_stats.ingest.basquethero.state import ScrapeState, ScrapeStateData


def test_scrape_state_data_roundtrip() -> None:
    data = ScrapeStateData(
        completed_resources={"/a", "/b"},
        failed_resources={"/c": "boom"},
    )
    restored = ScrapeStateData.from_dict(data.to_dict())
    assert restored.completed_resources == {"/a", "/b"}
    assert restored.failed_resources == {"/c": "boom"}


def test_scrape_state_data_from_dict_rejects_non_list_completed() -> None:
    with pytest.raises(TypeError, match="completed_resources"):
        ScrapeStateData.from_dict({"completed_resources": "not-a-list"})


def test_scrape_state_data_from_dict_rejects_non_dict_failed() -> None:
    with pytest.raises(TypeError, match="failed_resources"):
        ScrapeStateData.from_dict({"failed_resources": ["bad"]})


def test_mark_completed_persists_atomic(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state = ScrapeState(state_path)
    state.mark_completed("/liga/cc-2a-m-grup-01")
    assert state_path.is_file()
    fresh = ScrapeState(state_path)
    assert fresh.is_completed("/liga/cc-2a-m-grup-01")
    assert not (tmp_path / "state.json.tmp").exists()


def test_mark_completed_clears_prior_failure(tmp_path: Path) -> None:
    state = ScrapeState(tmp_path / "state.json")
    state.mark_failed("/x", "timeout")
    state.mark_completed("/x")
    fresh = ScrapeState(tmp_path / "state.json")
    data = fresh.load()
    assert "/x" in data.completed_resources
    assert "/x" not in data.failed_resources


def test_retry_failed_yields_only_failed(tmp_path: Path) -> None:
    state = ScrapeState(tmp_path / "state.json")
    state.mark_failed("/a", "err-a")
    state.mark_failed("/b", "err-b")
    state.mark_completed("/c")
    assert set(state.retry_failed()) == {"/a", "/b"}


def test_load_rejects_non_object(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text("[1, 2]", encoding="utf-8")
    state = ScrapeState(state_path)
    with pytest.raises(TypeError, match="JSON object"):
        state.load()
