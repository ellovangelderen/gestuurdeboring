from uuid import uuid4

from sqlalchemy import Column, Float, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class EisenProfiel(Base):
    __tablename__ = "eisenprofielen"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    workspace_id = Column(String, nullable=True)   # None = globaal
    naam = Column(String, nullable=False)
    dekking_weg_m = Column(Float, nullable=False)
    dekking_water_m = Column(Float, nullable=False)
    Rmin_m = Column(Float, nullable=False)
    versie_datum = Column(String, default="NEN 3651:2020")

    project_eisenprofielen = relationship("ProjectEisenProfiel", back_populates="eisenprofiel")


class ProjectEisenProfiel(Base):
    __tablename__ = "project_eisenprofielen"

    project_id = Column(String, ForeignKey("projects.id"), primary_key=True)
    eisenprofiel_id = Column(String, ForeignKey("eisenprofielen.id"))
    override_eisen = Column(JSON)   # vergunningspecifieke afwijkingen

    project = relationship("Project", back_populates="project_eisenprofiel")
    eisenprofiel = relationship("EisenProfiel", back_populates="project_eisenprofielen")
