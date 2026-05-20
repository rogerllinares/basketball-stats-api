#!/usr/bin/env bash
# Smoke test for Phase 2 endpoints — READ-01 .. READ-08.
#
# Pre-conditions: API is running and the minimal seed is loaded.
# - Local: `uv run uvicorn basketball_stats.main:app` + `uv run python -m basketball_stats.seed.minimal`.
# - Prod: BASE=https://<host> bash scripts/smoke-test-p2.sh  (seed must be loaded against the prod DB beforehand).
#
# Exit 0 = all 8 endpoints respond with the expected payload shape.

set -euo pipefail

BASE=${BASE:-http://localhost:8000}
echo "Smoke testing Phase 2 endpoints against ${BASE}"

probe() {
  local label="$1"
  local path="$2"
  local jq_check="$3"
  local body
  body=$(curl -fsS "${BASE}${path}")
  local result
  result=$(echo "${body}" | jq -r "${jq_check}")
  if [[ -z "${result}" || "${result}" == "null" ]]; then
    echo "FAIL ${label} (${path}) — jq '${jq_check}' returned: ${result}"
    echo "Body: ${body}" | head -c 400
    exit 1
  fi
  echo "OK   ${label} → ${result}"
}

probe "READ-01 list competitions"           "/api/v1/competitions"                              "length"
probe "READ-02 standings RANK"              "/api/v1/competitions/1/standings"                  ".[0].position"
probe "READ-03 leaderboards top val"        "/api/v1/competitions/1/leaderboards?stat=val&limit=3" "length"
probe "READ-04 team detail"                 "/api/v1/teams/1"                                   ".id"
probe "READ-05 player by slug"              "/api/v1/players/99001-5-marc-soler"                ".license_id"
probe "READ-06 player stats"                "/api/v1/players/by-id/1/stats?season_id=1"         ".games_played"
probe "READ-07 game detail with box-score"  "/api/v1/games/1"                                   ".box_scores | length"
probe "READ-08 games by matchday"           "/api/v1/competitions/1/games?matchday_no=1"        "length"

echo "All 8 Phase 2 endpoints OK"
