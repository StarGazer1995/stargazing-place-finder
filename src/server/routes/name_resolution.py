"""Resolve sky targets locally first, independently of survey image loading."""

import asyncio
import math
import re
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from stargazing_core import load_objects

router = APIRouter(tags=["telescope"])
REMOTE_DEADLINE_SECONDS = 5.0
SESAME_MIRRORS = (
    ("CDS", "https://cds.unistra.fr/cgi-bin/nph-sesame/-o/SVNI?"),
    ("Harvard", "https://vizier.cfa.harvard.edu/viz-bin/nph-sesame/-o/SVNI?"),
)


class ResolvedTarget(BaseModel):
    """Only finite ICRS coordinates are exposed, never catalog NaN fields."""

    name: str
    ra: float = Field(ge=0, lt=360, allow_inf_nan=False)
    dec: float = Field(ge=-90, le=90, allow_inf_nan=False)
    source: str


def _key(name: str) -> str:
    return "".join(name.split()).casefold()


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "RESOLVER_UNAVAILABLE",
            "message": "Name resolver unavailable; retry or use a catalog identifier.",
        },
    )


async def _resolve_remote(name: str) -> ResolvedTarget:
    async with httpx.AsyncClient(timeout=2.0, follow_redirects=True) as client:
        for source, base in SESAME_MIRRORS:
            try:
                response = await client.get(base + quote(name, safe=""))
                response.raise_for_status()
            except httpx.HTTPError:
                continue
            match = re.search(r"^%J\s+([+-]?[\d.]+)\s+([+-]?[\d.]+)", response.text, re.MULTILINE)
            if match:
                try:
                    ra, dec = map(float, match.groups())
                except ValueError:
                    continue
                if math.isfinite(ra) and math.isfinite(dec) and 0 <= ra < 360 and -90 <= dec <= 90:
                    return ResolvedTarget(name=name, ra=ra, dec=dec, source=source)
            # A network failure or malformed response is not evidence of absence.
            if re.search(r"^#!E.*(?:nothing found|not found|no match)", response.text, re.MULTILINE | re.IGNORECASE):
                raise HTTPException(
                    status_code=404, detail={"code": "OBJECT_NOT_FOUND", "message": "Object not found."}
                )
    raise _unavailable()


@router.get("/api/telescope/resolve", response_model=ResolvedTarget)
async def resolve_target(name: str = Query(min_length=1, max_length=120)) -> ResolvedTarget:
    """Resolve exact catalog IDs offline; bound all other name lookup to five seconds."""
    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail={"code": "INVALID_NAME", "message": "Enter an object name."})
    key = _key(name)
    for obj in load_objects():
        if _key(obj["name"]) == key:
            return ResolvedTarget(name=obj["name"], ra=obj["ra"], dec=obj["dec"], source="local_catalog")
    try:
        return await asyncio.wait_for(_resolve_remote(name), timeout=REMOTE_DEADLINE_SECONDS)
    except asyncio.TimeoutError:
        raise _unavailable() from None
