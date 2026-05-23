"""Typed exceptions for basquethero ingest pipeline.

Three failure modes:

- `BasqueteroFetchError` — HTTP-level (network, status code, retry exhausted).
- `BasqueteroParseError` — schema-level (RSC payload missing expected key, or
  page structure drifted from what the parser was tuned against).
- `BasqueteroError` — base class for any other ingest failure.

All three are non-fatal at the CLI layer: caller is expected to log the
exception (including the contextual fields below) and exit with a non-zero
status, so the operator can inspect the raw cache directory and fix the
parser or re-run the fetch.
"""

from __future__ import annotations


class BasqueteroError(Exception):
    """Base exception for any basquethero ingest failure."""


class BasqueteroFetchError(BasqueteroError):
    """HTTP-level failure during fetch (network, non-2xx, retry exhausted)."""

    def __init__(self, url: str, status: int | None, attempt: int) -> None:
        self.url = url
        self.status = status
        self.attempt = attempt
        status_str = str(status) if status is not None else "no-response"
        super().__init__(
            f"basquethero fetch failed: url={url} status={status_str} attempt={attempt}"
        )


class BasqueteroParseError(BasqueteroError):
    """Schema-level failure parsing RSC payload or page structure."""

    def __init__(
        self,
        raw_path: str,
        missing_key: str,
        expected_format: str,
    ) -> None:
        self.raw_path = raw_path
        self.missing_key = missing_key
        self.expected_format = expected_format
        super().__init__(
            f"basquethero parse failed: raw_path={raw_path} "
            f"missing_key={missing_key} expected_format={expected_format}"
        )
