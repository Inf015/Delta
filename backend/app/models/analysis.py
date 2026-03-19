import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, Enum as SAEnum, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class AnalysisStatus(str, enum.Enum):
    pending    = "pending"
    processing = "processing"
    done       = "done"
    failed     = "failed"


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("telemetry_sessions.id"), nullable=False, unique=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    status: Mapped[AnalysisStatus] = mapped_column(
        SAEnum(AnalysisStatus), nullable=False, default=AnalysisStatus.pending
    )

    # Resultado del pre-análisis (JSON calculado localmente, sin AI)
    pre_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Resultado de Claude (JSON estructurado)
    ai_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Tokens consumidos
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session = relationship("TelemetrySession", back_populates="analysis")
    user    = relationship("User")
    recommendations = relationship("Recommendation", back_populates="analysis")
