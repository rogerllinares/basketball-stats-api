"""Standings Pydantic schemas — output of the RANK() window function (STAT-01).

`StandingsRow` is the public-facing row; the repository computes `position` via the
window function so the row stays a plain dataclass-like value.
"""

from pydantic import BaseModel, ConfigDict


class StandingsRow(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "team_id": 1,
                    "display_name": "CB Granollers",
                    "played": 14,
                    "wins": 11,
                    "losses": 3,
                    "points_for": 1092,
                    "points_against": 938,
                    "point_diff": 154,
                    "position": 1,
                },
                {
                    "team_id": 2,
                    "display_name": "CB Artés",
                    "played": 14,
                    "wins": 9,
                    "losses": 5,
                    "points_for": 1011,
                    "points_against": 988,
                    "point_diff": 23,
                    "position": 2,
                },
            ]
        },
    )

    team_id: int
    display_name: str
    played: int
    wins: int
    losses: int
    points_for: int
    points_against: int
    point_diff: int
    position: int
