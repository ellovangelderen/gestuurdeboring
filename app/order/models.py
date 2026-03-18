import math
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base

# Legacy Project model verplaatst naar app/project/models.py — hier niet meer nodig.


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    ordernummer = Column(String, nullable=False)
    locatie = Column(String)
    klantcode = Column(String)
    opdrachtgever = Column(String)
    status = Column(String, default="order_received")
    ontvangen_op = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deadline = Column(DateTime, nullable=True)
    geleverd_op = Column(DateTime, nullable=True)
    vergunning = Column(String, default="-")
    prio = Column(Boolean, default=False)
    notitie = Column(Text, nullable=True)
    tekenaar = Column(String, default="martien")
    akkoord_contact = Column(String, nullable=True)
    # URLs
    google_maps_url = Column(String, nullable=True)
    pdok_url = Column(String, nullable=True)
    waterkering_url = Column(String, nullable=True)
    oppervlaktewater_url = Column(String, nullable=True)
    peil_url = Column(String, nullable=True)

    # Relaties
    boringen = relationship("Boring", back_populates="order", cascade="all, delete-orphan")
    klic_uploads = relationship("KLICUpload", back_populates="order", cascade="all, delete-orphan")
    ev_partijen = relationship("EVPartij", back_populates="order", cascade="all, delete-orphan")
    ev_zones = relationship("EVZone", back_populates="order", cascade="all, delete-orphan")
    email_contacten = relationship("EmailContact", back_populates="order", cascade="all, delete-orphan")


class Boring(Base):
    __tablename__ = "boringen"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    volgnummer = Column(Integer, nullable=False)
    type = Column(String, nullable=False)          # B / N / Z / C
    naam = Column(String, nullable=True)           # "HDD29", "BZ2"
    # Leidingparameters (alleen B/N/Z, niet C)
    materiaal = Column(String, default="PE100")
    SDR = Column(Integer, default=11)
    De_mm = Column(Float, default=160.0)
    dn_mm = Column(Float, nullable=True)
    medium = Column(String, default="Drukloos")
    Db_mm = Column(Float, default=60.0)
    Dp_mm = Column(Float, default=110.0)
    Dg_mm = Column(Float, default=240.0)
    # Hoeken (alleen B/N)
    intreehoek_gr = Column(Float, default=18.0)
    uittreehoek_gr = Column(Float, default=22.0)
    # Boogzinker params (alleen Z)
    booghoek_gr = Column(Float, nullable=True)
    stand = Column(Integer, nullable=True)
    # Meta
    status = Column(String, default="concept")
    aangemaakt_door = Column(String, nullable=True)
    aangemaakt_op = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaties
    order = relationship("Order", back_populates="boringen")
    trace_punten = relationship("TracePunt", back_populates="boring",
                                order_by="TracePunt.volgorde", cascade="all, delete-orphan")
    maaiveld_override = relationship("MaaiveldOverride", back_populates="boring",
                                     uselist=False, cascade="all, delete-orphan")
    doorsneden = relationship("Doorsnede", back_populates="boring",
                              order_by="Doorsnede.volgorde", cascade="all, delete-orphan")
    berekening = relationship("Berekening", back_populates="boring",
                              uselist=False, cascade="all, delete-orphan")
    boring_klics = relationship("BoringKLIC", back_populates="boring", cascade="all, delete-orphan")
    werkplan_afbeeldingen = relationship("WerkplanAfbeelding", back_populates="boring",
                                         order_by="WerkplanAfbeelding.volgorde",
                                         cascade="all, delete-orphan")

    # Properties
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

    @property
    def Rv_m(self) -> float:
        """Minimale buigradius in meters: Rv = 1200 x De."""
        return 1200.0 * (self.De_mm or 160.0) / 1000.0


class KLICUpload(Base):
    __tablename__ = "klic_uploads"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    meldingnummer = Column(String)
    versie = Column(Integer, default=1)
    type = Column(String, nullable=True)
    bestandsnaam = Column(String)
    bestandspad = Column(String)
    upload_datum = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    verwerkt = Column(Boolean, default=False)
    aantal_leidingen = Column(Integer, nullable=True)
    aantal_beheerders = Column(Integer, nullable=True)
    verwerk_fout = Column(String, nullable=True)
    verwerkt_op = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="klic_uploads")
    boring_klics = relationship("BoringKLIC", back_populates="klic_upload", cascade="all, delete-orphan")
    leidingen = relationship("KLICLeiding", back_populates="klic_upload", cascade="all, delete-orphan")


class BoringKLIC(Base):
    __tablename__ = "boring_klics"

    boring_id = Column(String, ForeignKey("boringen.id"), primary_key=True)
    klic_upload_id = Column(String, ForeignKey("klic_uploads.id"), primary_key=True)

    boring = relationship("Boring", back_populates="boring_klics")
    klic_upload = relationship("KLICUpload", back_populates="boring_klics")


