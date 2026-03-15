import math
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
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

    trace_punten = relationship("TracePunt", back_populates="project",
                                order_by="TracePunt.volgorde", cascade="all, delete-orphan")
    maaiveld_override = relationship("MaaiveldOverride", back_populates="project",
                                     uselist=False, cascade="all, delete-orphan")
    klic_uploads = relationship("KLICUpload", back_populates="project",
                                cascade="all, delete-orphan")
    klic_leidingen = relationship("KLICLeiding", back_populates="project",
                                  cascade="all, delete-orphan")
    doorsneden = relationship("Doorsnede", back_populates="project",
                              order_by="Doorsnede.volgorde", cascade="all, delete-orphan")
    berekening = relationship("Berekening", back_populates="project",
                              uselist=False, cascade="all, delete-orphan")
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


class TracePunt(Base):
    __tablename__ = "trace_punten"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    volgorde = Column(Integer, nullable=False)
    type = Column(String, nullable=False)   # "intree" / "tussenpunt" / "uittree"
    RD_x = Column(Float, nullable=False)
    RD_y = Column(Float, nullable=False)
    Rh_m = Column(Float)                   # horizontale boogstraal (alleen tussenpunten)
    label = Column(String)                  # bijv. "A", "Tv1", "Th1", "B"

    project = relationship("Project", back_populates="trace_punten")


class MaaiveldOverride(Base):
    __tablename__ = "maaiveld_overrides"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    MVin_NAP_m = Column(Float)
    MVuit_NAP_m = Column(Float)
    bron = Column(String, default="handmatig")
    override_datum = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    # AHN5 uitbreiding (backlog item 2)
    MVin_bron    = Column(String, default="handmatig")   # "handmatig" | "ahn5" | "niet_beschikbaar"
    MVuit_bron   = Column(String, default="handmatig")
    MVin_ahn5_m  = Column(Float, nullable=True)           # AHN5-referentiewaarde, nooit gewist
    MVuit_ahn5_m = Column(Float, nullable=True)

    project = relationship("Project", back_populates="maaiveld_override")


class KLICUpload(Base):
    __tablename__ = "klic_uploads"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    bestandsnaam = Column(String)
    bestandspad = Column(String)
    upload_datum = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    verwerkt = Column(Boolean, default=False)

    # Velden ingevuld na verwerking
    aantal_leidingen  = Column(Integer)
    aantal_beheerders = Column(Integer)
    verwerk_fout      = Column(String)
    verwerkt_op       = Column(DateTime)

    project  = relationship("Project", back_populates="klic_uploads")
    leidingen = relationship("KLICLeiding", back_populates="klic_upload",
                             cascade="all, delete-orphan")


class Doorsnede(Base):
    __tablename__ = "doorsneden"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    volgorde = Column(Integer, nullable=False)
    afstand_m = Column(Float)
    NAP_m = Column(Float)
    grondtype = Column(String, default="Zand")   # Zand / Klei / Veen
    GWS_m = Column(Float)
    phi_graden = Column(Float, default=35.0)
    E_modulus = Column(Float, default=75.0)
    override_vlag = Column(Boolean, default=True)
    override_datum = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="doorsneden")


class Berekening(Base):
    __tablename__ = "berekeningen"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    Ttot_N = Column(Float)
    bron = Column(String, default="sigma_override")
    override_datum = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="berekening")


class KLICLeiding(Base):
    __tablename__ = "klic_leidingen"

    id                 = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id         = Column(String, ForeignKey("projects.id"), nullable=False)
    klic_upload_id     = Column(String, ForeignKey("klic_uploads.id"), nullable=False)
    beheerder          = Column(String)
    leidingtype        = Column(String)
    thema              = Column(String)
    dxf_laag           = Column(String)
    geometrie_wkt      = Column(Text)
    diepte_m           = Column(Float)
    diepte_override_m  = Column(Float)
    sleufloze_techniek = Column(Boolean, default=False)
    bron_pdf_url       = Column(String)
    imkl_feature_id    = Column(String)

    project    = relationship("Project", back_populates="klic_leidingen")
    klic_upload = relationship("KLICUpload", back_populates="leidingen")
