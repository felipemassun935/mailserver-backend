import re

from pydantic import BaseModel, field_validator

# EmailStr de pydantic rechaza TLDs "reservados" como .local, que es
# justamente el dominio de este mailserver casero. Usamos una validación
# de formato liviana en su lugar.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email_format(value: str) -> str:
    if not _EMAIL_RE.match(value):
        raise ValueError("Dirección de email inválida")
    return value


class LoginRequest(BaseModel):
    email: str
    password: str

    _validate = field_validator("email")(validate_email_format)


class LoginResponse(BaseModel):
    token: str
    email: str


class MessageSummary(BaseModel):
    uid: str
    sender: str
    subject: str
    date: str
    seen: bool


class AttachmentMeta(BaseModel):
    index: int
    filename: str
    content_type: str
    size: int


class MessageDetail(BaseModel):
    uid: str
    sender: str
    to: str
    subject: str
    date: str
    body_text: str
    body_html: str | None = None
    attachments: list[AttachmentMeta] = []
