import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class TrackInfo(Base):
    __tablename__ = "track_info"

    track_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    track_type: Mapped[str] = mapped_column(String(20), default="unknown")  # real | fictional | unknown
    length_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    turns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    characteristics: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    sectors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    key_corners: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    lap_record: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    map_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="unknown")  # static | claude
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
