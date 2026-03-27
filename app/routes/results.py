from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.models.user import User
from app.models.analysis_result import AnalysisResult, ResultType
from app.schemas.analysis import (
    AnalysisResultCreate, AnalysisResultUpdate,
    AnalysisResultResponse, PaginatedResults,
)
from app.auth.jwt import get_current_active_user
from app.routes.wells import get_well_or_404, check_well_access
from app.services.audit import log_action, Actions

router = APIRouter(prefix="/wells/{well_id}/results", tags=["Résultats d'Analyse"])


@router.post("/", response_model=AnalysisResultResponse, status_code=201)
def create_result(
    well_id: int,
    body: AnalysisResultCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Ajouter un résultat d'analyse à un puits."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    result = AnalysisResult(**body.model_dump(), well_id=well_id, created_by=current_user.id)
    db.add(result)
    db.flush()
    log_action(db, Actions.CREATE_RESULT, user_id=current_user.id,
               resource_type="result", resource_id=result.id,
               ip_address=request.client.host)
    db.commit()
    db.refresh(result)
    return result


@router.get("/", response_model=PaginatedResults)
def list_results(
    well_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    result_type: Optional[ResultType] = Query(None),
    zone_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lister les résultats d'analyse d'un puits."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    query = db.query(AnalysisResult).filter(AnalysisResult.well_id == well_id)
    if result_type:
        query = query.filter(AnalysisResult.result_type == result_type)
    if zone_name:
        query = query.filter(AnalysisResult.zone_name.ilike(f"%{zone_name}%"))

    total = query.count()
    items = query.order_by(AnalysisResult.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return PaginatedResults(
        items=items, total=total, page=page, size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/{result_id}", response_model=AnalysisResultResponse)
def get_result(
    well_id: int,
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Détail d'un résultat d'analyse."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)
    result = db.query(AnalysisResult).filter(
        AnalysisResult.id == result_id,
        AnalysisResult.well_id == well_id,
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Résultat introuvable")
    return result


@router.put("/{result_id}", response_model=AnalysisResultResponse)
def update_result(
    well_id: int,
    result_id: int,
    body: AnalysisResultUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mettre à jour un résultat d'analyse."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)
    result = db.query(AnalysisResult).filter(
        AnalysisResult.id == result_id,
        AnalysisResult.well_id == well_id,
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Résultat introuvable")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(result, field, value)

    log_action(db, Actions.UPDATE_RESULT, user_id=current_user.id,
               resource_type="result", resource_id=result_id,
               ip_address=request.client.host)
    db.commit()
    db.refresh(result)
    return result


@router.delete("/{result_id}", status_code=204)
def delete_result(
    well_id: int,
    result_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Supprimer un résultat d'analyse."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)
    result = db.query(AnalysisResult).filter(
        AnalysisResult.id == result_id,
        AnalysisResult.well_id == well_id,
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Résultat introuvable")
    log_action(db, Actions.DELETE_RESULT, user_id=current_user.id,
               resource_type="result", resource_id=result_id,
               ip_address=request.client.host)
    db.delete(result)
    db.commit()
