from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List

from app.database.session import get_db
from app.models.user import User, UserRole
from app.models.well import Well
from app.schemas.well import WellCreate, WellUpdate, WellResponse, WellMapResponse, PaginatedWells
from app.auth.jwt import get_current_active_user
from app.services.audit import log_action, Actions

router = APIRouter(prefix="/wells", tags=["Puits"])


def get_well_or_404(well_id: int, db: Session) -> Well:
    well = db.query(Well).filter(Well.id == well_id, Well.is_active == True).first()
    if not well:
        raise HTTPException(status_code=404, detail="Puits introuvable")
    return well


def check_well_access(well: Well, current_user: User):
    """Non-admins can only access their own wells."""
    if current_user.role != UserRole.ADMIN and well.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé à ce puits")


@router.post("/", response_model=WellResponse, status_code=201)
def create_well(
    body: WellCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Créer un nouveau puits."""
    if db.query(Well).filter(Well.code == body.code).first():
        raise HTTPException(status_code=400, detail=f"Le code puits '{body.code}' existe déjà")

    well = Well(**body.model_dump(), owner_id=current_user.id)
    db.add(well)
    db.flush()
    log_action(db, Actions.CREATE_WELL, user_id=current_user.id,
               resource_type="well", resource_id=well.id,
               description=f"Puits créé: {well.name} ({well.code})",
               ip_address=request.client.host)
    db.commit()
    db.refresh(well)
    return well


@router.get("/", response_model=PaginatedWells)
def list_wells(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    field: Optional[str] = Query(None, description="Filtrer par champ pétrolier"),
    zone: Optional[str] = Query(None),
    basin: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    well_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Recherche sur nom ou code"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lister les puits avec filtres et pagination."""
    query = db.query(Well).filter(Well.is_active == True)

    # Non-admin users only see their own wells
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Well.owner_id == current_user.id)

    # Apply filters
    if field:
        query = query.filter(Well.field.ilike(f"%{field}%"))
    if zone:
        query = query.filter(Well.zone.ilike(f"%{zone}%"))
    if basin:
        query = query.filter(Well.basin.ilike(f"%{basin}%"))
    if country:
        query = query.filter(Well.country.ilike(f"%{country}%"))
    if status:
        query = query.filter(Well.status == status)
    if well_type:
        query = query.filter(Well.well_type == well_type)
    if search:
        query = query.filter(
            or_(Well.name.ilike(f"%{search}%"), Well.code.ilike(f"%{search}%"))
        )

    total = query.count()
    items = query.order_by(Well.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return PaginatedWells(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/map", response_model=List[WellMapResponse])
def get_wells_for_map(
    field: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Récupérer les puits avec coordonnées pour affichage cartographique."""
    query = db.query(Well).filter(
        Well.is_active == True,
        Well.latitude.isnot(None),
        Well.longitude.isnot(None),
    )
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Well.owner_id == current_user.id)
    if field:
        query = query.filter(Well.field.ilike(f"%{field}%"))
    return query.all()


@router.get("/{well_id}", response_model=WellResponse)
def get_well(
    well_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Détail d'un puits."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)
    return well


@router.put("/{well_id}", response_model=WellResponse)
def update_well(
    well_id: int,
    body: WellUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mettre à jour un puits."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    for field_name, value in body.model_dump(exclude_unset=True).items():
        setattr(well, field_name, value)

    log_action(db, Actions.UPDATE_WELL, user_id=current_user.id,
               resource_type="well", resource_id=well_id,
               ip_address=request.client.host)
    db.commit()
    db.refresh(well)
    return well


@router.delete("/{well_id}", status_code=204)
def delete_well(
    well_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Supprimer un puits (soft delete)."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)
    well.is_active = False
    log_action(db, Actions.DELETE_WELL, user_id=current_user.id,
               resource_type="well", resource_id=well_id,
               description=f"Puits supprimé: {well.name}",
               ip_address=request.client.host)
    db.commit()
