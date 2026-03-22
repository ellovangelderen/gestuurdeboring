"""Admin modellen — klanten, instellingen."""
from uuid import uuid4

from sqlalchemy import Column, String, Integer
from app.core.database import Base


class Instelling(Base):
    """Key-value systeeminstelling."""
    __tablename__ = "instellingen_kv"

    sleutel = Column(String, primary_key=True)
    waarde = Column(String, nullable=False, default="")


class Klant(Base):
    """Opdrachtgever / klant met logo en contactgegevens."""
    __tablename__ = "klanten"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    nr = Column(Integer, nullable=True)          # Martien's nummer (1-50)
    code = Column(String, nullable=False, unique=True)  # bijv. "3D", "VB"
    naam = Column(String, nullable=False)         # bijv. "3D-Drilling"
    contact = Column(String, nullable=True)       # bijv. "M.Visser"
    logo_bestand = Column(String, nullable=True)  # bijv. "logo_3D.png"
