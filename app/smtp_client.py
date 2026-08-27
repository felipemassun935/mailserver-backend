"""Cliente SMTP contra Postfix (submission, puerto 587 con STARTTLS)."""
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from app.config import settings
from app.tls import internal_mailserver_ssl_context


class SmtpAuthError(Exception):
    """Credenciales inválidas o fallo de autenticación SASL contra Postfix."""


class Attachment:
    __slots__ = ("filename", "content", "content_type")

    def __init__(self, filename: str, content: bytes, content_type: str) -> None:
        self.filename = filename
        self.content = content
        self.content_type = content_type


def send_message(
    email: str, password: str, to: str, subject: str, body: str, attachments: list[Attachment] | None = None
) -> bytes:
    """Envía el mensaje y devuelve los bytes RFC822 tal como se mandaron, para
    poder guardar una copia idéntica en la carpeta de Enviados.

    smtplib NO agrega Date/Message-ID por su cuenta (a diferencia de otros
    clientes SMTP) -- sin esto, la copia guardada en Enviados quedaba sin
    fecha."""
    msg = EmailMessage()
    msg["From"] = email
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(body)

    for attachment in attachments or []:
        content_type = attachment.content_type or "application/octet-stream"
        maintype, _, subtype = content_type.partition("/")
        msg.add_attachment(
            attachment.content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=attachment.filename,
        )

    context = internal_mailserver_ssl_context()

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        smtp.starttls(context=context)
        try:
            smtp.login(email, password)
        except smtplib.SMTPAuthenticationError as exc:
            raise SmtpAuthError(str(exc)) from exc
        smtp.send_message(msg)

    return msg.as_bytes()
