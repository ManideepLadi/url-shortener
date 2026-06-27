import logging
import ssl
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_CA_CERT_PATH = (
    Path(__file__).resolve().parents[2] / "certs" / "ca-certificate.crt"
)


def create_database_ssl_context() -> ssl.SSLContext:
    """
    Build SSL context for DigitalOcean Managed PostgreSQL.

    - verify-full (default): DATABASE_SSL_VERIFY_CA=true + CA cert
    - require only: DATABASE_SSL_VERIFY_CA=false — encrypted, no CA check (dev)
    """
    if not settings.database_ssl_verify_ca:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        logger.warning(
            "PostgreSQL SSL: encryption enabled, CA verification disabled (dev mode)"
        )
        return context

    context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    if settings.database_ca_cert:
        context.load_verify_locations(cadata=settings.database_ca_cert)
        logger.info("PostgreSQL SSL: verify-full using DATABASE_CA_CERT")
        return context

    if DEFAULT_CA_CERT_PATH.is_file():
        context.load_verify_locations(cafile=str(DEFAULT_CA_CERT_PATH))
        logger.info("PostgreSQL SSL: verify-full using %s", DEFAULT_CA_CERT_PATH)
        return context

    raise RuntimeError(
        "DATABASE_CA_CERT or certs/ca-certificate.crt is required when "
        "DATABASE_SSL_VERIFY_CA=true. For local dev only, set DATABASE_SSL_VERIFY_CA=false."
    )
