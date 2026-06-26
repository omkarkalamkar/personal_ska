#!/usr/bin/env bash
# Level-2 SKB-1306 probe: in-process sim, no --true-context.
# Usage: ./tests/integration/run_level2_probe.sh 0.45.0
#        ./tests/integration/run_level2_probe.sh 0.45.1

set -euo pipefail
TAG="${1:?pass tag e.g. 0.45.0 or 0.45.1}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

git fetch github --tags 2>/dev/null || true
git checkout "$TAG" -- src/ska_tmc_dishleafnode/dish_leaf_node.py

# Let MultiDeviceTestContext set TANGO_HOST for the sim (avoid stale host).
unset TANGO_HOST

LOG="probe-level2-${TAG}.log"
poetry run pytest tests/integration/test_is_subsystem_available_diagnostic_skb_1306.py \
  -v -s -o addopts="" 2>&1 | tee "$LOG"

echo ""
echo "=== timeline (${TAG}) ==="
grep -A20 'isSubsystemAvailable timeline' "$LOG" || true
