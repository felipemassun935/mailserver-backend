"""Contexto TLS compartido por los clientes IMAP y SMTP.

El certificado del mailserver tiene CN=homelab.miku-frog.ts.net (el nombre
por el que se accede vía Tailscale). Dentro de la red interna de Docker nos
conectamos por el nombre de servicio "mailserver", así que la verificación
de hostname del certificado siempre va a fallar aunque la cadena de
certificación sea válida y el tráfico esté cifrado. Deshabilitamos solo el
chequeo de hostname (check_hostname), no la verificación del certificado
en sí (verify_mode se mantiene en CERT_REQUIRED).
"""
import ssl


def internal_mailserver_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED
    return context
