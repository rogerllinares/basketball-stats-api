"""Team Pydantic schemas — TeamRead, TeamDetailRead, TeamCreate.

`TeamDetailRead` is used by router Task 5.2 (`GET /teams/{id}`) and embeds the current
roster, recent games, and upcoming games — defined here at Wave 3 to preserve the wave
boundary (routers only consume schemas; they do not define new ones).
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from basketball_stats.schemas.game import GameSummaryRead
from basketball_stats.schemas.player import PlayerRead


class TeamRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "club_id": 1,
                    "display_name": "CB Granollers",
                    "normalized_name": "cb-granollers",
                },
                {
                    "id": 2,
                    "club_id": 2,
                    "display_name": "CB Artés",
                    "normalized_name": "cb-artes",
                },
            ]
        },
    )

    id: int
    club_id: int
    display_name: str
    normalized_name: str


class TeamDetailRead(BaseModel):
    """READ-04 payload — full team page with roster + games."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "club_id": 1,
                    "display_name": "CB Granollers",
                    "normalized_name": "cb-granollers",
                    "roster_current": [
                        {
                            "id": 10,
                            "license_id": 99001,
                            "dorsal_default": 5,
                            "display_name": "Marc Soler",
                            "normalized_name": "marc-soler",
                        }
                    ],
                    "recent_games": [
                        {
                            "id": 7,
                            "game_date": "2025-10-12",
                            "matchday_no": 3,
                            "total_home": 78,
                            "total_away": 65,
                        }
                    ],
                    "upcoming_games": [
                        {
                            "id": 9,
                            "game_date": "2025-10-26",
                            "matchday_no": 5,
                            "total_home": 0,
                            "total_away": 0,
                        }
                    ],
                }
            ]
        },
    )

    id: int
    club_id: int
    display_name: str
    normalized_name: str
    roster_current: list[PlayerRead]
    recent_games: list[GameSummaryRead]
    upcoming_games: list[GameSummaryRead]


class TeamCreate(BaseModel):
    """Draft schema — POST endpoint lands in P3 AUTH."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "club_id": 1,
                    "display_name": "CB Granollers",
                    "normalized_name": "cb-granollers",
                }
            ]
        }
    )

    club_id: int
    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    normalized_name: Annotated[str, Field(min_length=1, max_length=120)]
