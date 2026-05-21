"""Player Pydantic schemas — PlayerRead, PlayerStatsRead, PlayerCreate.

`PlayerStatsRead` is the READ-06 payload — aggregated season stats (totals + per-game
averages) computed by the repository. It is a derived view, not a 1:1 ORM mirror.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class PlayerRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 10,
                    "license_id": 99001,
                    "dorsal_default": 5,
                    "display_name": "Marc Soler",
                    "normalized_name": "marc-soler",
                },
                {
                    "id": 11,
                    "license_id": 99002,
                    "dorsal_default": 8,
                    "display_name": "Jordi Vilaró",
                    "normalized_name": "jordi-vilaro",
                },
            ]
        },
    )

    id: int
    license_id: int
    dorsal_default: int
    display_name: str
    normalized_name: str


class PlayerStatsRead(BaseModel):
    """READ-06 payload — aggregated season stats for one player."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "player_id": 10,
                    "season_id": 1,
                    "games_played": 14,
                    "pts_total": 168,
                    "pts_avg": 12.0,
                    "reb_total": 84,
                    "reb_avg": 6.0,
                    "ast_avg": 3.5,
                    "val_avg": 14.2,
                }
            ]
        }
    )

    player_id: int
    season_id: int
    games_played: int
    pts_total: int
    pts_avg: float
    reb_total: int
    reb_avg: float
    ast_avg: float
    val_avg: float


class PlayerCreate(BaseModel):
    """Draft schema — POST endpoint lands in P3 AUTH."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "license_id": 99001,
                    "dorsal_default": 5,
                    "display_name": "Marc Soler",
                    "normalized_name": "marc-soler",
                }
            ]
        }
    )

    license_id: int
    dorsal_default: Annotated[int, Field(ge=0, le=999)]
    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    normalized_name: Annotated[str, Field(min_length=1, max_length=120)]
