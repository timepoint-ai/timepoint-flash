"""HTTP client for Clockchain entity resolution API.

Resolves character names to persistent entity IDs via the Clockchain
figures batch-resolve endpoint. All failures are gracefully degraded
to empty results — entity resolution is optional.

Examples:
    >>> from app.core.entity_client import resolve_figures
    >>> mapping = await resolve_figures(["Julius Caesar", "Brutus"])
    >>> mapping
    {"Julius Caesar": "fig_abc123", "Brutus": "fig_def456"}

Tests:
    - tests/unit/test_entity_client.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Timeouts: 5s connect, 10s read
_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)


def _get_base_url() -> str:
    """Return the base URL for entity resolution requests."""
    return settings.CLOCKCHAIN_ENTITY_URL or settings.CLOCKCHAIN_URL


def _get_headers() -> dict[str, str]:
    """Return auth headers for Clockchain requests."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = settings.CLOCKCHAIN_SERVICE_KEY
    if key:
        headers["X-Service-Key"] = key
    return headers


async def resolve_figures(
    names: list[str],
    entity_type: str = "person",
) -> dict[str, str]:
    """Resolve character names to Clockchain entity IDs.

    Calls POST /api/v1/figures/resolve/batch on the Clockchain (or Gateway).
    Returns an empty dict on any failure — entity resolution must never
    block generation.

    Args:
        names: List of character names to resolve.
        entity_type: Entity type hint (default "person").

    Returns:
        Mapping of {name: entity_id} for successfully resolved names.
    """
    if not names:
        return {}

    base_url = _get_base_url()
    if not base_url:
        logger.debug(
            "Entity resolution skipped: no CLOCKCHAIN_ENTITY_URL or CLOCKCHAIN_URL configured"
        )
        return {}

    url = f"{base_url.rstrip('/')}/api/v1/figures/resolve/batch"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                url,
                json={"names": [{"display_name": n, "entity_type": entity_type} for n in names]},
                headers=_get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            # Response: {"results": [{"figure": {"id": "...", "display_name": "..."}, "created": bool}, ...]}
            results: list[dict] = data.get("results", [])
            resolved: dict[str, str] = {}
            for item in results:
                figure = item.get("figure", {})
                display_name = figure.get("display_name", "")
                figure_id = figure.get("id", "")
                if display_name and figure_id:
                    resolved[display_name] = figure_id
            logger.debug(f"Entity resolution: {len(resolved)}/{len(names)} names resolved")
            return resolved

    except httpx.TimeoutException:
        logger.warning("Entity resolution timed out — continuing without entity IDs")
        return {}
    except httpx.HTTPStatusError as exc:
        logger.warning(
            f"Entity resolution HTTP {exc.response.status_code} — continuing without entity IDs"
        )
        return {}
    except Exception:
        logger.warning("Entity resolution failed — continuing without entity IDs", exc_info=True)
        return {}


@dataclass
class FigureData:
    """Rich figure data from Clockchain, including grounding status.

    Attributes:
        id: Clockchain figure ID.
        display_name: Canonical display name.
        aliases: Known aliases for this entity.
        entity_type: Type of entity (person, organization, place).
        grounding_status: Grounding state (ungrounded, grounded, failed, skipped).
        grounded_at: Timestamp of last grounding (if grounded).
        grounding_confidence: Confidence score of grounding (0.0-1.0).
        external_ids: External identifiers (e.g. grounding_sources).
        wikidata_qid: Wikidata QID if available.
    """

    id: str = ""
    display_name: str = ""
    aliases: list[str] = field(default_factory=list)
    entity_type: str = "person"
    grounding_status: str = "ungrounded"
    grounded_at: datetime | None = None
    grounding_confidence: float = 0.0
    external_ids: dict = field(default_factory=dict)
    wikidata_qid: str | None = None


async def resolve_figures_with_data(
    names: list[str],
    entity_type: str = "person",
) -> dict[str, FigureData]:
    """Resolve character names to full Clockchain figure data.

    Like resolve_figures but returns rich FigureData including grounding
    status, aliases, external IDs, and confidence scores.

    Args:
        names: List of character names to resolve.
        entity_type: Entity type hint (default "person").

    Returns:
        Mapping of {name: FigureData} for successfully resolved names.
        Returns empty dict on any failure — never blocks generation.
    """
    if not names:
        return {}

    base_url = _get_base_url()
    if not base_url:
        logger.debug(
            "Entity resolution skipped: no CLOCKCHAIN_ENTITY_URL or CLOCKCHAIN_URL configured"
        )
        return {}

    url = f"{base_url.rstrip('/')}/api/v1/figures/resolve/batch"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                url,
                json={"names": [{"display_name": n, "entity_type": entity_type} for n in names]},
                headers=_get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            results: list[dict] = data.get("results", [])
            resolved: dict[str, FigureData] = {}
            for item in results:
                figure = item.get("figure", {})
                display_name = figure.get("display_name", "")
                figure_id = figure.get("id", "")
                if display_name and figure_id:
                    external_ids = figure.get("external_ids", {})
                    grounded_at_str = figure.get("grounded_at")
                    grounded_at = None
                    if grounded_at_str:
                        try:
                            grounded_at = datetime.fromisoformat(grounded_at_str)
                        except (ValueError, TypeError):
                            pass

                    resolved[display_name] = FigureData(
                        id=figure_id,
                        display_name=display_name,
                        aliases=figure.get("aliases", []),
                        entity_type=figure.get("entity_type", entity_type),
                        grounding_status=figure.get("grounding_status", "ungrounded"),
                        grounded_at=grounded_at,
                        grounding_confidence=float(figure.get("grounding_confidence", 0.0)),
                        external_ids=external_ids,
                        wikidata_qid=external_ids.get("wikidata_qid"),
                    )

            logger.debug(
                f"Entity resolution (with data): {len(resolved)}/{len(names)} names resolved"
            )
            return resolved

    except httpx.TimeoutException:
        logger.warning("Entity resolution (with data) timed out — continuing without figure data")
        return {}
    except httpx.HTTPStatusError as exc:
        logger.warning(
            f"Entity resolution (with data) HTTP {exc.response.status_code} — "
            "continuing without figure data"
        )
        return {}
    except Exception:
        logger.warning(
            "Entity resolution (with data) failed — continuing without figure data",
            exc_info=True,
        )
        return {}
