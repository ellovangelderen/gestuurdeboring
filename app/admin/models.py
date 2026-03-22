"""Admin modellen — klanten, instellingen, gebruikers."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.core.database import Base


class User(Base):
    """Gebruiker met bcrypt wachtwoord hash en rol."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    username = Column(String, nullable=False, unique=True)
    wachtwoord_hash = Column(String, nullable=False)
    rol = Column(String, nullable=False, default="tekenaar")  # admin / tekenaar / viewer
    actief = Column(Boolean, nullable=False, default=True)
    workspace_id = Column(String, nullable=False, default="gbt-workspace-001")
    aangemaakt_op = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    laatst_ingelogd = Column(DateTime, nullable=True)


class Instelling(Base):
    """Key-value systeeminstelling."""
    __tablename__ = "instellingen_kv"

    sleutel = Column(String, primary_key=True)
    waarde = Column(String, nullable=False, default="")


class KaartLink(Base):
    """Externe kaartlink (RWS, ProRail, waterschap, gemeente)."""
    __tablename__ = "kaart_links"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    naam = Column(String, nullable=False)
    url = Column(String, nullable=False)
    omschrijving = Column(String, nullable=True)
    categorie = Column(String, default="kaart")  # kaart, zonering, gemeente
    volgorde = Column(Integer, default=0)


class Klant(Base):
    """Opdrachtgever / klant met logo en contactgegevens."""
    __tablename__ = "klanten"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    nr = Column(Integer, nullable=True)          # Martien's nummer (1-50)
    code = Column(String, nullable=False, unique=True)  # bijv. "3D", "VB"
    naam = Column(String, nullable=False)         # bijv. "3D-Drilling"
    contact = Column(String, nullable=True)       # bijv. "M.Visser"
    logo_bestand = Column(String, nullable=True)  # bijv. "logo_3D.png"
