"""HTTP-layer integration — /api/v1/competitions endpoints with seeded fixture."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_list_competitions_returns_one(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/api/v1/competitions")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["category"] == "1a-territorial"
    # X-Total-Count header (D2-13).
    assert response.headers["x-total-count"] == "1"


@pytest.mark.asyncio
async def test_competition_filter_by_gender(async_client: httpx.AsyncClient) -> None:
    response_m = await async_client.get("/api/v1/competitions?gender=m")
    response_f = await async_client.get("/api/v1/competitions?gender=f")
    assert response_m.status_code == 200
    assert response_f.status_code == 200
    assert len(response_m.json()) == 1
    assert len(response_f.json()) == 0


@pytest.mark.asyncio
async def test_competition_pagination_offset_beyond_total(
    async_client: httpx.AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/competitions?offset=10&limit=5")
    assert response.status_code == 200
    assert response.json() == []
    assert response.headers["x-total-count"] == "1"


@pytest.mark.asyncio
async def test_competition_404(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/api/v1/competitions/9999")
    assert response.status_code == 404
