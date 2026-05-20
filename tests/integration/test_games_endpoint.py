"""GET /api/v1/games/{id} returns full box-score payload — READ-07 + SC4."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_game_detail_has_quarters_and_box_scores(
    async_client: httpx.AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/games/1")
    assert response.status_code == 200
    body = response.json()

    # Per-quarter columns present.
    for key in (
        "q1_home",
        "q1_away",
        "q2_home",
        "q2_away",
        "q3_home",
        "q3_away",
        "q4_home",
        "q4_away",
        "total_home",
        "total_away",
    ):
        assert key in body, f"missing key {key}"

    # box_scores embedded: 24 rows (12 home + 12 away from seed_minimal).
    assert len(body["box_scores"]) == 24

    # Every box-score has the computed val/reb columns surfaced.
    for bs in body["box_scores"]:
        assert "val" in bs
        assert "reb" in bs
        assert bs["reb"] == bs["reb_of"] + bs["reb_def"]
