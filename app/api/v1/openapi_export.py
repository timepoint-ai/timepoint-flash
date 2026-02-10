"""OpenAPI schema convenience endpoint under the v1 prefix.

Endpoints:
    GET /api/v1/openapi.json — Returns the app's OpenAPI schema
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["openapi"])


@router.get("/openapi.json", include_in_schema=False)
async def openapi_v1(request: Request) -> JSONResponse:
    """Return the application's OpenAPI schema at a predictable v1 path.

    Useful for tooling that expects the schema at an API-versioned path.
    """
    schema = request.app.openapi()
    return JSONResponse(content=schema)
