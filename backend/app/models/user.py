import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class Plan(str, enum.Enum):
    free = "free"
    pro  = "pro"
    team = "team"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    # Plan y límites
    plan: Mapped[Plan] = mapped_column(SAEnum(Plan), nullable=False, default=Plan.free)
    analyses_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analyses_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Stripe
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Estado
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    @property
    def analyses_limit(self) -> int:
        limits = {Plan.free: 3, Plan.pro: 30, Plan.team: 100}
        return limits[self.plan]

    @property
    def analyses_remaining(self) -> int:
        return max(0, self.analyses_limit - self.analyses_used)

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.plan}]>"
