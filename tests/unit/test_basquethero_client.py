"""Unit tests for BasqueteroClient — mocks urllib.request.urlopen.

Covers W4 acceptance: GET request shape, retry on URLError, fail-fast on 4xx.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from basketball_stats.ingest.basquethero.client import BasqueteroClient
from basketball_stats.ingest.basquethero.exceptions import BasqueteroFetchError


def _mock_response(body: bytes, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = body
    resp.status = status
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def test_fetch_returns_bytes_on_2xx() -> None:
    client = BasqueteroClient(rate_limit_seconds=0.0, jitter_range=(0.0, 0.0))
    with patch("urllib.request.urlopen", return_value=_mock_response(b"<html>ok</html>")):
        body = client.fetch("/liga/cc-2a-m-grup-01")
    assert body == b"<html>ok</html>"


def test_fetch_includes_user_agent_header() -> None:
    client = BasqueteroClient(rate_limit_seconds=0.0, jitter_range=(0.0, 0.0))
    captured: dict[str, Any] = {}

    def fake_urlopen(req: Any, **_: Any) -> MagicMock:
        captured["ua"] = req.get_header("User-agent")
        return _mock_response(b"x")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client.fetch("/x")
    assert "Mozilla" in captured["ua"]


def test_fetch_raises_immediately_on_4xx() -> None:
    client = BasqueteroClient(rate_limit_seconds=0.0, jitter_range=(0.0, 0.0), max_retries=3)
    http_err = HTTPError("https://x", 404, "Not Found", hdrs=None, fp=BytesIO(b""))  # type: ignore[arg-type]
    with (
        patch("urllib.request.urlopen", side_effect=http_err),
        pytest.raises(BasqueteroFetchError) as exc_info,
    ):
        client.fetch("/missing")
    assert exc_info.value.status == 404


def test_fetch_retries_on_urlerror_then_raises() -> None:
    client = BasqueteroClient(rate_limit_seconds=0.0, jitter_range=(0.0, 0.0), max_retries=2)
    with (
        patch("urllib.request.urlopen", side_effect=URLError("network down")),
        patch("time.sleep"),
        pytest.raises(BasqueteroFetchError),
    ):
        client.fetch("/x")


def test_build_url_passes_through_absolute() -> None:
    client = BasqueteroClient(base_url="https://www.basquethero.cat")
    assert client._build_url("https://other.cat/x") == "https://other.cat/x"
    assert client._build_url("/liga") == "https://www.basquethero.cat/liga"
    assert client._build_url("liga") == "https://www.basquethero.cat/liga"
