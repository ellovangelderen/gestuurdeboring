from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from app.core.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True)
    naam = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
