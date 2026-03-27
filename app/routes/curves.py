from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import numpy as np

from app.database.session import get_db
from app.models.user import User
from app.models.petrophysical_file import CurveData
from app.schemas.petrophysical import CurveResponse, MultiCurveResponse, CurveDataPoint
from app.auth.jwt import get_current_active_user
from app.routes.wells import get_well_or_404, check_well_access

router = APIRouter(prefix="/wells/{well_id}/curves", tags=["Données de Courbes"])


@router.get("/available")
def get_available_curves(
    well_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lister toutes les courbes disponibles pour un puits."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    curves = (
        db.query(CurveData.curve_name, CurveData.unit)
        .filter(CurveData.well_id == well_id)
        .distinct()
        .all()
    )
    return [{"curve_name": c.curve_name, "unit": c.unit} for c in curves]


@router.get("/{curve_name}", response_model=CurveResponse)
def get_curve_data(
    well_id: int,
    curve_name: str,
    depth_from: Optional[float] = Query(None, description="Profondeur minimale (m)"),
    depth_to: Optional[float] = Query(None, description="Profondeur maximale (m)"),
    downsample: Optional[int] = Query(None, ge=100, le=10000, description="Nombre max de points"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Récupérer les données d'une courbe (profondeur vs valeur).
    Idéal pour tracer un log individuel.
    """
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    query = db.query(CurveData).filter(
        CurveData.well_id == well_id,
        CurveData.curve_name == curve_name.upper(),
    )
    if depth_from is not None:
        query = query.filter(CurveData.depth_m >= depth_from)
    if depth_to is not None:
        query = query.filter(CurveData.depth_m <= depth_to)

    data_rows = query.order_by(CurveData.depth_m).all()
    if not data_rows:
        raise HTTPException(status_code=404, detail=f"Courbe '{curve_name}' introuvable pour ce puits")

    unit = data_rows[0].unit

    # Build data points
    points = [CurveDataPoint(depth_m=r.depth_m, value=r.value) for r in data_rows]

    # Downsample using numpy if needed
    if downsample and len(points) > downsample:
        indices = np.linspace(0, len(points) - 1, downsample, dtype=int)
        points = [points[i] for i in indices]

    # Calculate statistics (exclude None values)
    values = [p.value for p in points if p.value is not None]
    statistics = {}
    if values:
        statistics = {
            "min": round(float(np.min(values)), 4),
            "max": round(float(np.max(values)), 4),
            "mean": round(float(np.mean(values)), 4),
            "std": round(float(np.std(values)), 4),
            "count": len(values),
        }

    return CurveResponse(
        well_id=well_id,
        well_name=well.name,
        curve_name=curve_name.upper(),
        unit=unit,
        data=points,
        statistics=statistics,
    )


@router.get("/", response_model=MultiCurveResponse)
def get_multi_curve_data(
    well_id: int,
    curves: str = Query(..., description="Courbes séparées par virgule, ex: GR,RHOB,NPHI"),
    depth_from: Optional[float] = Query(None),
    depth_to: Optional[float] = Query(None),
    downsample: Optional[int] = Query(2000, ge=100, le=10000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Récupérer plusieurs courbes alignées sur les mêmes profondeurs.
    Optimisé pour l'affichage de logs composites.
    """
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    curve_list = [c.strip().upper() for c in curves.split(",") if c.strip()]
    if not curve_list:
        raise HTTPException(status_code=400, detail="Aucune courbe spécifiée")
    if len(curve_list) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 courbes par requête")

    query = db.query(CurveData).filter(
        CurveData.well_id == well_id,
        CurveData.curve_name.in_(curve_list),
    )
    if depth_from is not None:
        query = query.filter(CurveData.depth_m >= depth_from)
    if depth_to is not None:
        query = query.filter(CurveData.depth_m <= depth_to)

    rows = query.order_by(CurveData.depth_m, CurveData.curve_name).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Aucune donnée trouvée")

    # Pivot: group by depth
    depth_set = sorted(set(r.depth_m for r in rows))
    units = {}
    curve_map: dict = {c: {} for c in curve_list}

    for r in rows:
        curve_map[r.curve_name][r.depth_m] = r.value
        if r.curve_name not in units:
            units[r.curve_name] = r.unit or ""

    # Downsample depths
    if downsample and len(depth_set) > downsample:
        indices = np.linspace(0, len(depth_set) - 1, downsample, dtype=int)
        depth_set = [depth_set[i] for i in indices]

    curves_data = {c: [curve_map[c].get(d) for d in depth_set] for c in curve_list}

    return MultiCurveResponse(
        well_id=well_id,
        well_name=well.name,
        depths=depth_set,
        curves=curves_data,
        units=units,
    )
