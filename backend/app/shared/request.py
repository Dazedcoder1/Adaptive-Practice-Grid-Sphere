import ipaddress

from fastapi import Request

from app.config.settings import settings
from app.shared.exceptions import Forbidden


def _valid_ip(value: str | None) -> str | None:
    try:
        return str(ipaddress.ip_address(value.strip())) if value else None
    except ValueError:
        return None


def client_ip(request: Request) -> str | None:
    """Caller's IP. X-Forwarded-For is client-controlled, so it's only honoured when
    TRUST_PROXY_HEADERS=true (i.e. behind our own nginx, which overwrites it)."""
    if settings.trust_proxy_headers:
        fwd = request.headers.get("x-forwarded-for")
        if fwd and (ip := _valid_ip(fwd.split(",")[0])):
            return ip
    return _valid_ip(request.client.host if request.client else None)


def user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua[:255] if ua else None


def require_trusted_origin(request: Request) -> None:
    """CSRF guard for cookie-authenticated endpoints (refresh/logout): browsers always send
    Origin on cross-site POSTs, so reject any origin we don't serve."""
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") not in {o.rstrip("/") for o in settings.cors_origins}:
        raise Forbidden("Untrusted origin", code="bad_origin")
