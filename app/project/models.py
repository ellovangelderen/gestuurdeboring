"""Legacy project models — alleen Project tabel bewaard voor backward compatibility.

De tabellen trace_punten, doorsneden, berekeningen, maaiveld_overrides, klic_uploads
en klic_leidingen zijn verplaatst naar app/order/models.py met boring_id FK (was project_id).
"""
import math
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    naam = Column(String, nullable=False)
    opdrachtgever = Column(String)
    ordernummer = Column(String)
    # Leidingparameters
    materiaal = Column(String, default="PE100")
    SDR = Column(Integer, default=11)
    De_mm = Column(Float, default=160.0)
    dn_mm = Column(Float)           # handmatig override; anders berekend
    medium = Column(String, default="Drukloos")
    Db_mm = Column(Float, default=60.0)    # boorstang diameter
    Dp_mm = Column(Float, default=110.0)   # pilotboorkop diameter
    Dg_mm = Column(Float, default=240.0)   # ruimer diameter
    # Hoeken
    intreehoek_gr = Column(Float, default=18.0)
    uittreehoek_gr = Column(Float, default=22.0)
    # Meta
    status = Column(String, default="concept")
    aangemaakt_door = Column(String)
    aangemaakt_op = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project_eisenprofiel = relationship("ProjectEisenProfiel", back_populates="project",
                                        uselist=False, cascade="all, delete-orphan")

    @property
    def dn_berekend(self) -> float:
        return round(self.De_mm / self.SDR, 1)

    @property
    def dn_effectief(self) -> float:
        return self.dn_mm if self.dn_mm else self.dn_berekend

    @property
    def Di_mm(self) -> float:
        return round(self.De_mm - 2 * self.dn_effectief, 2)

    @property
    def intreehoek_pct(self) -> float:
        return round(math.tan(math.radians(self.intreehoek_gr)) * 100, 1)

    @property
    def uittreehoek_pct(self) -> float:
        return round(math.tan(math.radians(self.uittreehoek_gr)) * 100, 1)
