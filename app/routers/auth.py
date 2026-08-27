from fastapi import APIRouter, Header, HTTPException, status

from app.imap_client import ImapAuthError, ImapConnectionError, verify_login
from app.schemas import LoginRequest, LoginResponse
from app.sessions import session_store

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    try:
        verify_login(payload.email, payload.password)
    except ImapAuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos")
    except ImapConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No se pudo conectar con el mailserver"
        )

    token = session_store.create(payload.email, payload.password)
    return LoginResponse(token=token, email=payload.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(authorization: str | None = Header(default=None)) -> None:
    if authorization and authorization.startswith("Bearer "):
        session_store.delete(authorization.removeprefix("Bearer ").strip())
