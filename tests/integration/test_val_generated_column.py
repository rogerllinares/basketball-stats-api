"""VAL + REB GENERATED columns assertion — STAT-04 + SC3.

Inline INSERTs (no seed fixture). Asserts Postgres computes
``reb = reb_of + reb_def`` and ``val = PIR FIBA`` literal at storage time.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_val_generated_column_matches_pir_fiba(db_session: AsyncSession) -> None:
    await db_session.execute(
        text("""
        INSERT INTO clubs (id, display_name, normalized_name)
          VALUES (901, 'CB Test', 'cb-test');
        INSERT INTO seasons (id, start_year, label)
          VALUES (901, 2025, '2025-26-test');
        INSERT INTO competitions
          (id, category, gender, territory, group_no, season_id, phase)
          VALUES (901, '1a-territorial', 'm', 'bcn', 99, 901, 'fase_previa');
        INSERT INTO teams (id, club_id, display_name, normalized_name)
          VALUES (901, 901, 'CB Test A', 'cb-test-a');
        INSERT INTO players
          (id, license_id, dorsal_default, display_name, normalized_name)
          VALUES (901, 99901, 5, 'Rafael Pintó', 'rafael-pinto');
        INSERT INTO games
          (id, competition_id, matchday_no, game_date, home_team_id, away_team_id,
           q1_home, q1_away, q2_home, q2_away, q3_home, q3_away, q4_home, q4_away,
           total_home, total_away)
          VALUES (901, 901, 1, '2025-10-15', 901, 901,
                  20, 18, 22, 24, 18, 20, 20, 22, 80, 84);
        """)
    )

    await db_session.execute(
        text("""
        INSERT INTO box_scores
          (game_id, player_id, team_id, pts, reb_of, reb_def, ast, rec, tap,
           fouls_drawn, fg2a, fg2m, fg3a, fg3m, fta, ftm, per, fc, blocks_received)
        VALUES (901, 901, 901, 10, 3, 2, 4, 2, 1, 2, 5, 4, 3, 1, 2, 1, 1, 2, 0);
        """)
    )
    await db_session.commit()

    row = (
        await db_session.execute(
            text("SELECT reb, val FROM box_scores WHERE game_id = 901 AND player_id = 901")
        )
    ).one()

    # reb = reb_of + reb_def = 3 + 2 = 5
    assert row.reb == 5
    # val = pts + reb + ast + rec + tap + fouls_drawn
    #       - (fg2a-fg2m) - (fg3a-fg3m) - (fta-ftm) - per - fc - blocks_received
    #     = 10 + 5 + 4 + 2 + 1 + 2 - 1 - 2 - 1 - 1 - 2 - 0 = 17
    assert row.val == 17
