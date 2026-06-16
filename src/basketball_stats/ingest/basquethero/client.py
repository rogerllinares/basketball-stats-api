"""Synchronous stdlib HTTP client for basquethero.cat (D2.5-02 relaxed, D2.5-09 zero deps).

The basquethero v2 source serves one ~1.3 MB HTML page per league calendar
and a similar weight per `/equipos`, `/jugadores`. We fetch a handful of
URLs per scrape — there is no fan-out, no concurrent batch, no need for
async. Stdlib `urllib.request` keeps the dep budget at zero.

Behaviour:

- `BasqueteroClient.fetch(path)` returns `bytes`. Raises `BasqueteroFetchError`
  on terminal failure (5 retries exhausted, non-2xx after retry, or network).
- Retry policy: exponential backoff `2 ** attempt + jitter` seconds.
- Rate limit: sleep `rate_limit_seconds + jitter` between successful fetches
  to be polite to the aggregator.
- UA rotation: picks one of `DEFAULT_UA_POOL` per request. No googlebot
  impersonation; real Chrome/Firefox UAs only.
"""

from __future__ import annotations

import logging
import random
import time
import urllib.error
import urllib.request

from basketball_stats.ingest.basquethero.exceptions import BasqueteroFetchError

logger = logging.getLogger(__name__)

DEFAULT_UA_POOL: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:131.0) Gecko/20100101 Firefox/131.0",
)


class BasqueteroClient:
    """One client per scrape session. Holds rate-limit state."""

    def __init__(
        self,
        base_url: str = "https://www.basquethero.cat",
        *,
        rate_limit_seconds: float = 1.0,
        jitter_range: tuple[float, float] = (0.0, 0.5),
        user_agents: tuple[str, ...] = DEFAULT_UA_POOL,
        max_retries: int = 5,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.rate_limit_seconds = rate_limit_seconds
        self.jitter_range = jitter_range
        self.user_agents = user_agents
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self._last_fetch_at: float | None = None

    def _build_url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def _wait_for_rate_limit(self) -> None:
        if self._last_fetch_at is None:
            return
        elapsed = time.monotonic() - self._last_fetch_at
        sleep_for = self.rate_limit_seconds - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for + random.uniform(*self.jitter_range))

    def _pick_user_agent(self) -> str:
        return random.choice(self.user_agents)

    def fetch(self, path: str) -> bytes:
        url = self._build_url(path)
        last_status: int | None = None
        for attempt in range(1, self.max_retries + 1):
            self._wait_for_rate_limit()
            user_agent = self._pick_user_agent()
            req = urllib.request.Request(url, headers={"User-Agent": user_agent})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    body: bytes = resp.read()
                    self._last_fetch_at = time.monotonic()
                    logger.debug(
                        "fetched %s status=%d bytes=%d attempt=%d",
                        url,
                        resp.status,
                        len(body),
                        attempt,
                    )
                    return body
            except urllib.error.HTTPError as e:
                last_status = e.code
                logger.warning("fetch HTTPError %d url=%s attempt=%d", e.code, url, attempt)
                if 400 <= e.code < 500:
                    raise BasqueteroFetchError(url=url, status=e.code, attempt=attempt) from e
            except urllib.error.URLError as e:
                last_status = None
                logger.warning("fetch URLError url=%s attempt=%d err=%s", url, attempt, e)
            backoff = 2**attempt + random.uniform(*self.jitter_range)
            time.sleep(backoff)
        raise BasqueteroFetchError(url=url, status=last_status, attempt=self.max_retries)
