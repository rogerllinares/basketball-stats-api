"""Unit tests for parser helpers — RSC chunks, payload decode, text extraction."""

from __future__ import annotations

from basketball_stats.ingest.basquethero.parser import (
    _extract_text,
    extract_rsc_chunks,
    try_decode_payload,
)


def test_extract_rsc_chunks_finds_push_calls() -> None:
    html = """
    <html><script>
    self.__next_f.push([1,"hello"])
    </script>
    <script>self.__next_f.push([2,"world"])</script>
    </html>
    """
    chunks = extract_rsc_chunks(html)
    assert len(chunks) == 2
    idx1, payload1 = chunks[0]
    idx2, payload2 = chunks[1]
    assert idx1 == 1 and payload1 == "hello"
    assert idx2 == 2 and payload2 == "world"


def test_extract_rsc_chunks_empty_html_returns_empty() -> None:
    assert extract_rsc_chunks("<html></html>") == []


def test_try_decode_payload_returns_none_on_garbage() -> None:
    assert try_decode_payload("not-json-at-all") is None


def test_try_decode_payload_returns_data_on_rsc_format() -> None:
    decoded = try_decode_payload('0:{"key":"value"}')
    assert decoded == {"key": "value"}


def test_try_decode_payload_strips_import_prefix() -> None:
    decoded = try_decode_payload('1:I[42,"chunk"]')
    assert decoded == [42, "chunk"]


def test_try_decode_payload_returns_none_for_plain_json() -> None:
    assert try_decode_payload('{"k": "v"}') is None


def test_extract_text_handles_str_node() -> None:
    assert _extract_text("hello") == "hello"


def test_extract_text_strips_whitespace() -> None:
    assert _extract_text("  hello  ") == "hello"


def test_extract_text_returns_none_for_empty_str() -> None:
    assert _extract_text("   ") is None


def test_extract_text_recurses_into_list() -> None:
    assert _extract_text([None, "", "found", "ignored"]) == "found"


def test_extract_text_returns_none_for_non_str_non_list() -> None:
    assert _extract_text(42) is None
    assert _extract_text({"key": "value"}) is None
