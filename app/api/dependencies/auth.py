"""Optional ``X-API-Key`` check for mutating HTTP endpoints."""

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """
    If ``API_KEY`` is set in settings, require the same value in ``X-API-Key``.

    Empty / unset ``API_KEY`` → no check (local development).
    """
    expected = (get_settings().api_key or "").strip()
    if not expected:
        return
    if (x_api_key or "").strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
