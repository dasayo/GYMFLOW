"""
Router de auth.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.schemas import LoginRequest, LoginResponse
from auth.service import CredencialesInvalidasError
from auth.service import login as login_service
from core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def post_login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        token, rol = login_service(payload.email, payload.password, db)
    except CredencialesInvalidasError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    return LoginResponse(access_token=token, rol=rol)
