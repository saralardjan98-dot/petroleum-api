from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, Boolean, JSON, Enum as SAEnum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.session import Base
import enum


class FileType(str, enum.Enum):
    LAS = "las"
    CSV = "csv"


class FileStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"


class PetrophysicalFile(Base):
    __tablename__ = "petrophysical_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(SAEnum(FileType), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    status = Column(SAEnum(FileStatus), default=FileStatus.UPLOADED)
    error_message = Column(Text, nullable=True)

    # LAS metadata extracted automatically
    well_name_in_file = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    field_in_file = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    country_in_file = Column(String(100), nullable=True)
    date_in_file = Column(String(100), nullable=True)
    service_company = Column(String(255), nullable=True)
    start_depth = Column(Float, nullable=True)
    stop_depth = Column(Float, nullable=True)
    step = Column(Float, nullable=True)
    depth_unit = Column(String(20), nullable=True)
    null_value = Column(Float, nullable=True)

    # Available curves as JSON list
    available_curves = Column(JSON, nullable=True)  # ["GR", "RHOB", "NPHI", ...]
    curve_units = Column(JSON, nullable=True)        # {"GR": "GAPI", "RHOB": "G/C3", ...}
    extra_metadata = Column(JSON, nullable=True)     # Other LAS header info

    # Foreign keys
    well_id = Column(Integer, ForeignKey("wells.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    well = relationship("Well", back_populates="petrophysical_files")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    curves = relationship("CurveData", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PetrophysicalFile(id={self.id}, filename={self.filename}, status={self.status})>"


class CurveData(Base):
    """
    Stores petrophysical curve data points.
    Each row = one depth measurement for one curve.
    For large datasets, consider TimescaleDB or partitioning.
    """
    __tablename__ = "curve_data"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("petrophysical_files.id", ondelete="CASCADE"), nullable=False)
    well_id = Column(Integer, ForeignKey("wells.id", ondelete="CASCADE"), nullable=False)  # Denormalized for fast queries
    curve_name = Column(String(50), nullable=False, index=True)  # GR, RHOB, NPHI, etc.
    depth_m = Column(Float, nullable=False)
    value = Column(Float, nullable=True)  # NULL for missing data (-9999 converted to NULL)
    unit = Column(String(20), nullable=True)

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_curve_well_depth", "well_id", "curve_name", "depth_m"),
        Index("idx_curve_file_name", "file_id", "curve_name"),
    )

    # Relationships
    file = relationship("PetrophysicalFile", back_populates="curves")

    def __repr__(self):
        return f"<CurveData(well={self.well_id}, curve={self.curve_name}, depth={self.depth_m})>"
