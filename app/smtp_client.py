"""Cliente SMTP contra Postfix (submission, puerto 587 con STARTTLS)."""
import smtplib
from email.message import EmailMessage

from app.config import settings
from app.tls import internal_mailserver_ssl_context


class SmtpAuthError(Exception):
    """Credenciales inválidas o fallo de autenticación SASL contra Postfix."""


def send_message(email: str, password: str, to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = email
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    context = internal_mailserver_ssl_context()

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        smtp.starttls(context=context)
        try:
            smtp.login(email, password)
        except smtplib.SMTPAuthenticationError as exc:
            raise SmtpAuthError(str(exc)) from exc
        smtp.send_message(msg)
