#!/usr/bin/env bash
# ==============================================================================
# SIH26162 - DB-001 PostGIS Infrastructure Validation Script
# ==============================================================================
set -euo pipefail

SERVICE_NAME="postgres-postgis"
CONTAINER_NAME="sih26162-postgres-postgis"
DB_NAME="${POSTGRES_DB:-sih26162}"
DB_USER="${POSTGRES_USER:-sih_user}"

echo "============================================================"
echo "SIH26162: Validating PostGIS Infrastructure (DB-001)"
echo "============================================================"

# 1. Check container running state
if ! docker compose ps --services --filter "status=running" | grep -q "${SERVICE_NAME}"; then
    echo "[FAIL] Service ${SERVICE_NAME} is not currently running."
    echo "Run 'docker compose up -d' first."
    exit 1
fi
echo "[PASS] 1. PostgreSQL container service is running."

# 2. Check healthcheck status
HEALTH_STATUS=$(docker inspect --format='{{json .State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo '"unknown"')
if [ "${HEALTH_STATUS}" != '"healthy"' ]; then
    echo "[WARN] Container health status is currently ${HEALTH_STATUS}. Waiting briefly..."
    for i in {1..10}; do
        HEALTH_STATUS=$(docker inspect --format='{{json .State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo '"unknown"')
        if [ "${HEALTH_STATUS}" = '"healthy"' ]; then
            break
        fi
        sleep 1
    done
fi

if [ "${HEALTH_STATUS}" = '"healthy"' ]; then
    echo "[PASS] 2. PostgreSQL healthcheck reports healthy."
else
    echo "[FAIL] 2. Container healthcheck status is ${HEALTH_STATUS} (expected 'healthy')."
    exit 1
fi

# 3. Connectivity check
if docker compose exec -T "${SERVICE_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
    echo "[PASS] 3. PostgreSQL connectivity verified with pg_isready."
else
    echo "[FAIL] 3. pg_isready connectivity failed."
    exit 1
fi

# 4. Check PostGIS extension presence
EXT_NAME=$(docker compose exec -T "${SERVICE_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT extname FROM pg_extension WHERE extname = 'postgis';" | tr -d '\r\n')
if [ "${EXT_NAME}" = "postgis" ]; then
    echo "[PASS] 4. PostGIS extension exists in database '${DB_NAME}'."
else
    echo "[FAIL] 4. PostGIS extension not found in database '${DB_NAME}'."
    exit 1
fi

# 5. Query PostGIS version
POSTGIS_VER=$(docker compose exec -T "${SERVICE_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT PostGIS_Version();" | tr -d '\r\n')
if [ -n "${POSTGIS_VER}" ]; then
    echo "[PASS] 5. PostGIS version queried successfully: ${POSTGIS_VER}"
else
    echo "[FAIL] 5. Failed to query PostGIS version."
    exit 1
fi

# 6. Spatial expression execution
SPATIAL_OUT=$(docker compose exec -T "${SERVICE_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT ST_AsText(ST_Point(77.2090, 28.6139, 4326));" | tr -d '\r\n')
EXPECTED_POINT="POINT(77.209 28.6139)"
if [ "${SPATIAL_OUT}" = "${EXPECTED_POINT}" ]; then
    echo "[PASS] 6. Spatial operation executed successfully: ST_Point(77.2090, 28.6139) -> ${SPATIAL_OUT}"
else
    echo "[FAIL] 6. Unexpected spatial output: '${SPATIAL_OUT}' (expected '${EXPECTED_POINT}')"
    exit 1
fi

echo "============================================================"
echo "DB-001 VALIDATION SUMMARY: ALL CHECKS PASSED"
echo "============================================================"
exit 0
