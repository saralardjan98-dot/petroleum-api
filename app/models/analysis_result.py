from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.session import Base
import enum


class ResultType(str, enum.Enum):
    POROSITY = "porosity"
    WATER_SATURATION = "water_saturation"
    PERMEABILITY = "permeability"
    LITHOLOGY = "lithology"
    NET_PAY = "net_pay"
    FORMATION_EVALUATION = "formation_evaluation"
    OTHER = "other"


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    result_type = Column(SAEnum(ResultType), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Depth interval
    depth_from_m = Column(Float, nullable=True)
    depth_to_m = Column(Float, nullable=True)
    zone_name = Column(String(255), nullable=True)       # e.g., "Reservoir A", "Zone 3"
    formation_name = Column(String(255), nullable=True)

    # Key result values (main KPIs)
    porosity_avg = Column(Float, nullable=True)          # Average porosity (fraction)
    water_saturation_avg = Column(Float, nullable=True)  # Average Sw (fraction)
    permeability_avg_md = Column(Float, nullable=True)   # Average permeability (md)
    net_pay_m = Column(Float, nullable=True)             # Net pay thickness (m)
    gross_pay_m = Column(Float, nullable=True)           # Gross pay thickness (m)
    ntg_ratio = Column(Float, nullable=True)             # Net-to-gross ratio

    # Cutoffs applied
    porosity_cutoff = Column(Float, nullable=True)
    sw_cutoff = Column(Float, nullable=True)
    vshale_cutoff = Column(Float, nullable=True)

    # Method used
    method = Column(String(255), nullable=True)          # e.g., "Archie", "Simandoux"
    parameters_used = Column(JSON, nullable=True)        # Method parameters

    # Detailed data as JSON array [{"depth": 1000.5, "porosity": 0.15, ...}]
    result_data = Column(JSON, nullable=True)

    # Foreign keys
    well_id = Column(Integer, ForeignKey("wells.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    well = relationship("Well", back_populates="analysis_results")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, well={self.well_id}, type={self.result_type})>"
