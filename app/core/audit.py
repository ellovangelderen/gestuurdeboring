"""Audit trail — wie heeft wat wanneer gewijzigd.

Simpel model: AuditLog tabel met actie, user, model, record_id, details.
Audit logging mag NOOIT de hoofdoperatie laten falen.
"""
import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text
from app.core.database import Base, SessionLocal

logger = logging.getLogger(__name__)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tijdstip = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    user = Column(String, nullable=False)
    actie = Column(String, nullable=False)    # "aangemaakt", "gewijzigd", "verwijderd"
    model = Column(String, nullable=False)     # "Order", "Boring", "Klant"
    record_id = Column(String, nullable=True)  # ID van het gewijzigde record
    details = Column(Text, nullable=True)      # Extra info (bijv. welke velden)


def log_audit(db, user: str, actie: str, model: str, record_id: str = None, details: str = None):
    """Voeg een audit log entry toe. Faalt NOOIT — gebruikt aparte session."""
    try:
        audit_db = SessionLocal()
        try:
            entry = AuditLog(user=user, actie=actie, model=model, record_id=record_id, details=details)
            audit_db.add(entry)
            audit_db.commit()
        finally:
            audit_db.close()
    except Exception as exc:
        logger.warning("Audit log fout (niet kritisch): %s", exc)
