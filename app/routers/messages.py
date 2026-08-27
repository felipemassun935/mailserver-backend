from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.deps import get_current_session
from app.imap_client import ImapConnectionError, get_attachment, get_message, list_messages
from app.schemas import MessageDetail, MessageSummary, validate_email_format
from app.sessions import Session
from app.smtp_client import Attachment, SmtpAuthError, send_message

router = APIRouter(prefix="/api/messages", tags=["messages"])

# Límite generoso para un mailserver casero; evita que un adjunto gigante
# tumbe el proceso por consumo de memoria (todo se maneja en memoria, sin streaming a disco).
MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024


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


@router.get("/{uid}/attachments/{index}")
def download_attachment(
    uid: str, index: int, folder: str = "INBOX", session: Session = Depends(get_current_session)
):
    try:
        content, filename, content_type = get_attachment(session.email, session.password, uid, index, folder=folder)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ImapConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No se pudo conectar con el mailserver"
        )

    # El filename viene del email (potencialmente hostil): lo saneamos para
    # el header Content-Disposition, no vaya a inyectar CRLF u otros headers.
    safe_filename = filename.replace("\r", "").replace("\n", "").replace('"', "")
    return Response(
        content=content,
        media_type=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.post("/send", status_code=status.HTTP_204_NO_CONTENT)
async def send(
    to: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    session: Session = Depends(get_current_session),
) -> None:
    try:
        validate_email_format(to)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dirección de email inválida")

    attachments: list[Attachment] = []
    for upload in files:
        content = await upload.read()
        if len(content) > MAX_ATTACHMENT_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El adjunto '{upload.filename}' supera el tamaño máximo permitido (25MB)",
            )
        attachments.append(
            Attachment(
                filename=upload.filename or "adjunto",
                content=content,
                content_type=upload.content_type or "application/octet-stream",
            )
        )

    try:
        send_message(session.email, session.password, to, subject, body, attachments)
    except SmtpAuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Fallo de autenticación SMTP")
