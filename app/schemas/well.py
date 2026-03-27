from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class WellBase(BaseModel):
    name: str
    code: str
    field: str
    zone: Optional[str] = None
    basin: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_m: Optional[float] = None
    total_depth_m: Optional[float] = None
    spud_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    well_type: Optional[str] = None
    status: Optional[str] = None
    operator: Optional[str] = None
    description: Optional[str] = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v):
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("La latitude doit être entre -90 et 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v):
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("La longitude doit être entre -180 et 180")
        return v


class WellCreate(WellBase):
    pass


class WellUpdate(BaseModel):
    name: Optional[str] = None
    field: Optional[str] = None
    zone: Optional[str] = None
    basin: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_m: Optional[float] = None
    total_depth_m: Optional[float] = None
    spud_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    well_type: Optional[str] = None
    status: Optional[str] = None
    operator: Optional[str] = None
    description: Optional[str] = None


class WellResponse(WellBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WellMapResponse(BaseModel):
    """Lightweight response for map display."""
    id: int
    name: str
    code: str
    field: str
    zone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None
    well_type: Optional[str] = None

    model_config = {"from_attributes": True}


class WellFilter(BaseModel):
    """Query parameters for filtering wells."""
    field: Optional[str] = None
    zone: Optional[str] = None
    basin: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = None
    well_type: Optional[str] = None
    search: Optional[str] = None  # Searches name and code


class PaginatedWells(BaseModel):
    items: List[WellResponse]
    total: int
    page: int
    size: int
    pages: int
