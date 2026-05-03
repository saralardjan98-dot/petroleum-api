import traceback
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.auth.jwt import get_current_active_user # تأكدي من وجود هذا السطر
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, LoginRequest, ChangePasswordRequest
from app.auth.jwt import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_active_user
)
from app.services.audit import log_action, Actions
from app.core.config import settings

router = APIRouter(tags=["Authentification"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):

    try:
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(status_code=400, detail="Email déjà utilisé")

        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(status_code=400, detail="Username déjà utilisé")

        user = User(
            email=user_data.email,
            username=user_data.username,
            display_name=user_data.full_name,
            hashed_password=hash_password(user_data.password),
            role=user_data.role,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Connexion et obtention des tokens JWT."""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        log_action(db, Actions.LOGIN, description=f"Échec login: {credentials.email}",
                   ip_address=request.client.host, status="failed")
        db.commit()
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    log_action(db, Actions.LOGIN, user_id=user.id, resource_type="user",
               ip_address=request.client.host)
    db.commit()

    return {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    "user": {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role
    }
}


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_tok: str, db: Session = Depends(get_db)):
    """Renouveler l'access token via le refresh token."""
    token_data = decode_token(refresh_tok)
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user :
        raise HTTPException(status_code=401, detail="Token invalide")

    token_payload = {"sub": str(user.id), "role": user.role.value}
    return Token(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    # مرري كل الحقول المطلوبة في UserResponse لتجنب الـ ValidationError
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        role=current_user.role,
        is_active=getattr(current_user, 'is_active', True),  # أضيفي هذا
        created_at=getattr(current_user, 'created_at', None), # أضيفي هذا
        display_name=getattr(current_user, 'display_name', current_user.username) # أضيفي هذا[cite: 1]
    )

@router.put("/me/password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Changer son mot de passe."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    current_user.hashed_password = hash_password(body.new_password)
    log_action(db, Actions.CHANGE_PASSWORD, user_id=current_user.id,
               ip_address=request.client.host)
    db.commit()
