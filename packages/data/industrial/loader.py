"""Isolated data loader and enrichment pipeline for industrial infrastructure assets."""

import csv
import json
import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from packages.data.industrial.deduplication import (
    find_duplicate_candidates,
    link_duplicate_records,
)
from packages.data.industrial.normalizer import (
    compute_canonical_asset_id,
    normalize_coordinates,
    normalize_facility_name,
    normalize_industry_and_asset_type,
    normalize_operational_status,
    normalize_state_name,
)
from packages.schemas.enums import ContextType
from packages.schemas.industrial_asset import (
    AssetType,
    IndustrialAsset,
    IndustrialAssetCollection,
    IndustryType,
    OperationalStatus,
)

logger = logging.getLogger(__name__)

# Default file paths relative to project root
DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_DATA2_DIR = DEFAULT_BASE_DIR / "data2" / "industrial_infra"
DEFAULT_GEO_DIR = DEFAULT_BASE_DIR / "data2" / "lulc_and_geo"


def _col_letter_to_index(col_letter: str) -> int:
    """Convert Excel column letter (e.g. 'A', 'Z', 'AA') to 0-indexed column integer."""
    idx = 0
    for char in col_letter.upper():
        idx = idx * 26 + (ord(char) - ord("A") + 1)
    return idx - 1


def _read_xlsx_sheet_aligned(
    xlsx_path: Path, target_sheet_name: str
) -> list[list[str]]:
    """Parse an XLSX worksheet using pure Python standard library.

    Zero external dependencies required.
    """
    with zipfile.ZipFile(xlsx_path, "r") as z:
        # 1. Read shared strings
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for si in tree.findall("main:si", ns):
                t_el = si.find("main:t", ns)
                if t_el is not None and t_el.text:
                    shared_strings.append(t_el.text)
                else:
                    r_texts = [
                        t.text
                        for t in si.findall(".//main:t", ns)
                        if t.text is not None
                    ]
                    shared_strings.append("".join(r_texts))

        # 2. Find target sheet relationship ID in workbook.xml
        wb_tree = ET.fromstring(z.read("xl/workbook.xml"))
        ns_wb = {
            "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }
        sheet_r_id = None
        for s in wb_tree.findall(".//main:sheet", ns_wb):
            if s.attrib.get("name") == target_sheet_name:
                sheet_r_id = s.attrib.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                )
                break

        if not sheet_r_id:
            return []

        # 3. Resolve target sheet path in workbook.xml.rels
        rels_tree = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        ns_rel = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
        sheet_target = None
        for rel in rels_tree.findall("rel:Relationship", ns_rel):
            if rel.attrib.get("Id") == sheet_r_id:
                sheet_target = "xl/" + rel.attrib.get("Target", "").lstrip("/")
                break

        if not sheet_target or sheet_target not in z.namelist():
            return []

        # 4. Stream rows and place cells in exact column positions
        sheet_tree = ET.fromstring(z.read(sheet_target))
        ns_s = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

        parsed_rows: list[list[str]] = []
        for row_el in sheet_tree.findall(".//main:row", ns_s):
            row_dict: dict[int, str] = {}
            max_col = 0
            for c in row_el.findall("main:c", ns_s):
                r_ref = c.attrib.get("r", "")
                m = re.match(r"^([A-Z]+)", r_ref)
                col_idx = _col_letter_to_index(m.group(1)) if m else len(row_dict)
                max_col = max(max_col, col_idx)

                t_attr = c.attrib.get("t")
                v_el = c.find("main:v", ns_s)
                val = ""
                if v_el is not None and v_el.text is not None:
                    val = v_el.text
                    if t_attr == "s":
                        idx_ss = int(val)
                        val = (
                            shared_strings[idx_ss]
                            if idx_ss < len(shared_strings)
                            else val
                        )
                else:
                    is_el = c.find(".//main:t", ns_s)
                    if is_el is not None and is_el.text:
                        val = is_el.text

                row_dict[col_idx] = val

            row_list = [row_dict.get(i, "") for i in range(max_col + 1)]
            parsed_rows.append(row_list)

        return parsed_rows


