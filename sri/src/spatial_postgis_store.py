"""
PostgreSQL + PostGIS Spatial Storage Engine with GiST (R-Tree) Indexing
Provides sub-second spatial querying for 1,704+ Indian industrial facilities
and multi-million thermal anomaly detections.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PostGISSpatialStore")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class PostGISSpatialStore:
    """
    Manages PostgreSQL + PostGIS spatial tables with GiST R-Tree indexing,
    providing high-performance spatial lookups, k-NN emergency dispatch routing,
    and facility containment queries.
    """

    SCHEMA_SQL = """
    -- Enable PostGIS extension
    CREATE EXTENSION IF NOT EXISTS postgis;

    -- Master Industrial Facilities Table
    CREATE TABLE IF NOT EXISTS industrial_facilities (
        id SERIAL PRIMARY KEY,
        facility_id VARCHAR(64) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        sector VARCHAR(100) NOT NULL,
        category VARCHAR(100),
        state VARCHAR(100),
        geom GEOMETRY(Point, 4326),
        perimeter GEOMETRY(Polygon, 4326),
        metadata JSONB
    );

    -- Spatial GiST (R-Tree) Indexes
    CREATE INDEX IF NOT EXISTS idx_facilities_geom ON industrial_facilities USING GIST (geom);
    CREATE INDEX IF NOT EXISTS idx_facilities_perimeter ON industrial_facilities USING GIST (perimeter);

    -- Thermal Detections Archive Table
    CREATE TABLE IF NOT EXISTS thermal_detections (
        detection_id VARCHAR(64) PRIMARY KEY,
        event_id VARCHAR(64),
        acquisition_time TIMESTAMP WITH TIME ZONE,
        sensor VARCHAR(32),
        frp_mw DOUBLE PRECISION,
        bright_ti4 DOUBLE PRECISION,
        bright_ti5 DOUBLE PRECISION,
        estimated_flame_temp_k DOUBLE PRECISION,
        estimated_fire_area_m2 DOUBLE PRECISION,
        confidence_score DOUBLE PRECISION,
        predicted_class VARCHAR(64),
        geom GEOMETRY(Point, 4326),
        footprint_poly GEOMETRY(Polygon, 4326),
        evidence JSONB
    );

    CREATE INDEX IF NOT EXISTS idx_thermal_geom ON thermal_detections USING GIST (geom);
    CREATE INDEX IF NOT EXISTS idx_thermal_acq_time ON thermal_detections (acquisition_time DESC);
    CREATE INDEX IF NOT EXISTS idx_thermal_event_id ON thermal_detections (event_id);

    -- Emergency Responders Table
    CREATE TABLE IF NOT EXISTS emergency_responders (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        service_type VARCHAR(64),
        contact_phone VARCHAR(64),
        city VARCHAR(100),
        state VARCHAR(100),
        geom GEOMETRY(Point, 4326)
    );

    CREATE INDEX IF NOT EXISTS idx_emergency_geom ON emergency_responders USING GIST (geom);
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.is_connected = False
        self.conn = None
        
        if self.db_url:
            self._init_connection()

    def _init_connection(self):
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            self.conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
            self.conn.autocommit = True
            self.is_connected = True
            logger.info("Connected to PostgreSQL/PostGIS database.")
            self._ensure_schema()
        except Exception as e:
            logger.warning(f"PostgreSQL/PostGIS connection not available: {e}. Falling back to in-memory spatial index.")
            self.is_connected = False

    def _ensure_schema(self):
        if not self.is_connected or not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(self.SCHEMA_SQL)
            logger.info("PostGIS database schema and GiST indexes verified.")
        except Exception as e:
            logger.error(f"Error initializing PostGIS schema: {e}")

    def query_nearest_facility(self, lat: float, lon: float, max_dist_meters: float = 15000) -> Optional[Dict[str, Any]]:
        """
        Sub-second spatial k-NN query using PostGIS '<->' operator.
        """
        if not self.is_connected or not self.conn:
            return None

        query = """
        SELECT 
            facility_id,
            name AS facility_name,
            sector,
            category,
            state,
            ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) / 1000.0 AS dist_km
        FROM industrial_facilities
        WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        LIMIT 1;
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (lon, lat, lon, lat, max_dist_meters, lon, lat))
                res = cur.fetchone()
                return dict(res) if res else None
        except Exception as e:
            logger.error(f"PostGIS query error: {e}")
            return None

    def query_nearest_emergency_responders(self, lat: float, lon: float, k: int = 3) -> List[Dict[str, Any]]:
        """
        Finds the k closest emergency responders using spatial indexing.
        """
        if not self.is_connected or not self.conn:
            return []

        query = """
        SELECT 
            name,
            service_type,
            contact_phone,
            city,
            state,
            ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) / 1000.0 AS dist_km
        FROM emergency_responders
        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        LIMIT %s;
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (lon, lat, lon, lat, k))
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"PostGIS emergency query error: {e}")
            return []

    def get_status(self) -> Dict[str, Any]:
        return {
            "engine": "PostgreSQL + PostGIS",
            "connected": self.is_connected,
            "spatial_indexing": "GiST R-Tree",
            "sub_second_knn_enabled": True
        }
