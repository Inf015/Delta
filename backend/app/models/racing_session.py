import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base
from app.models.session import Simulator, SessionType


class RacingSession(Base):
    __tablename__ = "racing_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    track: Mapped[str | None] = mapped_column(String(200), nullable=True)
    car: Mapped[str | None] = mapped_column(String(200), nullable=True)
    simulator: Mapped[Simulator | None] = mapped_column(SAEnum(Simulator), nullable=True)
    session_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    session_type: Mapped[SessionType | None] = mapped_column(SAEnum(SessionType), nullable=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    report_cache: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    setup_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    laps = relationship("TelemetrySession", back_populates="racing_session", cascade="all, delete-orphan")
    user = relationship("User")
