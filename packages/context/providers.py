"""Provider abstractions and in-memory test providers for external context features."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from packages.context.matching import evaluate_spatial_association
from packages.context.models import ContextFeature, SpatialMatchRule
from packages.schemas.common import Coordinate


class ContextProvider(ABC):
    """Abstract interface for external geospatial context providers."""

    @abstractmethod
    def query_features_near(
        self,
        coordinate: Coordinate,
        radius_meters: float,
    ) -> list[ContextFeature]:
        """Query candidate features located near the specified coordinate.

        Args:
            coordinate: Target search coordinate (latitude, longitude).
            radius_meters: Search radius in geodesic meters.

        Returns:
            list[ContextFeature]: List of candidate context features.
        """
        ...


class InMemoryContextProvider(ContextProvider):
    """In-memory ContextProvider for deterministic, offline testing and evaluation."""

    def __init__(
        self,
        features: Sequence[ContextFeature] | None = None,
        provider_name: str = "in_memory",
        is_healthy: bool = True,
    ) -> None:
        self.features: list[ContextFeature] = list(features) if features else []
        self.provider_name = provider_name
        self.is_healthy = is_healthy

    def query_features_near(
        self,
        coordinate: Coordinate,
        radius_meters: float,
    ) -> list[ContextFeature]:
        """Query in-memory candidate features within radius_meters."""
        if not self.is_healthy:
            raise RuntimeError(
                f"External provider '{self.provider_name}' is unavailable."
            )

        results: list[ContextFeature] = []
        for feat in self.features:
            is_matched, _ = evaluate_spatial_association(
                target_coord=coordinate,
                feature=feat,
                max_radius_meters=radius_meters,
                rule=SpatialMatchRule.PROXIMITY_RADIUS,
            )
            if is_matched:
                results.append(feat)

        return results
