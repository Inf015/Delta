import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import String, Float, Boolean, Integer, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class Simulator(str, enum.Enum):
    ac  = "AC"
    r3e = "R3E"


class SessionType(str, enum.Enum):
    practice = "Practice"
    qualify  = "Qualify"
    race     = "Race"


class SourceType(str, enum.Enum):
    upload = "upload"
    drive  = "drive"


class TelemetrySession(Base):
    __tablename__ = "telemetry_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Datos de la vuelta
    simulator: Mapped[Simulator] = mapped_column(SAEnum(Simulator), nullable=False)
    track: Mapped[str] = mapped_column(String(200), nullable=False)
    car: Mapped[str] = mapped_column(String(200), nullable=False)
    session_type: Mapped[SessionType] = mapped_column(SAEnum(SessionType), nullable=False)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Tiempos
    lap_time: Mapped[float] = mapped_column(Float, nullable=False)
    s1: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    s2: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    s3: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Contexto
    tyre_compound: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    track_temp: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ambient_temp: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    track_length: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Archivo origen
    source: Mapped[SourceType] = mapped_column(SAEnum(SourceType), nullable=False, default=SourceType.upload)
    csv_path: Mapped[str] = mapped_column(String(500), nullable=False)
    session_date: Mapped[str] = mapped_column(String(30), nullable=False, default="")

    # Estado de procesamiento
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    drive_pdf_link: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Agrupación en sesión de carrera
    racing_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("racing_sessions.id"), nullable=True, index=True
    )

    user = relationship("User")
    analysis = relationship("Analysis", back_populates="session", uselist=False)
    pilot_notes = relationship("PilotNote", back_populates="session")
    racing_session = relationship("RacingSession", back_populates="laps")
