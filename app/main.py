import os
import time
from datetime import datetime
from typing import Any, Dict, List

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from search_engine.search_ops import search_manual_mapping, search_color_mapping
from search_engine.utils import search_engine_client, load_model, MANUAL_MAPPING, SEARCH_CONFIDENCE, COLOR_MAPPING

# Initialize FastAPI app
app = FastAPI()

# Allow all origins for CORS
origins = ["*"]

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Load a machine learning model used for search scoring or embedding
MODEL = load_model()

# Connect to the search engine client (e.g., Elasticsearch)
SEARCH_ENGINE = search_engine_client()

# Per-check deadline for /health. A health check that can hang is worse than
# none, so this stays well below any uptime checker's own timeout.
HEALTH_TIMEOUT = float(os.getenv("HEALTH_TIMEOUT_SECONDS", "5"))

def _run_check(name: str, check):
    """Run one dependency check, recording latency and never raising."""
    started = time.monotonic()
    try:
        detail = check()
        ok = True
    except Exception as exc:
        ok = False
        detail = f"{type(exc).__name__}: {exc}"
    return {
        "ok": ok,
        "latencyMs": int((time.monotonic() - started) * 1000),
        "detail": detail,
        "critical": True,
    }


def _check_elasticsearch() -> str:
    """
    Confirm Elasticsearch answers and still holds the mapping index.

    The timeout goes through .options(): in elasticsearch-py 8 the generated
    API methods do not take request_timeout as a keyword argument.
    """
    client = SEARCH_ENGINE.options(request_timeout=HEALTH_TIMEOUT)
    if not client.ping():
        raise RuntimeError("ping failed")
    if not client.indices.exists(index=MANUAL_MAPPING):
        raise RuntimeError(f"index '{MANUAL_MAPPING}' is missing")
    return f"reachable, index '{MANUAL_MAPPING}' present"


def _check_model() -> str:
    """The sentence transformer is loaded once at import; confirm it is there."""
    if MODEL is None:
        raise RuntimeError("sentence transformer not loaded")
    return "sentence transformer loaded"


@app.get("/health")
def health() -> JSONResponse:
    """
    Report whether this service can actually answer a tag lookup.

    Returns 200 while every dependency answers and 503 otherwise, so an uptime
    check needs no body parsing, while the body names each dependency with its
    latency so an alert can say what broke.

    Elasticsearch going away is exactly how this service failed before, and it
    showed up only as 500s on the search endpoints.
    """
    started = time.monotonic()
    checks: Dict[str, Any] = {
        "elasticsearch": _run_check("elasticsearch", _check_elasticsearch),
        "model": _run_check("model", _check_model),
    }
    healthy = all(c["ok"] for c in checks.values())

    return JSONResponse(
        content={
            "status": "ok" if healthy else "degraded",
            "timestamp": f"{datetime.now():%Y-%m-%dT%H:%M:%S%z}",
            "durationMs": int((time.monotonic() - started) * 1000),
            "checks": checks,
        },
        status_code=status.HTTP_200_OK
        if healthy
        else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.get("/search_osm_tag_v2")
def func_search_in_manual_mapping(word: str, limit: int):
    """
    Search for OSM (OpenStreetMap) tags using a manually defined mapping index.

    Args:
        word (str): The search keyword to look up in the manual mapping.
        limit (int): Maximum number of results to return.

    Returns:
        List[Dict]: A list of matched results with scores and tags.

    Description:
        This endpoint uses a custom search engine and preloaded model to perform
        a semantic search over a manually curated OSM tag index. The results are
        filtered by confidence threshold and limited by the `limit` parameter.
    """
    return search_manual_mapping(word=word,
                                 model=MODEL,
                                 client=SEARCH_ENGINE,
                                 limit=limit,
                                 confidence=SEARCH_CONFIDENCE,
                                 index_name=MANUAL_MAPPING)

@app.get("/color_mapping")
def func_color_mapping(color: str):
    """
    Search for a tag mapping related to a given color.

    Args:
        color (str): The color to search for in the color mapping index.

    Returns:
        Dict or List[Dict]: The most relevant result associated with the given color.

    Description:
        This endpoint queries the color mapping index to find semantic matches
        for the provided color string. It returns the top result (limit = 1).
    """
    return search_color_mapping(word=color,
                                client=SEARCH_ENGINE,
                                index_name=COLOR_MAPPING,
                                limit=1)