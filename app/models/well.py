from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.session import Base


class Well(Base):
    __tablename__ = "wells"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    field = Column(String(255), nullable=False, index=True)   # Champ pétrolier
    zone = Column(String(255), nullable=True, index=True)     # Zone géologique
    basin = Column(String(255), nullable=True)                # Bassin sédimentaire
    country = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    elevation_m = Column(Float, nullable=True)                # Élévation KB (Kelly Bushing)
    total_depth_m = Column(Float, nullable=True)              # Profondeur totale
    spud_date = Column(DateTime(timezone=True), nullable=True)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    well_type = Column(String(50), nullable=True)             # exploration, appraisal, production
    status = Column(String(50), nullable=True)                # active, abandoned, suspended
    operator = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="wells")
    petrophysical_files = relationship("PetrophysicalFile", back_populates="well", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="well", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Well(id={self.id}, code={self.code}, field={self.field})>"
