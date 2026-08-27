from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_session
from app.imap_client import ImapConnectionError, get_message, list_messages
from app.schemas import MessageDetail, MessageSummary, SendMessageRequest
from app.sessions import Session
from app.smtp_client import SmtpAuthError, send_message

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("", response_model=list[MessageSummary])
def get_messages(folder: str = "INBOX", limit: int = 50, session: Session = Depends(get_current_session)):
    try:
        return list_messages(session.email, session.password, folder=folder, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ImapConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No se pudo conectar con el mailserver"
        )


@router.get("/{uid}", response_model=MessageDetail)
def get_message_detail(uid: str, folder: str = "INBOX", session: Session = Depends(get_current_session)):
    try:
        return get_message(session.email, session.password, uid, folder=folder)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ImapConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No se pudo conectar con el mailserver"
        )


@router.post("/send", status_code=status.HTTP_204_NO_CONTENT)
def send(payload: SendMessageRequest, session: Session = Depends(get_current_session)) -> None:
    try:
        send_message(session.email, session.password, payload.to, payload.subject, payload.body)
    except SmtpAuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Fallo de autenticación SMTP")
