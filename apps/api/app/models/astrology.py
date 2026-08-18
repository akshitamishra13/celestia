from datetime import UTC, date, datetime, time
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def now() -> datetime:
    return datetime.now(UTC)


class BirthProfile(Base):
    __tablename__ = "birth_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    gender: Mapped[str | None] = mapped_column(String(40), nullable=True)
    date_of_birth: Mapped[date] = mapped_column(Date)
    time_of_birth: Mapped[time] = mapped_column(Time)
    birth_place: Mapped[str] = mapped_column(String(240))
    canonical_place: Mapped[str] = mapped_column(String(240))
    latitude: Mapped[str] = mapped_column(String(32))
    longitude: Mapped[str] = mapped_column(String(32))
    timezone: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class BirthChart(Base):
    __tablename__ = "birth_charts"
    __table_args__ = (UniqueConstraint("birth_profile_id", "calculation_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    birth_profile_id: Mapped[UUID] = mapped_column(ForeignKey("birth_profiles.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="mock")
    provider_version: Mapped[str] = mapped_column(String(20), default="v1")
    calculation_version: Mapped[str] = mapped_column(String(20), default="v1")
    ayanamsha: Mapped[str] = mapped_column(String(40), default="lahiri")
    house_system: Mapped[str] = mapped_column(String(40), default="whole_sign")
    calculation_key: Mapped[str] = mapped_column(String(64), index=True)
    chart_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CompatibilityMatch(Base):
    __tablename__ = "compatibility_matches"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    person_a_chart_id: Mapped[UUID] = mapped_column(ForeignKey("birth_charts.id"))
    person_b_chart_id: Mapped[UUID] = mapped_column(ForeignKey("birth_charts.id"))
    compatibility_version: Mapped[str] = mapped_column(String(20), default="v1")
    calculation_key: Mapped[str] = mapped_column(String(64), index=True)
    result_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    report_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[UUID]
    title: Mapped[str] = mapped_column(String(180))
    report_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
