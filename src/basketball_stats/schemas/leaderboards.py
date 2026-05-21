"""Leaderboard Pydantic schemas — output of the RANK() window function (STAT-02).

`LeaderboardStat` mirrors the `ALLOWED_STATS` set declared on the repository side.
Adding a stat requires updating both the Literal here and the SQL builder in
`repositories/leaderboards.py`.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

LeaderboardStat = Literal["val", "pts", "reb", "ast", "rec", "tap", "plus_minus"]


class LeaderboardRow(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "player_id": 10,
                    "display_name": "Marc Soler",
                    "games_played": 12,
                    "avg_stat": 17.5,
                    "position": 1,
                },
                {
                    "player_id": 11,
                    "display_name": "Jordi Vilaró",
                    "games_played": 11,
                    "avg_stat": 15.2,
                    "position": 2,
                },
            ]
        },
    )

    player_id: int
    display_name: str
    games_played: int
    avg_stat: float
    position: int
