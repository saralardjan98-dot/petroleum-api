from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.petrophysical_file import FileType, FileStatus


class PetrophysicalFileResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: FileType
    file_size_bytes: Optional[int] = None
    status: FileStatus
    error_message: Optional[str] = None

    # LAS metadata
    well_name_in_file: Optional[str] = None
    company: Optional[str] = None
    field_in_file: Optional[str] = None
    start_depth: Optional[float] = None
    stop_depth: Optional[float] = None
    step: Optional[float] = None
    depth_unit: Optional[str] = None
    null_value: Optional[float] = None
    available_curves: Optional[List[str]] = None
    curve_units: Optional[Dict[str, str]] = None

    well_id: int
    uploaded_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CurveDataPoint(BaseModel):
    depth_m: float
    value: Optional[float] = None


class CurveResponse(BaseModel):
    """Response for a single curve visualization."""
    well_id: int
    well_name: str
    curve_name: str
    unit: Optional[str] = None
    depth_unit: str = "m"
    data: List[CurveDataPoint]
    statistics: Optional[Dict[str, float]] = None  # min, max, mean, std


class MultiCurveResponse(BaseModel):
    """Response for multiple curves (log display)."""
    well_id: int
    well_name: str
    depths: List[float]
    curves: Dict[str, List[Optional[float]]]  # {curve_name: [values]}
    units: Dict[str, str]


class CurveFilter(BaseModel):
    depth_from: Optional[float] = None
    depth_to: Optional[float] = None
    curves: Optional[List[str]] = None  # Filter specific curves
    downsample: Optional[int] = None    # Max number of points (for performance)
