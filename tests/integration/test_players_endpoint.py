"""GET /api/v1/players slug + by-id + stats — READ-05 + READ-06.

Anchor: 99001-5-marc-soler must resolve to the first seed player row.
"""

import httpx
import pytest


@pytest.mark.asyncio
async def test_player_slug_resolves_marc_soler(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/api/v1/players/99001-5-marc-soler")
    assert response.status_code == 200
    body = response.json()
    assert body["license_id"] == 99001
    assert body["dorsal_default"] == 5
    assert body["display_name"] == "Marc Soler"


@pytest.mark.asyncio
async def test_player_slug_malformed_returns_422(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/api/v1/players/not-a-valid-slug")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_player_slug_not_found_returns_404(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/api/v1/players/12345-99-no-such-player")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_player_stats_endpoint(async_client: httpx.AsyncClient) -> None:
    # Player id=1 (first row from seed) has 1 box-score from the seed game.
    response = await async_client.get("/api/v1/players/by-id/1/stats?season_id=1")
    assert response.status_code == 200
    body = response.json()
    assert body["games_played"] >= 1
    assert body["pts_total"] >= 0
