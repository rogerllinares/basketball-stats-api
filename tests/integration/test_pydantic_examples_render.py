"""OpenAPI examples render at /openapi.json — OBS-08 + SC7.

Asserts every key Read schema has a non-empty `examples` list in the OpenAPI
component schema, so /docs renders a meaningful dropdown for each.
"""

import httpx
import pytest


@pytest.mark.asyncio
async def test_openapi_components_have_examples(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200

    schemas = response.json()["components"]["schemas"]

    # Only schemas that are referenced by P2 endpoints appear in the OpenAPI
    # components map. TeamRead / CoachRead / *Create are P3 draft schemas.
    must_have_examples = (
        "CompetitionRead",
        "TeamDetailRead",
        "PlayerRead",
        "PlayerStatsRead",
        "BoxScoreRead",
        "GameRead",
        "GameSummaryRead",
        "StandingsRow",
        "LeaderboardRow",
    )

    for name in must_have_examples:
        assert name in schemas, f"schema {name} missing"
        examples = schemas[name].get("examples")
        assert examples is not None, f"schema {name} has no examples"
        assert len(examples) >= 1, f"schema {name} examples list empty"
