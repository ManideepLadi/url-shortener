import logging
import ssl
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_CA_CERT_PATH = (
    Path(__file__).resolve().parents[2] / "certs" / "ca-certificate.crt"
)


def _load_ca_into_context(context: ssl.SSLContext, pem: str, source: str) -> None:
    try:
        context.load_verify_locations(cadata=pem)
    except ssl.SSLError as exc:
        raise RuntimeError(
            f"Invalid DATABASE_CA_CERT from {source}. "
            "Ensure the linked database injects ${db-dev.CA_CERT} or paste valid PEM content."
        ) from exc
    logger.info("PostgreSQL SSL: verify-full using %s", source)


def create_database_ssl_context() -> ssl.SSLContext:
    """
    Build SSL context for DigitalOcean Managed PostgreSQL.

    - verify-full: DATABASE_SSL_VERIFY_CA=true + CA cert
    - require only: DATABASE_SSL_VERIFY_CA=false — encrypted, no CA check
    """
    if not settings.database_ssl_verify_ca:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        logger.warning(
            "PostgreSQL SSL: encryption enabled, CA verification disabled"
        )
        return context

    context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    if settings.database_ca_cert:
        _load_ca_into_context(context, settings.database_ca_cert, "DATABASE_CA_CERT")
        return context

    if DEFAULT_CA_CERT_PATH.is_file():
        pem = DEFAULT_CA_CERT_PATH.read_text(encoding="utf-8")
        _load_ca_into_context(context, pem, str(DEFAULT_CA_CERT_PATH))
        return context

    raise RuntimeError(
        "DATABASE_SSL_VERIFY_CA=true but no CA certificate is configured. "
        "On App Platform, link the database and set DATABASE_CA_CERT=${db-dev.CA_CERT}. "
        "Or set DATABASE_SSL_VERIFY_CA=false to use encryption without CA verification."
    )