class IndustrialDataLoader:
    """Resilient, read-only loader for industrial assets.

    Supports deterministic enrichment, spatial state lookup, and deduplication.
    """

    def __init__(
        self,
        data_dir: Path | str | None = None,
        geo_dir: Path | str | None = None,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA2_DIR
        self.geo_dir = Path(geo_dir) if geo_dir else DEFAULT_GEO_DIR
        self._state_geometries: list[tuple[str, Any]] | None = None

    def _get_state_geometries(self) -> list[tuple[str, Any]]:
        """Load and cache state boundary geometries for spatial state attribution."""
        if self._state_geometries is not None:
            return self._state_geometries

        state_geojson_path = self.geo_dir / "india_state.geojson"
        if not state_geojson_path.is_file():
            self._state_geometries = []
            return self._state_geometries

        try:
            from shapely.geometry import shape

            with open(state_geojson_path, encoding="utf-8") as f:
                gj = json.load(f)

            geoms: list[tuple[str, Any]] = []
            for feat in gj.get("features", []):
                state_name = feat.get("properties", {}).get("NAME_1")
                geom_dict = feat.get("geometry")
                if state_name and geom_dict:
                    geoms.append((state_name, shape(geom_dict)))

            self._state_geometries = geoms
        except Exception as exc:
            logger.warning("Could not load state boundaries: %s", exc)
            self._state_geometries = []

        return self._state_geometries

    def _lookup_spatial_state(self, lat: float, lon: float) -> str | None:
        """Find the Indian State/UT name containing the coordinate."""
        states = self._get_state_geometries()
        if not states:
            return None

        try:
            from shapely.geometry import Point

            pt = Point(lon, lat)
            for name, geom in states:
                if geom.contains(pt):
                    return normalize_state_name(name)
        except Exception:
            return None

        return None

    def _load_gppd_index(self) -> dict[tuple[float, float, str], dict[str, Any]]:
        """Build coordinate+name lookup index for WRI GPPD power plants."""
        gppd_path = self.data_dir / "global_power_plant_database.csv"
        if not gppd_path.is_file():
            return {}

        index: dict[tuple[float, float, str], dict[str, Any]] = {}
        try:
            with open(gppd_path, encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("country") != "IND":
                        continue
                    try:
                        lat_r = round(float(row["latitude"]), 4)
                        lon_r = round(float(row["longitude"]), 4)
                        raw_name_key = str(row.get("name", "")).strip().lower()
                        norm_name_key = normalize_facility_name(
                            row.get("name", "")
                        ).lower()
                        index[(lat_r, lon_r, raw_name_key)] = row
                        index[(lat_r, lon_r, norm_name_key)] = row
                    except (ValueError, KeyError):
                        continue
        except Exception as exc:
            logger.warning("Error loading GPPD database: %s", exc)

        return index

    def _load_gogpt_index(self) -> dict[tuple[float, float, str], dict[str, Any]]:
        """Build coordinate+name lookup index for GEM GOGPT gas and oil units."""
        gogpt_path = (
            self.data_dir
            / "Global Oil and Gas Plant Tracker (GOGPT) - August 2026.xlsx"
        )
        if not gogpt_path.is_file():
            return {}

        index: dict[tuple[float, float, str], dict[str, Any]] = {}
        try:
            parsed_rows = _read_xlsx_sheet_aligned(gogpt_path, "Gas & Oil Units")
            if not parsed_rows:
                return {}

            headers = [str(c).strip() for c in parsed_rows[0]]
            if "Country/Area" not in headers or "Plant name" not in headers:
                return {}

            c_idx = headers.index("Country/Area")
            name_idx = headers.index("Plant name")
            lat_idx = next(i for i, h in enumerate(headers) if "lat" in h.lower())
            lon_idx = next(i for i, h in enumerate(headers) if "lon" in h.lower())

            for r in parsed_rows[1:]:
                if len(r) <= max(c_idx, name_idx, lat_idx, lon_idx):
                    continue
                if str(r[c_idx] or "").strip().lower() != "india":
                    continue
                try:
                    lat_r = round(float(r[lat_idx]), 4)
                    lon_r = round(float(r[lon_idx]), 4)
                    raw_name_key = str(r[name_idx] or "").strip().lower()
                    norm_name_key = normalize_facility_name(r[name_idx]).lower()
                    row_dict = dict(
                        zip(
                            headers,
                            [str(c) if c is not None else "" for c in r],
                            strict=False,
                        )
                    )
                    index[(lat_r, lon_r, raw_name_key)] = row_dict
                    index[(lat_r, lon_r, norm_name_key)] = row_dict
                except (ValueError, TypeError):
                    continue
        except Exception as exc:
            logger.warning("Error loading GOGPT database: %s", exc)

        return index

    def load_primary_master_facilities(
        self,
        enrich: bool = True,
        detect_duplicates: bool = True,
    ) -> IndustrialAssetCollection:
        """Load and normalize the 1,704 primary industrial facilities.

        Args:
            enrich: If True, cross-references GPPD and GOGPT to enrich IDs,
                owners, and dates.
            detect_duplicates: If True, identifies co-located and cross-provider
                duplicate pairs.

        Returns:
            IndustrialAssetCollection: Validated collection of normalized assets.
        """
        csv_path = self.data_dir / "master_india_industrial_facilities.csv"
        if not csv_path.is_file():
            raise FileNotFoundError(f"Master industrial CSV not found at {csv_path}")

        gppd_index = self._load_gppd_index() if enrich else {}
        gogpt_index = self._load_gogpt_index() if enrich else {}

        assets: list[IndustrialAsset] = []

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_name = row.get("name")
                name = normalize_facility_name(raw_name)

                lat_norm, lon_norm, is_valid_coord = normalize_coordinates(
                    row.get("lat"), row.get("lon")
                )

                raw_type = row.get("type")
                raw_cat = row.get("category")
                raw_source = row.get("source") or "Master Industrial Dataset"

                industry, asset_type, context_type = normalize_industry_and_asset_type(
                    raw_type=raw_type,
                    raw_category=raw_cat,
                )

                # Parse capacity
                capacity_val: float | None = None
                raw_cap = row.get("capacity_mw")
                if raw_cap and raw_cap.strip():
                    try:
                        c_float = float(raw_cap.strip())
                        if c_float >= 0.0:
                            capacity_val = round(c_float, 2)
                    except ValueError:
                        pass

                capacity_unit = "MW" if capacity_val is not None else None

                # Enrichment fields
                source_id: str | None = None
                owner: str | None = None
                operator: str | None = None
                state: str | None = None
                district: str | None = None
                city: str | None = None
                primary_fuel: str | None = None
                commissioning_year: int | None = None
                status = OperationalStatus.OPERATING
                metadata: dict[str, Any] = {
                    "original_type": raw_type,
                    "original_category": raw_cat,
                    "original_source": raw_source,
                }

                lookup_key = (round(lat_norm, 4), round(lon_norm, 4), name.lower())

                # Check WRI GPPD enrichment
                if raw_source == "WRI Power Database" and lookup_key in gppd_index:
                    g_row = gppd_index[lookup_key]
                    source_id = g_row.get("gppd_idnr")
                    owner = g_row.get("owner") or None
                    primary_fuel = g_row.get("primary_fuel") or None
                    comm_str = g_row.get("commissioning_year")
                    if comm_str and comm_str.strip():
                        import contextlib

                        with contextlib.suppress(ValueError):
                            commissioning_year = int(float(comm_str.strip()))
                    metadata["gppd_url"] = g_row.get("url")
                    metadata["gppd_source"] = g_row.get("source")
                    metadata["gppd_geolocation_source"] = g_row.get(
                        "geolocation_source"
                    )

                # Check GEM GOGPT enrichment
                elif (
                    raw_source == "GEM Oil & Gas Tracker" and lookup_key in gogpt_index
                ):
                    gem_row = gogpt_index[lookup_key]
                    source_id = gem_row.get("GEM unit ID") or gem_row.get(
                        "GEM location ID"
                    )
                    operator = gem_row.get("Operator(s)") or None
                    owner = gem_row.get("Owner(s)") or gem_row.get("Parent(s)") or None
                    state = normalize_state_name(gem_row.get("State/Province"))
                    district = gem_row.get("Major area (prefecture, district)") or None
                    city = gem_row.get("City") or None
                    primary_fuel = (
                        gem_row.get("Fuel classification")
                        or gem_row.get("Fuel")
                        or None
                    )
                    status = normalize_operational_status(gem_row.get("Status"))
                    start_yr = gem_row.get("Start year")
                    if start_yr and start_yr.strip():
                        import contextlib

                        with contextlib.suppress(ValueError):
                            commissioning_year = int(float(start_yr.strip()))
                    metadata["wiki_url"] = gem_row.get("Wiki URL")
                    metadata["gem_location_id"] = gem_row.get("GEM location ID")

                # If state not populated from source, perform spatial state lookup
                if not state and is_valid_coord:
                    state = self._lookup_spatial_state(lat_norm, lon_norm)

                if "wri" in raw_source.lower():
                    provider_tag = "wri"
                elif "gem" in raw_source.lower():
                    provider_tag = "gem"
                else:
                    provider_tag = "master"

                asset_id = compute_canonical_asset_id(
                    provider=provider_tag,
                    raw_id=source_id,
                    name=name,
                    latitude=lat_norm,
                    longitude=lon_norm,
                    primary_fuel=primary_fuel,
                )

                asset = IndustrialAsset(
                    id=asset_id,
                    name=name,
                    asset_type=asset_type,
                    industry=industry,
                    context_type=context_type,
                    latitude=lat_norm,
                    longitude=lon_norm,
                    country="India",
                    state=state,
                    district=district,
                    city=city,
                    operator=operator,
                    owner=owner,
                    status=status,
                    capacity=capacity_val,
                    capacity_unit=capacity_unit,
                    primary_fuel=primary_fuel,
                    commissioning_year=commissioning_year,
                    source=raw_source,
                    source_id=source_id,
                    linked_source_ids=[],
                    is_map_eligible=is_valid_coord,
                    metadata=metadata,
                )
                assets.append(asset)

        # Duplicate detection and non-destructive linking
        duplicate_candidates_count = 0
        if detect_duplicates:
            candidates = find_duplicate_candidates(assets, max_distance_meters=1000.0)
            duplicate_candidates_count = len(candidates)
            assets = link_duplicate_records(assets, candidates, link_threshold=0.70)

        # Deterministic sorting: (industry, latitude, longitude, id)
        assets.sort(
            key=lambda a: (
                a.industry.value,
                a.latitude,
                a.longitude,
                a.id,
            )
        )

        sources_summary = dict(Counter(a.source for a in assets))
        industries_summary = dict(Counter(a.industry.value for a in assets))

        return IndustrialAssetCollection(
            assets=assets,
            total_count=len(assets),
            map_eligible_count=sum(1 for a in assets if a.is_map_eligible),
            sources_summary=sources_summary,
            industries_summary=industries_summary,
            duplicate_candidates_count=duplicate_candidates_count,
        )

    def load_expansion_steel_facilities(self) -> list[IndustrialAsset]:
        """Load and normalize heavy metallurgy and steel plants."""
        steel_filename = (
            "Plant-level_data_Global_Iron_and_Steel_Tracker_June_2026_V1.xlsx"
        )
        steel_path = self.data_dir / "gem-download" / steel_filename
        if not steel_path.is_file():
            # Try root directory fallback
            steel_path = DEFAULT_BASE_DIR / steel_filename

        if not steel_path.is_file():
            logger.warning("GEM Steel tracker not found at %s", steel_path)
            return []

        assets: list[IndustrialAsset] = []
        try:
            parsed_rows = _read_xlsx_sheet_aligned(steel_path, "Plant data")
            if not parsed_rows:
                return []

            headers = [str(c).strip() for c in parsed_rows[0]]
            c_idx = headers.index("Country/area")
            name_idx = headers.index("Plant name (English)")
            coord_idx = headers.index("Coordinates")
            id_idx = headers.index("GEM plant ID")
            subnat_idx = headers.index("Subnational unit")
            muni_idx = headers.index("Municipality")
            owner_idx = headers.index("Owner")
            wiki_idx = headers.index("GEM wiki page")

            for r in parsed_rows[1:]:
                if len(r) <= max(c_idx, name_idx, coord_idx, id_idx):
                    continue
                if str(r[c_idx] or "").strip().lower() != "india":
                    continue

                raw_coords = r[coord_idx]
                if not raw_coords or "," not in str(raw_coords):
                    continue

                try:
                    parts = str(raw_coords).split(",")
                    lat_norm, lon_norm, is_valid = normalize_coordinates(
                        parts[0], parts[1]
                    )
                except Exception:
                    continue

                if not is_valid:
                    continue

                plant_name = normalize_facility_name(r[name_idx])
                plant_id = str(r[id_idx] or "").strip()
                state = (
                    normalize_state_name(r[subnat_idx]) if len(r) > subnat_idx else None
                )
                city = (
                    str(r[muni_idx] or "").strip() or None
                    if len(r) > muni_idx
                    else None
                )
                owner = (
                    str(r[owner_idx] or "").strip() or None
                    if len(r) > owner_idx
                    else None
                )
                wiki_url = str(r[wiki_idx] or "").strip() if len(r) > wiki_idx else ""

                asset_id = compute_canonical_asset_id(
                    provider="gem_steel",
                    raw_id=plant_id,
                    name=plant_name,
                    latitude=lat_norm,
                    longitude=lon_norm,
                )

                asset = IndustrialAsset(
                    id=asset_id,
                    name=plant_name,
                    asset_type=AssetType.STEEL_PLANT,
                    industry=IndustryType.METALLURGY,
                    context_type=ContextType.INDUSTRIAL,
                    latitude=lat_norm,
                    longitude=lon_norm,
                    country="India",
                    state=state,
                    district=None,
                    city=city,
                    operator=None,
                    owner=owner,
                    status=OperationalStatus.OPERATING,
                    capacity=None,
                    capacity_unit="ttpa",
                    primary_fuel="metallurgical_coal",
                    commissioning_year=None,
                    source="GEM Iron & Steel Tracker",
                    source_id=plant_id,
                    linked_source_ids=[],
                    is_map_eligible=True,
                    metadata={"wiki_url": wiki_url},
                )
                assets.append(asset)
        except Exception as exc:
            logger.warning("Error loading steel tracker: %s", exc)

        return assets
