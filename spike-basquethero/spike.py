#!/usr/bin/env python3
"""
Phase 2.5 spike — basquethero.cat as data source.

Goal: verify with stdlib-only (urllib + re + json) that we can fetch a
public calendar page from basquethero.cat and extract enough game data
to populate an MVP basketball database.

Decision context:
- Memory `project_basketball_phase_2_5.md`: 11 decisions D2.5-01..11 locked 2026-05-21.
- Original source FCBQ (basquetcatala.cat) blocked by reCAPTCHA v3 wall (STOP).
- Roger AFK decision 2026-05-22 #1: switch to basquethero.cat.

Findings before this spike (Bash probes earlier in this AFK tick):
- robots.txt: User-Agent * Allow / (fully permissive).
- Sitemap: 17,017 URLs at https://www.basquethero.cat/sitemap.xml.
- Roger's league `cc-2a-m` slug matches the site convention.
- Stack: Next.js + React Server Components (RSC) on Vercel.
- Content streamed via `self.__next_f.push([1, "<payload>"])` chunks.

This spike: fetch /liga/cc-2a-m-grup-01/calendario + extract RSC chunks +
parse + look for game entities.

Run: `py spike.py [league_slug]`  (default: cc-2a-m-grup-01)
Stdlib-only: NO pip install required.
"""

import json
import re
import sys
import urllib.error
import urllib.request

UA = "BasketballStatsAPI-spike/0.1 (Roger Llinares, portfolio research)"
TIMEOUT_S = 20


def fetch(url: str) -> str:
    """Fetch URL with UA. Raise on HTTP error. Return decoded text."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return resp.read().decode("utf-8", errors="replace")


# RSC payloads in Next.js look like:
#   <script>self.__next_f.push([1,"<json-stringified-string>"])</script>
# The payload string itself is JSON-stringified (double-escaped). Each push
# can carry one JSON-encoded value, often a numbered chunk index + content.
RSC_RE = re.compile(
    r'self\.__next_f\.push\(\[(\d+),(?:"((?:\\.|[^"\\])*)")?\]\)',
    re.DOTALL,
)


def extract_rsc_chunks(html: str) -> list[tuple[int, str]]:
    """Pull every (index, payload-string) pair from RSC bootstrap chunks."""
    out: list[tuple[int, str]] = []
    for idx_str, raw in RSC_RE.findall(html):
        if not raw:
            continue
        # raw is a JSON string literal; unescape via json.loads of the quoted form
        try:
            payload = json.loads(f'"{raw}"')
        except json.JSONDecodeError:
            continue
        out.append((int(idx_str), payload))
    return out


def walk_for_game_like(obj, hits: list, depth: int = 0):
    """Recursively walk JSON looking for dict nodes that look like games."""
    if depth > 12:
        return
    if isinstance(obj, dict):
        keys = set(obj.keys())
        # Heuristic: a game node usually has team identifiers + scores or date.
        markers = {
            "equipoLocal",
            "equipoVisitante",
            "homeTeam",
            "awayTeam",
            "puntosLocal",
            "puntosVisitante",
            "marcadorLocal",
            "fechaPartido",
            "jornada",
            "matchDate",
            "fixtureDate",
        }
        if len(keys & markers) >= 2:
            hits.append(obj)
        for v in obj.values():
            walk_for_game_like(v, hits, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            walk_for_game_like(v, hits, depth + 1)


def try_decode_payload(payload: str):
    """RSC payloads start with a key like `2:` or `3:I[...]`. The JSON part
    starts after the first colon. Decode best-effort. Return decoded obj or None."""
    if ":" not in payload:
        return None
    head, _, body = payload.partition(":")
    if not body:
        return None
    # Strip leading non-JSON prefix chars (e.g. "I" for imports, "HL" for headers).
    body = body.lstrip("I").lstrip("HL").lstrip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def main():
    league = sys.argv[1] if len(sys.argv) > 1 else "cc-2a-m-grup-01"
    url = f"https://www.basquethero.cat/liga/{league}/calendario"
    print(f"[spike] GET {url}")
    try:
        html = fetch(url)
    except urllib.error.URLError as e:
        print(f"[ERR] fetch failed: {e}", file=sys.stderr)
        sys.exit(2)
    print(f"[spike] response: {len(html)} chars")

    chunks = extract_rsc_chunks(html)
    print(f"[spike] RSC chunks found: {len(chunks)}")
    if not chunks:
        print("[spike] FAIL — no RSC chunks. Page rendering changed or anti-bot triggered.")
        sys.exit(3)

    # Try decoding each payload and walking for game-like nodes.
    game_hits: list = []
    total_decoded = 0
    for _idx, payload in chunks:
        obj = try_decode_payload(payload)
        if obj is None:
            continue
        total_decoded += 1
        walk_for_game_like(obj, game_hits)
    print(f"[spike] decoded payloads: {total_decoded} / {len(chunks)}")
    print(f"[spike] game-like nodes detected: {len(game_hits)}")

    if game_hits:
        print("\n[spike] sample game node #1 (keys + first 800 chars):")
        sample = game_hits[0]
        print(f"  keys: {sorted(sample.keys())[:25]}")
        rendered = json.dumps(sample, ensure_ascii=False, indent=2)[:800]
        print(rendered)

    # Fallback: even without strict game detection, dump key-name frequency
    # to help Roger see what entities are in the page.
    print("\n[spike] top dict-key frequency across all payloads (top 30):")
    freq: dict[str, int] = {}

    def count_keys(o):
        if isinstance(o, dict):
            for k in o:
                freq[k] = freq.get(k, 0) + 1
            for v in o.values():
                count_keys(v)
        elif isinstance(o, list):
            for v in o:
                count_keys(v)

    for _idx, payload in chunks:
        obj = try_decode_payload(payload)
        if obj is not None:
            count_keys(obj)
    top = sorted(freq.items(), key=lambda kv: -kv[1])[:30]
    for k, n in top:
        print(f"  {n:5d}  {k}")

    print("\n[spike] DONE.")
    sys.exit(0 if game_hits else 1)


if __name__ == "__main__":
    main()
