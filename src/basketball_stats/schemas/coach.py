"""Coach Pydantic schemas — CoachRead, CoachCreate."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class CoachRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "license_id": 88001,
                    "display_name": "Xavier Pasqual",
                    "normalized_name": "xavier-pasqual",
                }
            ]
        },
    )

    id: int
    license_id: int | None
    display_name: str
    normalized_name: str


class CoachCreate(BaseModel):
    """Draft schema — POST endpoint lands in P3 AUTH."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "license_id": 88001,
                    "display_name": "Xavier Pasqual",
                    "normalized_name": "xavier-pasqual",
                }
            ]
        }
    )

    license_id: int | None
    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    normalized_name: Annotated[str, Field(min_length=1, max_length=120)]
