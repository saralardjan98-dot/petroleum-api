import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.session import get_db
from app.models.user import User
from app.models.well import Well
from app.models.petrophysical_file import PetrophysicalFile, FileType, FileStatus
from app.schemas.petrophysical import PetrophysicalFileResponse
from app.auth.jwt import get_current_active_user
from app.services.file_processor import save_upload_file, validate_file_extension, validate_file_size, process_file
from app.services.audit import log_action, Actions
from app.routes.wells import get_well_or_404, check_well_access
from app.core.config import settings

router = APIRouter(prefix="/wells/{well_id}/files", tags=["Fichiers Pétrophysiques"])


def get_file_type(filename: str) -> FileType:
    ext = filename.rsplit(".", 1)[-1].lower()
    return FileType.LAS if ext == "las" else FileType.CSV


@router.post("/", response_model=PetrophysicalFileResponse, status_code=201)
async def upload_file(
    well_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Uploader un fichier LAS ou CSV associé à un puits.
    Le traitement (extraction des courbes) se fait en arrière-plan.
    """
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    # Validate filename/extension
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Extension non supportée. Formats acceptés: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read and validate size
    content = await file.read()
    if not validate_file_size(len(content)):
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux. Maximum: {settings.MAX_FILE_SIZE_MB} MB",
        )

    # Save to disk
    unique_filename, filepath = save_upload_file(content, file.filename, well_id)

    # Create DB record
    file_record = PetrophysicalFile(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=filepath,
        file_type=get_file_type(file.filename),
        file_size_bytes=len(content),
        well_id=well_id,
        uploaded_by=current_user.id,
        status=FileStatus.UPLOADED,
    )
    db.add(file_record)
    db.flush()

    log_action(db, Actions.UPLOAD_FILE, user_id=current_user.id,
               resource_type="file", resource_id=file_record.id,
               description=f"Fichier uploadé: {file.filename}",
               ip_address=request.client.host)
    db.commit()
    db.refresh(file_record)

    # Process in background (parse curves)
    background_tasks.add_task(process_file, db, file_record)

    return file_record


@router.get("/", response_model=List[PetrophysicalFileResponse])
def list_files(
    well_id: int,
    status: Optional[FileStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lister les fichiers d'un puits."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    query = db.query(PetrophysicalFile).filter(PetrophysicalFile.well_id == well_id)
    if status:
        query = query.filter(PetrophysicalFile.status == status)
    return query.order_by(PetrophysicalFile.created_at.desc()).all()


@router.get("/{file_id}", response_model=PetrophysicalFileResponse)
def get_file(
    well_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Détail d'un fichier pétrophysique."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    file_record = db.query(PetrophysicalFile).filter(
        PetrophysicalFile.id == file_id,
        PetrophysicalFile.well_id == well_id,
    ).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return file_record


@router.post("/{file_id}/reprocess", response_model=PetrophysicalFileResponse)
def reprocess_file(
    well_id: int,
    file_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Relancer le traitement d'un fichier (utile en cas d'erreur)."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    file_record = db.query(PetrophysicalFile).filter(
        PetrophysicalFile.id == file_id,
        PetrophysicalFile.well_id == well_id,
    ).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    file_record.status = FileStatus.UPLOADED
    file_record.error_message = None
    log_action(db, Actions.REPROCESS_FILE, user_id=current_user.id,
               resource_type="file", resource_id=file_id,
               ip_address=request.client.host)
    db.commit()

    background_tasks.add_task(process_file, db, file_record)
    db.refresh(file_record)
    return file_record


@router.delete("/{file_id}", status_code=204)
def delete_file(
    well_id: int,
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Supprimer un fichier pétrophysique et ses données associées."""
    well = get_well_or_404(well_id, db)
    check_well_access(well, current_user)

    file_record = db.query(PetrophysicalFile).filter(
        PetrophysicalFile.id == file_id,
        PetrophysicalFile.well_id == well_id,
    ).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    # Delete physical file
    if os.path.exists(file_record.file_path):
        os.remove(file_record.file_path)

    log_action(db, Actions.DELETE_FILE, user_id=current_user.id,
               resource_type="file", resource_id=file_id,
               description=f"Fichier supprimé: {file_record.original_filename}",
               ip_address=request.client.host)
    db.delete(file_record)
    db.commit()
