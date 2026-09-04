"""HTTP Client for OpenStreetMap Overpass API queries with retries and rate safety."""

import json
import logging
import time
from typing import Any

import httpx

from packages.config.settings import Settings, get_settings
from packages.logging import get_logger, log_with_context

logger = get_logger("packages.data.forests.client")


class OverpassApiError(Exception):
    """Exception raised when an Overpass API query fails or times out."""


class ForestOverpassClient:
    """Production client for querying OpenStreetMap forest geometries.

    Uses Overpass API with exponential backoff and query limits.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.endpoint_url = self.settings.OSM_OVERPASS_URL
        self.user_agent = self.settings.OSM_USER_AGENT
        self.timeout = float(self.settings.OSM_TIMEOUT_SECONDS)
        self.max_retries = int(self.settings.OSM_MAX_RETRIES)
        self.backoff_factor = float(self.settings.OSM_RETRY_BACKOFF_FACTOR)

    def build_country_query(
        self,
        country_code: str,
        limit: int | None = None,
        include_boundary: bool = False,
    ) -> str:
        """Construct Overpass QL query string for a country ISO code."""
        code = country_code.strip().upper()
        boundary_clauses = ""
        if include_boundary:
            boundary_clauses = (
                '  way["boundary"="forest"](area.searchArea);\n'
                '  relation["boundary"="forest"](area.searchArea);\n'
            )

        limit_clause = f" {limit}" if limit else ""
        return (
            f"[out:json][timeout:{int(self.timeout)}];\n"
            f'area["ISO3166-1"="{code}"][admin_level=2]->.searchArea;\n'
            f"(\n"
            f'  way["natural"="wood"](area.searchArea);\n'
            f'  relation["natural"="wood"](area.searchArea);\n'
            f'  way["landuse"="forest"](area.searchArea);\n'
            f'  relation["landuse"="forest"](area.searchArea);\n'
            f"{boundary_clauses}"
            f");\n"
            f"out geom{limit_clause};"
        )

    def build_bbox_query(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        limit: int | None = None,
        include_boundary: bool = False,
    ) -> str:
        """Construct Overpass QL query string for a bounding box."""
        bbox_str = f"{min_lat},{min_lon},{max_lat},{max_lon}"
        boundary_clauses = ""
        if include_boundary:
            boundary_clauses = (
                f'  way["boundary"="forest"]({bbox_str});\n'
                f'  relation["boundary"="forest"]({bbox_str});\n'
            )

        limit_clause = f" {limit}" if limit else ""
        return (
            f"[out:json][timeout:{int(self.timeout)}];\n"
            f"(\n"
            f'  way["natural"="wood"]({bbox_str});\n'
            f'  relation["natural"="wood"]({bbox_str});\n'
            f'  way["landuse"="forest"]({bbox_str});\n'
            f'  relation["landuse"="forest"]({bbox_str});\n'
            f"{boundary_clauses}"
            f");\n"
            f"out geom{limit_clause};"
        )

    def execute_query(self, query: str) -> dict[str, Any]:
        """Execute Overpass QL query with retry logic and exponential backoff."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                log_with_context(
                    logger,
                    logging.INFO,
                    f"Executing Overpass API query (attempt {attempt + 1}/"
                    f"{self.max_retries + 1})",
                    context={"endpoint": self.endpoint_url},
                )
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.endpoint_url,
                        data={"data": query},
                        headers=headers,
                    )

                    if response.status_code == 200:
                        try:
                            return response.json()
                        except json.JSONDecodeError as jde:
                            raise OverpassApiError(
                                f"Failed to parse Overpass JSON response: {jde}"
                            ) from jde

                    if response.status_code in (429, 502, 503, 504):
                        last_error = OverpassApiError(
                            f"Overpass API HTTP {response.status_code}: "
                            f"{response.text[:200]}"
                        )
                    else:
                        raise OverpassApiError(
                            f"Overpass API error HTTP {response.status_code}: "
                            f"{response.text[:300]}"
                        )
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e

            if attempt < self.max_retries:
                sleep_duration = self.backoff_factor * (2**attempt)
                log_with_context(
                    logger,
                    logging.WARNING,
                    f"Overpass query attempt {attempt + 1} failed. "
                    f"Retrying in {sleep_duration:.1f}s",
                    context={"error": str(last_error)},
                )
                time.sleep(sleep_duration)

        raise OverpassApiError(
            f"Overpass API query failed after {self.max_retries + 1} "
            f"attempts: {last_error}"
        )
