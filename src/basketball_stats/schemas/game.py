"""Game + BoxScore Pydantic schemas.

`GameSummaryRead` is a compact form embedded inside `TeamDetailRead.recent_games`
and `upcoming_games`. `GameRead` is the full payload returned by `GET /games/{id}`,
including the full box-score list.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict


class BoxScoreRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "game_id": 1,
                    "player_id": 10,
                    "team_id": 1,
                    "min": 28,
                    "pts": 10,
                    "plus_minus": 4,
                    "fg2m": 4,
                    "fg2a": 5,
                    "fg3m": 1,
                    "fg3a": 3,
                    "ftm": 1,
                    "fta": 2,
                    "reb_of": 3,
                    "reb_def": 2,
                    "reb": 5,
                    "ast": 4,
                    "rec": 2,
                    "tap": 1,
                    "per": 1,
                    "fc": 2,
                    "fouls_drawn": 2,
                    "blocks_received": 0,
                    "val": 17,
                }
            ]
        },
    )

    game_id: int
    player_id: int
    team_id: int
    min: int
    pts: int
    plus_minus: int
    fg2m: int
    fg2a: int
    fg3m: int
    fg3a: int
    ftm: int
    fta: int
    reb_of: int
    reb_def: int
    reb: int
    ast: int
    rec: int
    tap: int
    per: int
    fc: int
    fouls_drawn: int
    blocks_received: int
    val: int


class GameSummaryRead(BaseModel):
    """Compact game view embedded inside TeamDetailRead."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "game_date": "2025-10-12",
                    "matchday_no": 3,
                    "total_home": 78,
                    "total_away": 65,
                }
            ]
        },
    )

    id: int
    game_date: date
    matchday_no: int
    total_home: int
    total_away: int


class GameRead(BaseModel):
    """READ-07 full payload — per-quarter scores + full box-score."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "competition_id": 1,
                    "matchday_no": 3,
                    "game_date": "2025-10-12",
                    "home_team_id": 1,
                    "away_team_id": 2,
                    "q1_home": 18,
                    "q1_away": 14,
                    "q2_home": 22,
                    "q2_away": 19,
                    "q3_home": 16,
                    "q3_away": 15,
                    "q4_home": 22,
                    "q4_away": 17,
                    "total_home": 78,
                    "total_away": 65,
                    "box_scores": [],
                }
            ]
        },
    )

    id: int
    competition_id: int
    matchday_no: int
    game_date: date
    home_team_id: int
    away_team_id: int
    q1_home: int
    q1_away: int
    q2_home: int
    q2_away: int
    q3_home: int
    q3_away: int
    q4_home: int
    q4_away: int
    total_home: int
    total_away: int
    box_scores: list[BoxScoreRead]
