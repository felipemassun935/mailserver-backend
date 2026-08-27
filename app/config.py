"""Configuración vía variables de entorno. Sin base de datos: todo lo que
necesita este servicio es dónde está el mailserver y cuánto dura una sesión."""
import os


class Settings:
    # Nombre de servicio Docker del mailserver (red interna "mailserver_mailserver-net")
    IMAP_HOST: str = os.getenv("IMAP_HOST", "mailserver")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))

    SMTP_HOST: str = os.getenv("SMTP_HOST", "mailserver")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))  # submission, STARTTLS

    MAIL_DOMAIN: str = os.getenv("MAIL_DOMAIN", "homelab.local")

    SESSION_TTL_HOURS: int = int(os.getenv("SESSION_TTL_HOURS", "8"))

    # Orígenes permitidos para CORS en desarrollo (Vite dev server, etc).
    # En producción el propio FastAPI sirve el build de React, así que no hace falta.
    CORS_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    ]


settings = Settings()
