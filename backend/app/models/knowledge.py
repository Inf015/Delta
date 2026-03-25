import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class KnowledgeProfile(Base):
    """
    Perfil de aprendizaje por piloto + circuito + auto.
    Se actualiza automáticamente con cada sesión procesada (0 tokens).
    """
    __tablename__ = "knowledge_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Clave del perfil
    track: Mapped[str] = mapped_column(String(200), nullable=False)
    car: Mapped[str] = mapped_column(String(200), nullable=False)
    simulator: Mapped[str] = mapped_column(String(10), nullable=False)

    # Estadísticas acumuladas
    sessions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_lap: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_lap: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Sector débil detectado automáticamente ("S1" | "S2" | "S3" | None)
    weak_sector: Mapped[str | None] = mapped_column(String(5), nullable=True)

    # Tendencia: segundos ganados por cada 5 sesiones (positivo = mejorando)
    trend: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Análisis por curva acumulado (JSON: {zona: {avg_entry_speed, avg_apex_speed, ...}})
    corner_profiles: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Setup más usado (JSON con los campos que el sim exporta)
    common_setup: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Problemas recurrentes detectados por Claude
    # {area: {count, confirmed, last_seen_lap_time}}
    recurring_issues: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User")
    recommendations = relationship("Recommendation", back_populates="profile")


class Recommendation(Base):
    """
    Recomendación de Claude asociada a un análisis y un perfil.
    Se evalúa en la siguiente sesión del mismo circuito+auto.
    """
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id"), nullable=False, index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_profiles.id"), nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)   # ej. "130R", "Spoon"

    # Resultado evaluado en la siguiente sesión
    tested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delta_improvement: Mapped[float | None] = mapped_column(Float, nullable=True)  # segundos ganados

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    analysis = relationship("Analysis", back_populates="recommendations")
    profile  = relationship("KnowledgeProfile", back_populates="recommendations")


class PilotNote(Base):
    """Notas del piloto asociadas a una sesión (feedback activo)."""
    __tablename__ = "pilot_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("telemetry_sessions.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    tag: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "good_lap" | "new_setup" | ...

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("TelemetrySession", back_populates="pilot_notes")
    user    = relationship("User")
