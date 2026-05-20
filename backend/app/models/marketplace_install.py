import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.types import GUID


class MarketplaceInstall(Base):
    """One row per (installer, agent). When auth lands (0.2), installer_id
    will be linked to the User table; for now it is just a UUID we accept
    from the client so anonymous installs are still tracked uniquely."""

    __tablename__ = "marketplace_installs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False
    )
    installer_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("agent_id", "installer_id", name="uq_install_agent_user"),
        Index("idx_install_agent", "agent_id"),
    )
