"""Session store en memoria del proceso. No hay base de datos de usuarios:
la "sesión" es simplemente el par (email, password) que ya se validó contra
IMAP, guardado bajo un token random. Se pierde todo al reiniciar el proceso,
lo cual es aceptable para este caso de uso casero."""
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.config import settings


@dataclass
class Session:
    email: str
    password: str
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, email: str, password: str) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_TTL_HOURS)
        with self._lock:
            self._sessions[token] = Session(email=email, password=password, expires_at=expires_at)
        return token

    def get(self, token: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None
            if session.expires_at < datetime.now(timezone.utc):
                del self._sessions[token]
                return None
            return session

    def delete(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)


session_store = SessionStore()
