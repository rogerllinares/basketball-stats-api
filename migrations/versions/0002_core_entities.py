"""Phase 2 core entities — 9 tables + 2 GENERATED COLUMNS + composite indexes.

Revision ID: 0002_core_entities
Revises: 0001_baseline
Create Date: 2026-05-20

Written by hand. `alembic revision --autogenerate` does NOT reliably emit
`Computed()` expressions or some Postgres-specific clauses (research §1 Pitfalls
+ D-19 P1). The migration deliberately mirrors D2-06 schema literal and the
PIR FIBA VAL expression from D2-07.

Tables created in FK order:
    clubs → seasons → competitions → teams → players → coaches
    → rosters → coaching_assignments → games → box_scores

GENERATED COLUMNS on box_scores (STORED, Postgres 16+):
    reb = reb_of + reb_def                      (D2-09 showcase)
    val = PIR FIBA literal                       (D2-07 + STAT-04 + SC3)

Indexes (Q1 resolution from PLAN — D2-20 composite on avg_stat DESC was
infeasible because avg_stat is window-function output, not stored):
    ix_games_competition_id        — accelerates leaderboards JOIN
    ix_box_scores_player_lookup    — accelerates PARTITION BY player_id
    ix_games_date_competition      — STAT-05 calendar queries
    ix_box_scores_val_desc         — showcase b-tree on GENERATED column
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_core_entities"
down_revision: str | Sequence[str] | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ENUM `competition_phase` mirrors D2-05.
competition_phase = postgresql.ENUM(
    "fase_previa",
    "segona_fase",
    "playoff",
    name="competition_phase",
    create_type=False,
)


def upgrade() -> None:
    """Create 9 entity tables + 2 GENERATED COLUMNS + 4 indexes."""
    competition_phase.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "clubs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("normalized_name", name="uq_clubs_normalized_name"),
    )

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=16), nullable=False),
        sa.UniqueConstraint("label", name="uq_seasons_label"),
    )

    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("gender", sa.String(length=16), nullable=False),
        sa.Column("territory", sa.String(length=64), nullable=False),
        sa.Column("group_no", sa.Integer(), nullable=False),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id"),
            nullable=False,
        ),
        sa.Column(
            "phase",
            competition_phase,
            nullable=False,
        ),
        sa.UniqueConstraint(
            "category",
            "gender",
            "territory",
            "group_no",
            "season_id",
            "phase",
            name="uq_competitions_natural_key",
        ),
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "club_id",
            sa.Integer(),
            sa.ForeignKey("clubs.id"),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.UniqueConstraint(
            "club_id",
            "normalized_name",
            name="uq_teams_club_normalized_name",
        ),
    )

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("license_id", sa.Integer(), nullable=False),
        sa.Column("dorsal_default", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.UniqueConstraint(
            "license_id",
            "dorsal_default",
            "normalized_name",
            name="uq_players_license_dorsal_normalized",
        ),
    )

    op.create_table(
        "coaches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("license_id", sa.Integer(), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.UniqueConstraint(
            "license_id",
            "normalized_name",
            name="uq_coaches_license_normalized",
        ),
    )

    op.create_table(
        "rosters",
        sa.Column(
            "player_id",
            sa.Integer(),
            sa.ForeignKey("players.id"),
            primary_key=True,
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            primary_key=True,
        ),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id"),
            primary_key=True,
        ),
        sa.Column("dorsal_at_season", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.Date(), nullable=False),
        sa.Column("left_at", sa.Date(), nullable=True),
    )

    op.create_table(
        "coaching_assignments",
        sa.Column(
            "coach_id",
            sa.Integer(),
            sa.ForeignKey("coaches.id"),
            primary_key=True,
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            primary_key=True,
        ),
        sa.Column(
            "season_id",
            sa.Integer(),
            sa.ForeignKey("seasons.id"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.Date(), nullable=False),
        sa.Column("ended_at", sa.Date(), nullable=True),
    )

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "competition_id",
            sa.Integer(),
            sa.ForeignKey("competitions.id"),
            nullable=False,
        ),
        sa.Column("matchday_no", sa.Integer(), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column(
            "home_team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            nullable=False,
        ),
        sa.Column(
            "away_team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            nullable=False,
        ),
        sa.Column("q1_home", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("q1_away", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("q2_home", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("q2_away", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("q3_home", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("q3_away", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("q4_home", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("q4_away", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_home", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_away", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "box_scores",
        sa.Column(
            "game_id",
            sa.Integer(),
            sa.ForeignKey("games.id"),
            primary_key=True,
        ),
        sa.Column(
            "player_id",
            sa.Integer(),
            sa.ForeignKey("players.id"),
            primary_key=True,
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id"),
            nullable=False,
        ),
        sa.Column("min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("plus_minus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fg2m", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fg2a", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fg3m", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fg3a", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ftm", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reb_of", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reb_def", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ast", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tap", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("per", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fouls_drawn", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocks_received", sa.Integer(), nullable=False, server_default="0"),
        # GENERATED COLUMNS — STORED. persisted=True is mandatory (Postgres 18
        # would default to VIRTUAL otherwise). val references (reb_of+reb_def)
        # directly because a generated column cannot reference another generated
        # column in the same row (Postgres 16 DDL rule — research §1 pitfall).
        sa.Column(
            "reb",
            sa.Integer(),
            sa.Computed("reb_of + reb_def", persisted=True),
        ),
        sa.Column(
            "val",
            sa.Integer(),
            sa.Computed(
                "pts + (reb_of + reb_def) + ast + rec + tap + fouls_drawn"
                " - (fg2a - fg2m) - (fg3a - fg3m) - (fta - ftm)"
                " - per - fc - blocks_received",
                persisted=True,
            ),
        ),
    )

    # Indexes — Q1 resolution. The original D2-20 composite
    # (comp, season, avg_stat DESC) was infeasible: avg_stat is a window-function
    # output (computed, not stored). Replaced by 4 real indexes targeting the
    # actual access paths.
    op.create_index(
        "ix_games_competition_id",
        "games",
        ["competition_id"],
    )
    op.create_index(
        "ix_box_scores_player_lookup",
        "box_scores",
        ["player_id"],
    )
    op.create_index(
        "ix_games_date_competition",
        "games",
        [sa.text("game_date DESC"), "competition_id"],
    )
    op.create_index(
        "ix_box_scores_val_desc",
        "box_scores",
        [sa.text("val DESC")],
    )


def downgrade() -> None:
    """Reverse FK order — drop indexes, then tables, then ENUM."""
    op.drop_index("ix_box_scores_val_desc", table_name="box_scores")
    op.drop_index("ix_games_date_competition", table_name="games")
    op.drop_index("ix_box_scores_player_lookup", table_name="box_scores")
    op.drop_index("ix_games_competition_id", table_name="games")

    op.drop_table("box_scores")
    op.drop_table("games")
    op.drop_table("coaching_assignments")
    op.drop_table("rosters")
    op.drop_table("coaches")
    op.drop_table("players")
    op.drop_table("teams")
    op.drop_table("competitions")
    op.drop_table("seasons")
    op.drop_table("clubs")

    competition_phase.drop(op.get_bind(), checkfirst=True)
