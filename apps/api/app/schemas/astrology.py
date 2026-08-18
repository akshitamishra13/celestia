from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BirthDetails(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    date_of_birth: date
    time_of_birth: time
    place: str = Field(min_length=2, max_length=240)
    gender: str | None = Field(default=None, max_length=40)

    @field_validator("name", "place")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("date_of_birth")
    @classmethod
    def date_must_not_be_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value


class KundliRequest(BaseModel):
    birth_profile_id: UUID | None = None
    birth_details: BirthDetails | None = None


class CompatibilityRequest(BaseModel):
    person_a: BirthDetails
    person_b: BirthDetails


class DataResponse(BaseModel):
    success: bool = True
    data: dict | list


class ReportSummary(BaseModel):
    id: UUID
    report_type: str
    source_id: UUID
    title: str
    created_at: datetime
