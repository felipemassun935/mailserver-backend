# Webmail backend

FastAPI sin base de datos propia: el login es un intento de conexión IMAP
contra Dovecot. Si las credenciales son válidas, se guardan en memoria del
proceso asociadas a un token de sesión random (TTL configurable, sin
persistencia entre reinicios).

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Requiere poder resolver `IMAP_HOST`/`SMTP_HOST` (por defecto `mailserver`,
el nombre del servicio Docker). Para probar contra el mailserver real desde
fuera de Docker, apuntar esas variables a `localhost` o a la IP/hostname que
corresponda.

## Endpoints

- `POST /api/auth/login` `{email, password}` → `{token, email}`
- `POST /api/auth/logout` (header `Authorization: Bearer <token>`)
- `GET  /api/messages?folder=INBOX&limit=50`
- `GET  /api/messages/{uid}?folder=INBOX`
- `POST /api/messages/send` `{to, subject, body}`

## Build de un solo contenedor

Ver `Dockerfile` y `docker-compose.yml`: el build junta este repo con
`mailserver-frontend` (como carpeta hermana) para que un mismo contenedor
FastAPI sirva la API y los estáticos del build de React.
