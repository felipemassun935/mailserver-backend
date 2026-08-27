"""Cliente IMAP contra Dovecot. Cada llamada abre y cierra su propia
conexión: el volumen de uso de un mailserver casero con 2 cuentas no
justifica mantener un pool de conexiones persistente, y así nos evitamos
manejar reconexión/expiración de sesiones IMAP en el backend."""
import imaplib
import ssl
from contextlib import contextmanager
from datetime import datetime
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime

from app.config import settings
from app.tls import internal_mailserver_ssl_context


class ImapAuthError(Exception):
    """Credenciales inválidas o fallo de login contra Dovecot."""


class ImapConnectionError(Exception):
    """No se pudo establecer conexión con el mailserver (host caído, DNS, etc)."""


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


@contextmanager
def imap_connection(email: str, password: str):
    context = internal_mailserver_ssl_context()
    try:
        conn = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT, ssl_context=context)
    except (OSError, ssl.SSLError) as exc:
        raise ImapConnectionError(str(exc)) from exc

    try:
        try:
            conn.login(email, password)
        except imaplib.IMAP4.error as exc:
            raise ImapAuthError(str(exc)) from exc
        yield conn
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def verify_login(email: str, password: str) -> None:
    """Levanta ImapAuthError si las credenciales no son válidas."""
    with imap_connection(email, password):
        pass


def _parse_envelope_date(raw_date: str | None) -> str:
    if not raw_date:
        return ""
    try:
        return parsedate_to_datetime(raw_date).isoformat()
    except Exception:
        return raw_date


def list_messages(email: str, password: str, folder: str = "INBOX", limit: int = 50) -> list[dict]:
    with imap_connection(email, password) as conn:
        status, _ = conn.select(folder, readonly=True)
        if status != "OK":
            raise ValueError(f"No se pudo abrir la carpeta '{folder}'")

        status, data = conn.uid("search", None, "ALL")
        if status != "OK":
            raise ValueError("Fallo al listar mensajes")

        uids = data[0].split()
        uids.reverse()  # más recientes primero
        uids = uids[:limit]

        messages: list[dict] = []
        for uid in uids:
            status, msg_data = conn.uid(
                "fetch", uid, "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
            )
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue

            flags_raw = msg_data[0][0].decode(errors="replace") if isinstance(msg_data[0], tuple) else ""
            seen = "\\Seen" in flags_raw

            header_bytes = msg_data[0][1] if isinstance(msg_data[0], tuple) else b""
            header_msg: Message = message_from_bytes(header_bytes)

            messages.append(
                {
                    "uid": uid.decode(),
                    "sender": _decode(header_msg.get("From")),
                    "subject": _decode(header_msg.get("Subject")) or "(sin asunto)",
                    "date": _parse_envelope_date(header_msg.get("Date")),
                    "seen": seen,
                }
            )
        return messages


def _extract_body(msg: Message) -> tuple[str, str | None]:
    body_text = ""
    body_html: str | None = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in disposition:
                continue
            charset = part.get_content_charset() or "utf-8"
            if content_type == "text/plain" and not body_text:
                body_text = part.get_payload(decode=True).decode(charset, errors="replace")
            elif content_type == "text/html" and body_html is None:
                body_html = part.get_payload(decode=True).decode(charset, errors="replace")
    else:
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        text = payload.decode(charset, errors="replace") if payload else ""
        if msg.get_content_type() == "text/html":
            body_html = text
        else:
            body_text = text

    return body_text, body_html


def get_message(email: str, password: str, uid: str, folder: str = "INBOX") -> dict:
    with imap_connection(email, password) as conn:
        status, _ = conn.select(folder, readonly=False)  # no readonly: abrir marca como leído
        if status != "OK":
            raise ValueError(f"No se pudo abrir la carpeta '{folder}'")

        status, msg_data = conn.uid("fetch", uid, "(RFC822)")
        if status != "OK" or not msg_data or msg_data[0] is None:
            raise ValueError("Mensaje no encontrado")

        raw = msg_data[0][1]
        msg: Message = message_from_bytes(raw)
        body_text, body_html = _extract_body(msg)

        return {
            "uid": uid,
            "sender": _decode(msg.get("From")),
            "to": _decode(msg.get("To")),
            "subject": _decode(msg.get("Subject")) or "(sin asunto)",
            "date": _parse_envelope_date(msg.get("Date")),
            "body_text": body_text,
            "body_html": body_html,
        }
