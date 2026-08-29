"""Smoke test for BE-001 repository skeleton importability."""

import importlib
import unittest


class TestRepositorySkeletonSmoke(unittest.TestCase):
    """Verify that all foundational packages and modules are importable."""

    def test_import_services(self) -> None:
        """Test that all service packages and subpackages can be imported."""
        modules = [
            "services",
            "services.api",
            "services.api.routes",
            "services.api.schemas",
            "services.api.services",
            "services.api.repositories",
            "services.worker",
            "services.worker.jobs",
            "services.worker.ingestion",
            "services.worker.enrichment",
            "services.worker.persistence",
            "services.ml",
            "services.ml.features",
            "services.ml.training",
            "services.ml.evaluation",
            "services.ml.inference",
            "services.ml.calibration",
        ]
        for mod_name in modules:
            with self.subTest(module=mod_name):
                mod = importlib.import_module(mod_name)
                self.assertIsNotNone(mod)

    def test_import_packages(self) -> None:
        """Test that all shared packages can be imported."""
        modules = [
            "packages",
            "packages.schemas",
            "packages.geospatial",
            "packages.evidence",
        ]
        for mod_name in modules:
            with self.subTest(module=mod_name):
                mod = importlib.import_module(mod_name)
                self.assertIsNotNone(mod)


if __name__ == "__main__":
    unittest.main()
