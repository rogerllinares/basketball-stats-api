"""Pydantic models for the basquethero fixture JSON schema (D2.5-04).

This module defines the shape of the JSON file that the parser writes to
`data/seed/basquethero/<slug>-<season>.json` and that the loader at
`data/seed/load_basquethero.py` reads back. Both sides validate against
`BasqueteroFixture`, so the contract is the same source of truth.

Design notes:

- `ConfigDict(strict=True, extra="forbid")` on every model — catches drift
  early (a new field appearing in the page rendering breaks the parser,
  not the loader; a missing field breaks both, immediately).
- `FixtureBoxScore` does NOT carry `val` or `reb`: those are GENERATED
  columns computed by Postgres on INSERT/UPDATE (see
  `src/basketball_stats/models/box_score.py`). The fixture carries only
  the raw inputs the operator's acta provides.
- `FixturePlayer.license_id` is `int | None` — basquethero does not always
  expose a license id (amateur players sometimes appear without one). The
  loader skips players without a license_id and emits a structured stderr
  warning rather than inventing IDs (D2.5-05).
- `source_site` is a literal so a future ingest from a different aggregator
  cannot accidentally be loaded under this model — a different aggregator
  needs its own fixture model with its own literal tag.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, HttpUrl


def _coerce_iso_datetime(v: object) -> object:
    # strict=True forbids str→datetime in dict-mode; tests round-trip through
    # `model_validate(dict)` after mutating JSON, so accept ISO strings here.
    if isinstance(v, str):
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    return v


def _coerce_iso_date(v: object) -> object:
    if isinstance(v, str):
        return date.fromisoformat(v)
    return v


IsoDatetime = Annotated[datetime, BeforeValidator(_coerce_iso_datetime)]
IsoDate = Annotated[date, BeforeValidator(_coerce_iso_date)]


Position = Literal["PG", "SG", "SF", "PF", "C"]
"""5 standard basketball positions. None is also valid (amateur leagues skip)."""


class FixtureMetadata(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    fixture_version: str
    """Semver-style version of the fixture schema itself, not of the data."""

    scraped_at: IsoDatetime
    source_url: HttpUrl
    source_site: Literal["basquethero.cat"]


class FixtureCompetition(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    slug: str
    season: str
    """Display string like '2025-26' (not a normalised year)."""

    name: str
    gender: Literal["M", "F"]
    category: str
    """Free-form category label as basquethero displays it (e.g. '2a', 'cc')."""


class FixtureTeam(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    basquethero_team_id: int
    club_slug: str
    display_name: str


class FixturePlayer(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    license_id: int | None
    """basquethero may omit the federation license id for some players."""

    first_name: str
    last_name: str
    position: Position | None = None


class FixtureBoxScore(BaseModel):
    """One row per (game, player). Raw acta fields only — `val` and `reb` are
    GENERATED COLUMNS in the database and MUST NOT appear in the fixture."""

    model_config = ConfigDict(strict=True, extra="forbid")

    player_license_id: int | None
    """Same nullable rule as FixturePlayer.license_id."""

    minutes: int
    points: int
    fg2m: int
    fg2a: int
    fg3m: int
    fg3a: int
    ftm: int
    fta: int
    reb_of: int
    reb_def: int
    ast: int
    rec: int
    """Recoveries (steals)."""

    tap: int
    """Blocks (tapones)."""

    fouls_drawn: int
    per: int
    """Personal fouls."""

    fc: int
    """Fouls committed (alias for some FCBQ acta variants)."""

    blocks_received: int


class FixtureGame(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    basquethero_game_id: int
    date: IsoDate
    home_team_id: int
    """basquethero_team_id of the home team."""

    away_team_id: int
    q1_home: int
    q1_away: int
    q2_home: int
    q2_away: int
    q3_home: int
    q3_away: int
    q4_home: int
    q4_away: int
    box_scores: list[FixtureBoxScore]


class BasqueteroFixture(BaseModel):
    """Root container for one (competition, season) snapshot."""

    model_config = ConfigDict(strict=True, extra="forbid")

    metadata: FixtureMetadata
    competition: FixtureCompetition
    teams: list[FixtureTeam]
    players: list[FixturePlayer]
    games: list[FixtureGame]