class KLICLeiding(Base):
    __tablename__ = "klic_leidingen"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    klic_upload_id = Column(String, ForeignKey("klic_uploads.id"), nullable=False)
    beheerder = Column(String)
    leidingtype = Column(String)
    thema = Column(String)
    dxf_laag = Column(String)
    geometrie_wkt = Column(Text)
    diepte_m = Column(Float)
    diepte_override_m = Column(Float)
    sleufloze_techniek = Column(Boolean, default=False)
    mogelijk_sleufloze = Column(Boolean, default=False)
    bron_pdf_url = Column(String)
    imkl_feature_id = Column(String)
    diepte_bron = Column(String)              # "imkl", "tekstveld_onzeker", None
    ev_verplicht = Column(Boolean, default=False)
    ev_contactgegevens = Column(String)
    label_tekst = Column(Text)
    toelichting_tekst = Column(Text)

    klic_upload = relationship("KLICUpload", back_populates="leidingen")


class TracePunt(Base):
    __tablename__ = "trace_punten"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    boring_id = Column(String, ForeignKey("boringen.id"), nullable=False)
    volgorde = Column(Integer, nullable=False)
    type = Column(String, nullable=False)   # "intree" / "tussenpunt" / "uittree"
    RD_x = Column(Float, nullable=False)
    RD_y = Column(Float, nullable=False)
    Rh_m = Column(Float)
    label = Column(String)
    variant = Column(Integer, default=0)    # 0=hoofd, 1/2/3=alternatieven

    boring = relationship("Boring", back_populates="trace_punten")


class MaaiveldOverride(Base):
    __tablename__ = "maaiveld_overrides"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    boring_id = Column(String, ForeignKey("boringen.id"), nullable=False)
    MVin_NAP_m = Column(Float)
    MVuit_NAP_m = Column(Float)
    bron = Column(String, default="handmatig")
    override_datum = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    MVin_bron = Column(String, default="handmatig")
    MVuit_bron = Column(String, default="handmatig")
    MVin_ahn5_m = Column(Float, nullable=True)
    MVuit_ahn5_m = Column(Float, nullable=True)

    boring = relationship("Boring", back_populates="maaiveld_override")


class Doorsnede(Base):
    __tablename__ = "doorsneden"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    boring_id = Column(String, ForeignKey("boringen.id"), nullable=False)
    volgorde = Column(Integer, nullable=False)
    afstand_m = Column(Float)
    NAP_m = Column(Float)
    grondtype = Column(String, default="Zand")
    GWS_m = Column(Float)
    phi_graden = Column(Float, default=35.0)
    E_modulus = Column(Float, default=75.0)
    override_vlag = Column(Boolean, default=True)
    override_datum = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    boring = relationship("Boring", back_populates="doorsneden")


class Berekening(Base):
    __tablename__ = "berekeningen"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    boring_id = Column(String, ForeignKey("boringen.id"), nullable=False)
    Ttot_N = Column(Float)
    bron = Column(String, default="sigma_override")
    override_datum = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    boring = relationship("Boring", back_populates="berekening")


class EVPartij(Base):
    __tablename__ = "ev_partijen"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    naam = Column(String)
    volgorde = Column(Integer)

    order = relationship("Order", back_populates="ev_partijen")


class EmailContact(Base):
    __tablename__ = "email_contacten"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    naam = Column(String)
    volgorde = Column(Integer)

    order = relationship("Order", back_populates="email_contacten")


class EVZone(Base):
    __tablename__ = "ev_zones"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    klic_upload_id = Column(String, ForeignKey("klic_uploads.id"), nullable=False)
    beheerder = Column(String)
    geometrie_wkt = Column(Text, nullable=False)
    netwerk_href = Column(String)

    order = relationship("Order", back_populates="ev_zones")


class WerkplanAfbeelding(Base):
    """Afbeeldingen voor werkplan-generatie (luchtfoto, topotijdreis, KLIC screenshot, etc.)."""
    __tablename__ = "werkplan_afbeeldingen"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    boring_id = Column(String, ForeignKey("boringen.id"), nullable=False)
    categorie = Column(String, nullable=False)  # "luchtfoto", "topotijdreis_1", "topotijdreis_2", "topotijdreis_3", "klic", "rws", "overig"
    bestandsnaam = Column(String)
    bestandspad = Column(String)
    bijschrift = Column(String, nullable=True)   # bijv. "Omstreeks 1870", "Screenshot van de KLIC"
    volgorde = Column(Integer, default=0)
    upload_datum = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    boring = relationship("Boring", back_populates="werkplan_afbeeldingen")
