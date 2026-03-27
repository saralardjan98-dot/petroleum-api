from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.analysis_result import ResultType


class AnalysisResultBase(BaseModel):
    name: str
    result_type: ResultType
    description: Optional[str] = None
    depth_from_m: Optional[float] = None
    depth_to_m: Optional[float] = None
    zone_name: Optional[str] = None
    formation_name: Optional[str] = None
    porosity_avg: Optional[float] = None
    water_saturation_avg: Optional[float] = None
    permeability_avg_md: Optional[float] = None
    net_pay_m: Optional[float] = None
    gross_pay_m: Optional[float] = None
    ntg_ratio: Optional[float] = None
    porosity_cutoff: Optional[float] = None
    sw_cutoff: Optional[float] = None
    vshale_cutoff: Optional[float] = None
    method: Optional[str] = None
    parameters_used: Optional[Dict[str, Any]] = None
    result_data: Optional[List[Dict[str, Any]]] = None


class AnalysisResultCreate(AnalysisResultBase):
    pass


class AnalysisResultUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    porosity_avg: Optional[float] = None
    water_saturation_avg: Optional[float] = None
    result_data: Optional[List[Dict[str, Any]]] = None


class AnalysisResultResponse(AnalysisResultBase):
    id: int
    well_id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedResults(BaseModel):
    items: List[AnalysisResultResponse]
    total: int
    page: int
    size: int
    pages: int
