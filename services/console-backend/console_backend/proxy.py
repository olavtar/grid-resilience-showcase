# This project was developed with assistance from AI tools.

"""HTTP proxy helpers for forwarding requests to backend services."""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from fastapi import HTTPException

logger = structlog.get_logger()


async def proxy_get(client: httpx.AsyncClient, url: str) -> Any:
    """Forward a GET request to a backend service."""
    try:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.RequestError as e:
        logger.error("proxy_request_failed", url=url, error=str(e))
        raise HTTPException(status_code=502, detail=f"Upstream unreachable: {url}") from None
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from None


async def proxy_post(
    client: httpx.AsyncClient, url: str, body: dict[str, Any] | None = None
) -> Any:
    """Forward a POST request to a backend service."""
    try:
        resp = await client.post(url, json=body, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.RequestError as e:
        logger.error("proxy_request_failed", url=url, error=str(e))
        raise HTTPException(status_code=502, detail=f"Upstream unreachable: {url}") from None
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from None
