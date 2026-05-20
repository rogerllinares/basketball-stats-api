"""Competition Pydantic v2 schemas — OBS-08 examples in Catalan.

`CompetitionRead` mirrors the ORM model; `CompetitionCreate` is a draft for the P3
POST endpoint. Examples render as a dropdown in Swagger UI at /docs.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Phase = Literal["fase_previa", "segona_fase", "playoff"]


class CompetitionRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "category": "1a-territorial",
                    "gender": "m",
                    "territory": "bcn",
                    "group_no": 4,
                    "season_id": 1,
                    "phase": "fase_previa",
                    "display_name": "1a Territorial Masculí · BCN · Grup 4 · 2025-26",
                },
                {
                    "id": 2,
                    "category": "super-copa",
                    "gender": "m",
                    "territory": "cat",
                    "group_no": 1,
                    "season_id": 1,
                    "phase": "playoff",
                    "display_name": "Super Copa Masculina · Playoff · 2025-26",
                },
            ]
        },
    )

    id: int
    category: str
    gender: Literal["m", "f"]
    territory: str
    group_no: int
    season_id: int
    phase: Phase
    display_name: str


class CompetitionCreate(BaseModel):
    """Draft schema — POST endpoint lands in P3 AUTH."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "category": "1a-territorial",
                    "gender": "m",
                    "territory": "bcn",
                    "group_no": 4,
                    "season_id": 1,
                    "phase": "fase_previa",
                }
            ]
        }
    )

    category: Annotated[str, Field(min_length=1, max_length=64)]
    gender: Literal["m", "f"]
    territory: Annotated[str, Field(min_length=3, max_length=8)]
    group_no: Annotated[int, Field(ge=1, le=99)]
    season_id: int
    phase: Phase
