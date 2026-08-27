from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_session
from app.imap_client import ImapConnectionError, resolve_special_folders
from app.sessions import Session

router = APIRouter(prefix="/api/folders", tags=["folders"])


@router.get("")
def get_folders(session: Session = Depends(get_current_session)) -> dict[str, str | None]:
    """Nombres reales de INBOX y de la carpeta de enviados en este servidor
    (no siempre se llaman literalmente 'INBOX'/'Sent')."""
    try:
        return resolve_special_folders(session.email, session.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ImapConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No se pudo conectar con el mailserver"
        )
