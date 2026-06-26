#!/usr/bin/env bash
# Level-2 SKB-1306 probe: in-process sim, no --true-context.
# Usage: ./tests/integration/run_level2_probe.sh 0.45.0
#        ./tests/integration/run_level2_probe.sh 0.45.1
#
# Requires a healthy sim: startup must read True within ~30s (0.45.1) before
# subscribe phases are meaningful. All-False timelines indicate env/sim issue.

set -euo pipefail
TAG="${1:?pass tag e.g. 0.45.0 or 0.45.1}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

git fetch github --tags 2>/dev/null || true

# Keep probe harness + weather skip conftest on current branch; only swap dish impl.
PROBE_REF="${PROBE_REF:-github/exp/signal-init-fix}"
git checkout "$PROBE_REF" -- \
  tests/integration/conftest.py \
  tests/integration/skb_1306_fixtures.py \
  tests/integration/skb_1306_test_devices.py \
  tests/integration/test_is_subsystem_available_diagnostic_skb_1306.py \
  tests/integration/test_is_subsystem_available_skb_1306.py \
  tests/integration/test_skb_1306_sim_health.py \
  tests/integration/run_level2_probe.sh \
  tests/unit/skb_1306_availability_timeline.py 2>/dev/null || true

git checkout "$TAG" -- src/ska_tmc_dishleafnode/dish_leaf_node.py

DLN="src/ska_tmc_dishleafnode/dish_leaf_node.py"
if [[ "$TAG" == "0.45.1" ]] && ! grep -q 'read_isSubsystemAvailable' "$DLN"; then
  echo "ERROR: $DLN is not 0.45.1 (missing read_isSubsystemAvailable). Tag checkout failed?"
  exit 1
fi
if [[ "$TAG" == "0.45.0" ]] && ! grep -q 'attribute_from_signal' "$DLN"; then
  echo "ERROR: $DLN is not 0.45.0 (missing attribute_from_signal). Tag checkout failed?"
  exit 1
fi

# Do NOT unset TANGO_HOST — /etc/tangorc may have invalid "TANGO_HOST=:10000".
# MultiDeviceTestContext overrides this for the sim process.
export TANGO_HOST=127.0.0.1:10000

LOG="probe-level2-${TAG}.log"
echo "=== dish_leaf_node from tag ${TAG}, TANGO_HOST=${TANGO_HOST} ===" | tee "$LOG"

echo "=== sim connectivity ===" | tee -a "$LOG"
if ! poetry run pytest tests/integration/test_skb_1306_sim_health.py::test_sim_devices_reachable \
  -v -s -o addopts="" 2>&1 | tee -a "$LOG"; then
  echo ""
  echo "Sim connectivity failed — helper dish / test DB not healthy. See $LOG"
  exit 1
fi

if [[ "$TAG" == "0.45.1" ]]; then
  echo "=== 0.45.1 liveliness gate (must read True) ===" | tee -a "$LOG"
  if ! poetry run pytest \
    tests/integration/test_skb_1306_sim_health.py::test_sim_liveliness_promotes_availability \
    -v -s -o addopts="" 2>&1 | tee -a "$LOG"; then
    echo ""
    echo "0.45.1 never reached isSubsystemAvailable=True — sim/liveliness broken. See $LOG"
    exit 1
  fi
fi

poetry run pytest tests/integration/test_is_subsystem_available_diagnostic_skb_1306.py \
  -v -s -o addopts="" 2>&1 | tee -a "$LOG"

echo ""
echo "=== timeline (${TAG}) ==="
grep -A25 'isSubsystemAvailable timeline' "$LOG" || true

if grep -q 'never read True within 60s' "$LOG"; then
  echo ""
  echo "WARNING: sim never reached True — subscribe False is not SKB-1306 evidence."
  echo "  - Confirm TANGO_HOST=127.0.0.1:10000 (not unset / not :10000 from tangorc)"
  echo "  - For 0.45.1 baseline, startup should be True within ~30s when sim is healthy"
  echo "  - Run: poetry run pytest tests/integration/test_is_subsystem_available_skb_1306.py::test_read_true_after_startup -v -s -o addopts=\"\""
  exit 1
fi
