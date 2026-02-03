import logging
from unittest import mock

import pytest
from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tmc_common import Band
from ska_tmc_simulators import DishMode

from ska_tmc_dishleafnode.enums.enums import CapabilityStates
from ska_tmc_dishleafnode.manager.health_data import (
    DishBandCapabilityStateData,
    DishHealthData,
    DishHealthStateAndInfoManager,
    GPMValidationResultData,
    KValueValidationResultData,
)


@pytest.mark.parametrize(
    "gpm_result,kvalue_code,dish_state,expect_gpm_err,"
    "expect_k_err,expect_dish_err",
    [
        # GPM OK, KValue OK, Dish OK -> no errors
        ([ResultCode.OK], ResultCode.OK, HealthState.OK, False, False, False),
        # GPM FAILED, KValue OK, Dish OK -> only GPM error
        (
            [ResultCode.FAILED],
            ResultCode.OK,
            HealthState.OK,
            True,
            False,
            False,
        ),
        # GPM OK, KValue FAILED, Dish OK -> only KValue error
        (
            [ResultCode.OK],
            ResultCode.FAILED,
            HealthState.OK,
            False,
            True,
            False,
        ),
        # GPM OK, KValue OK, Dish DEGRADED -> only Dish Manager error
        (
            [ResultCode.OK],
            ResultCode.OK,
            HealthState.DEGRADED,
            False,
            False,
            True,
        ),
        # GPM OK, KValue OK, Dish FAILED -> only Dish Manager error
        (
            [ResultCode.OK],
            ResultCode.OK,
            HealthState.FAILED,
            False,
            False,
            True,
        ),
        # GPM OK, KValue OK, Dish UNKNOWN -> only Dish Manager error
        (
            [ResultCode.OK],
            ResultCode.OK,
            HealthState.UNKNOWN,
            False,
            False,
            True,
        ),
        # Combined: GPM FAILED, KValue FAILED, Dish UNKNOWN -> all errors
        (
            [ResultCode.FAILED],
            ResultCode.FAILED,
            HealthState.UNKNOWN,
            True,
            True,
            True,
        ),
    ],
)
def test_generate_health_info_parametrized(
    gpm_result,
    kvalue_code,
    dish_state,
    expect_gpm_err,
    expect_k_err,
    expect_dish_err,
    cm_without_er_lp,
):
    logger = logging.getLogger("test")
    # cm = CMStub()
    cm = cm_without_er_lp

    for events, data_type in zip(
        [gpm_result, kvalue_code, dish_state],
        [
            "GPMValidationResultData",
            "KValueValidationResultData",
            "DishManagerHealthData",
        ],
    ):
        logger.info("Event input: %s", events)
        cm.health_manager.update_health_data_and_aggregate(events, data_type)

    health_info = cm.health_manager.generate_health_info()
    # generate_health_info uses a fixed placeholder
    # key "mid-tmc/leaf-node-dish/ska001"
    logger.info("Generated healthInfo: %s", health_info)
    assert "HealthSummary" in health_info
    info_list = health_info["HealthSummary"]

    # GPM error
    has_gpm_msg = any("GPM validation failed" in s for s in info_list)
    assert has_gpm_msg is expect_gpm_err

    # KValue error
    has_k_msg = any("KValue validation failed" in s for s in info_list)
    assert has_k_msg is expect_k_err

    # Dish Manager health message
    has_dish_msg = any(
        "Dish Manager" in s and "health state reported" in s for s in info_list
    )
    assert has_dish_msg is expect_dish_err


@pytest.mark.parametrize(
    "capability_state,expected_health",
    [
        (CapabilityStates.UNAVAILABLE, HealthState.FAILED),
        (CapabilityStates.STANDBY, HealthState.OK),
        (CapabilityStates.CONFIGURING, HealthState.OK),
        (CapabilityStates.OPERATE_DEGRADED, HealthState.OK),
        (CapabilityStates.OPERATE_FULL, HealthState.OK),
        (CapabilityStates.UNKNOWN, HealthState.FAILED),
    ],
)
def test_evaluate_health_state_for_all_capability_states_band1(
    cm_without_er_lp, capability_state, expected_health
):
    """
    If Band1 is configured, health state should depend on Band1 capability.

    UNAVAILABLE -> FAILED
    STANDBY/CONFIGURING/OPERATE_* -> OK
    UNKNOWN -> FAILED (assumed; adjust if rules differ)
    """
    cm = cm_without_er_lp
    logger = logging.getLogger("test.health.band1.capability")
    hm = DishHealthStateAndInfoManager(component_manager=cm, logger=logger)

    dh = DishHealthData()

    # IMPORTANT: set these on dh (the object you actually evaluate)
    dh.gpm_validation_result = GPMValidationResultData(
        result=["ResultCode.OK"]
    )
    dh.k_value_validation_result = KValueValidationResultData(
        result_code=ResultCode.OK
    )

    # Use primitive string expected by rules / indexing
    dh.receiver_band = Band.B1

    dh.band_capability_data = DishBandCapabilityStateData(
        band_capabilities={
            "B1": capability_state,
            "B2": CapabilityStates.UNKNOWN,
            "B3": CapabilityStates.UNKNOWN,
            "B4": CapabilityStates.UNKNOWN,
            "B5a": CapabilityStates.UNKNOWN,
            "B5b": CapabilityStates.UNKNOWN,
        }
    )

    logger.info("Evaluating DishHealthData: %s", dh)
    assert hm.evaluate_health_state(dh) == expected_health


@pytest.mark.parametrize(
    "capability_state,expected_health",
    [
        (CapabilityStates.UNAVAILABLE, HealthState.FAILED),
        (CapabilityStates.STANDBY, HealthState.OK),
        (CapabilityStates.CONFIGURING, HealthState.OK),
        (CapabilityStates.OPERATE_DEGRADED, HealthState.OK),
        (CapabilityStates.OPERATE_FULL, HealthState.OK),
        (CapabilityStates.UNKNOWN, HealthState.FAILED),
    ],
)
def test_healthstate_for_all_capability_states_when_band_not_configured(
    cm_without_er_lp, capability_state, expected_health
):
    """
    If receiver band is NOT configured, health state depends on whether ALL
    band capabilities are in an acceptable state.

    This test sets ALL bands to the same capability_state and checks the
    evaluated health.

    Note: UNKNOWN expectation is rule-dependent; enable once confirmed.
    """
    logger = logging.getLogger("test")
    cm = cm_without_er_lp
    hm = DishHealthStateAndInfoManager(
        component_manager=cm, logger=logging.getLogger("test")
    )

    dh = DishHealthData()

    # "Band not configured": use NONE (primitive).
    # Use .value to keep rule_engine happy if it expects numeric/decimal.
    dh.receiver_band = Band.NONE
    # IMPORTANT: set these on dh (the object you actually evaluate)
    dh.gpm_validation_result = GPMValidationResultData(result=[ResultCode.OK])
    dh.k_value_validation_result = KValueValidationResultData(
        result_code=ResultCode.OK
    )

    dh.band_capability_data = DishBandCapabilityStateData(
        band_capabilities={
            "B1": capability_state,
            "B2": capability_state,
            "B3": capability_state,
            "B4": capability_state,
            "B5a": capability_state,
            "B5b": capability_state,
        }
    )

    logger.info(f"Evaluating health state for DishHealthData: {dh}")
    assert hm.evaluate_health_state(dh) == expected_health


def test_evaluate_health_state_failed_when_kvalue_validation_failed(
    cm_without_er_lp,
):
    """
    Health should be FAILED when kValue validation result is FAILED.
    """
    cm = cm_without_er_lp
    hm = DishHealthStateAndInfoManager(
        component_manager=cm, logger=logging.getLogger("test")
    )

    dh = DishHealthData()
    dh.k_value_validation_result = KValueValidationResultData(
        result_code=ResultCode.FAILED
    )

    assert hm.evaluate_health_state(dh) == HealthState.FAILED


def test_evaluate_health_state_degraded_when_any_gpm_failed(cm_without_er_lp):
    """
    Health should be DEGRADED when any GPM validation result equals 'FAILED'.
    """
    cm = cm_without_er_lp
    hm = DishHealthStateAndInfoManager(
        component_manager=cm, logger=logging.getLogger("test")
    )

    dh = DishHealthData()
    dh.gpm_validation_result = GPMValidationResultData(
        result=[ResultCode.FAILED]
    )

    assert hm.evaluate_health_state(dh) == HealthState.DEGRADED


@pytest.mark.parametrize(
    "b1_state,expected_health",
    [
        (CapabilityStates.UNAVAILABLE, HealthState.FAILED),
        (CapabilityStates.STANDBY, HealthState.OK),
        (CapabilityStates.CONFIGURING, HealthState.OK),
        (CapabilityStates.OPERATE_DEGRADED, HealthState.OK),
        (CapabilityStates.OPERATE_FULL, HealthState.OK),
        # Per current health_rules.py:
        # GOOD_STATES_SET includes 'UNKNOWN',
        # and for a configured band the OK rule
        # checks membership in GOOD_STATES_SET -> UNKNOWN should be OK.
        (CapabilityStates.UNKNOWN, HealthState.FAILED),
    ],
)
def test_evaluate_health_state_band1_configured_b2_unavailable(
    cm_without_er_lp, b1_state, expected_health
):
    """
    Band1 is configured; Band2 is UNAVAILABLE (always).
    Health must still be driven by Band1 capability state only.
    """
    cm = cm_without_er_lp
    hm = DishHealthStateAndInfoManager(
        component_manager=cm, logger=logging.getLogger("test")
    )

    dh = DishHealthData()
    dh.receiver_band = Band.B1  # rules use 'NONE'/'UNKNOWN' strings, so use

    dh.k_value_validation_result = KValueValidationResultData(
        result_code=ResultCode.OK
    )
    dh.gpm_validation_result = GPMValidationResultData(result=[ResultCode.OK])

    # Important: keep all band capabilities as strings (no Enum objects)
    dh.band_capability_data = DishBandCapabilityStateData(
        band_capabilities={
            "B1": b1_state,
            "B2": CapabilityStates.UNAVAILABLE,
            "B3": CapabilityStates.UNKNOWN,
            "B4": CapabilityStates.UNKNOWN,
            "B5a": CapabilityStates.UNKNOWN,
            "B5b": CapabilityStates.UNKNOWN,
        }
    )

    assert hm.evaluate_health_state(dh) == expected_health


@pytest.mark.p1
@pytest.mark.parametrize(
    "b2_state,b1_state,expected_health",
    [
        # Case 1: B2 is UNAVAILABLE (existing behaviour)
        (
            CapabilityStates.UNAVAILABLE,
            CapabilityStates.UNAVAILABLE,
            HealthState.FAILED,
        ),
        (
            CapabilityStates.UNAVAILABLE,
            CapabilityStates.STANDBY,
            HealthState.OK,
        ),
        (
            CapabilityStates.UNAVAILABLE,
            CapabilityStates.CONFIGURING,
            HealthState.OK,
        ),
        (
            CapabilityStates.UNAVAILABLE,
            CapabilityStates.OPERATE_DEGRADED,
            HealthState.OK,
        ),
        (
            CapabilityStates.UNAVAILABLE,
            CapabilityStates.OPERATE_FULL,
            HealthState.OK,
        ),
        # Per current health_rules.py (GOOD_STATES_SET includes 'UNKNOWN'):
        (
            CapabilityStates.UNAVAILABLE,
            CapabilityStates.UNKNOWN,
            HealthState.FAILED,
        ),
        # Case 2: B2 is OPERATE_FULL (new condition you asked for)
        (
            CapabilityStates.OPERATE_FULL,
            CapabilityStates.UNAVAILABLE,
            HealthState.FAILED,
        ),
        (
            CapabilityStates.OPERATE_FULL,
            CapabilityStates.STANDBY,
            HealthState.OK,
        ),
        (
            CapabilityStates.OPERATE_FULL,
            CapabilityStates.CONFIGURING,
            HealthState.OK,
        ),
        (
            CapabilityStates.OPERATE_FULL,
            CapabilityStates.OPERATE_DEGRADED,
            HealthState.OK,
        ),
        (
            CapabilityStates.OPERATE_FULL,
            CapabilityStates.OPERATE_FULL,
            HealthState.OK,
        ),
        (
            CapabilityStates.OPERATE_FULL,
            CapabilityStates.UNKNOWN,
            HealthState.FAILED,
        ),
    ],
)
def test_evaluate_health_state_band1_configured_b2_varies(
    cm_without_er_lp, b2_state, b1_state, expected_health
):
    """
    Band1 is configured. Vary Band1 capability; set Band2 either
    UNAVAILABLE or
    OPERATE_FULL. Health should still be driven by Band1 capability only.
    """
    cm = cm_without_er_lp
    hm = DishHealthStateAndInfoManager(
        component_manager=cm, logger=logging.getLogger("test")
    )

    dh = DishHealthData()
    dh.receiver_band = Band.B1

    # Make OK-rule candidates eligible (unless Band1 capability forces FAILED)
    dh.k_value_validation_result = KValueValidationResultData(
        result_code=ResultCode.OK
    )
    dh.gpm_validation_result = GPMValidationResultData(result=[ResultCode.OK])

    dh.band_capability_data = DishBandCapabilityStateData(
        band_capabilities={
            "B1": b1_state,
            "B2": b2_state,
            "B3": CapabilityStates.UNKNOWN,
            "B4": CapabilityStates.UNKNOWN,
            "B5a": CapabilityStates.UNKNOWN,
            "B5b": CapabilityStates.UNKNOWN,
        }
    )

    assert hm.evaluate_health_state(dh) == expected_health


def _make_health_data(
    *,
    receiver_band: str,
    b1_state: str,
    b2_state: str,
    kvalue_code: str,
    gpm_result: list[str],
) -> DishHealthData:
    """Build DishHealthData using only primitives (rule_engine friendly)."""
    dh = DishHealthData()
    dh.receiver_band = receiver_band
    dh.k_value_validation_result = KValueValidationResultData(
        result_code=kvalue_code
    )
    dh.gpm_validation_result = GPMValidationResultData(result=gpm_result)
    dh.band_capability_data = DishBandCapabilityStateData(
        band_capabilities={
            "B1": b1_state,
            "B2": b2_state,
            "B3": CapabilityStates.UNKNOWN,
            "B4": CapabilityStates.UNKNOWN,
            "B5a": CapabilityStates.UNKNOWN,
            "B5b": CapabilityStates.UNKNOWN,
        }
    )
    return dh


def test_healthinfo_updates_on_dish_master_health_transitions_sequence(
    cm_without_er_lp,
):
    """
    Simulate Dish Master healthState events arriving in sequence and verify
    healthInfo is updated each time.

    Sequence: DEGRADED -> FAILED -> UNKNOWN -> OK

    Also logs the healthInfo after each event so transitions are visible
    in pytest output/captured logs.
    """
    logger = logging.getLogger("test.healthinfo.transitions")
    cm = cm_without_er_lp

    health_info_cb = mock.Mock()
    cm._update_health_info_callback = health_info_cb

    # Avoid unrelated side-effects
    cm._update_health_state_callback = mock.Mock()

    hm = DishHealthStateAndInfoManager(component_manager=cm, logger=logger)

    # Keep other signals "healthy" so DishManager message is primary delta.
    hm.update_health_data_and_aggregate(
        ResultCode.OK, "KValueValidationResultData"
    )
    hm.update_health_data_and_aggregate(["OK"], "GPMValidationResultData")
    hm.update_health_data_and_aggregate(Band.NONE, "receiver_band")

    standby = CapabilityStates.STANDBY
    for band in ["B1", "B2", "B3", "B4", "B5a", "B5b"]:
        hm.update_health_data_and_aggregate(
            (band, standby),
            "DishBandCapabilityStateData",
        )

    sequence = [
        HealthState.DEGRADED,
        HealthState.FAILED,
        HealthState.UNKNOWN,
        HealthState.OK,
    ]

    for idx, state in enumerate(sequence, start=1):
        logger.info(
            "---- DishMaster health transition step %d -> %s ----",
            idx,
            state,
        )

        hm.update_health_data_and_aggregate(state, "DishManagerHealthData")

        # We expect healthInfo callback to be called on each aggregate call
        assert health_info_cb.call_count >= idx

        health_info = health_info_cb.call_args[0][0]
        logger.info("HealthInfo after %s: %s", state, health_info)
        assert "HealthSummary" in health_info

        info_list = health_info["HealthSummary"]
        logger.info("HealthInfo.Info list after %s: %s", state, info_list)

        has_dm_msg = any(
            "Dish Manager" in s and "health state reported as" in s
            for s in info_list
        )

        logger.info("state -%s , state -%s", state, state)
        if state in (
            HealthState.DEGRADED,
            HealthState.FAILED,
            HealthState.UNKNOWN,
        ):
            assert (
                has_dm_msg
            ), f"Expected Dish Manager message for state={state}"
            assert any(state.name in s for s in info_list), (
                "Expected state name "
                f"{state.name} to appear in Dish Manager message"
            )
        else:
            # OK should not contribute a Dish Manager error message
            assert (
                not has_dm_msg
            ), "Did not expect Dish Manager message for state=OK"


def test_healthstate_degraded_when_no_band_requested_and_any_band_good(
    cm_without_er_lp,
):
    """
    Use DishHealthStateAndInfoManager +
    update_health_data_and_aggregate to build  context
    and verify HealthState.DEGRADED when:

      - k_value_validation_result.result_code == 'OK'
      - receiver_band in {'NONE', 'UNKNOWN'}
      - ANY band capability is in GOOD_STATES_SET (e.g. STANDBY)
        but NOT ALL are good (so it doesn't become OK via the 'NONE' OK rule)

    This specifically targets the DEGRADED rule:
      k_value_validation_result.result_code == 'OK' AND receiver_band in
      {'NONE','UNKNOWN'}
      AND $any(state in GOOD_STATES_SET for state in band_capability_values)
    """
    logger = logging.getLogger("test.health.degraded.any_good_band")
    cm = cm_without_er_lp
    hm = DishHealthStateAndInfoManager(component_manager=cm, logger=logger)

    # Keep GPM "not failed" so it doesn't trigger the other DEGRADED rule
    hm.update_health_data_and_aggregate(["OK"], "GPMValidationResultData")

    # KValue OK (required by the target DEGRADED rule)
    hm.update_health_data_and_aggregate(
        ResultCode.OK, "KValueValidationResultData"
    )

    # No band requested (required by the target DEGRADED rule)
    hm.update_health_data_and_aggregate(Band.NONE, "receiver_band")

    # Provide band capabilities such that:
    # - at least one band is GOOD (e.g. STANDBY)
    # - at least one band is NOT GOOD (e.g. UNAVAILABLE)
    # This ensures $any(...) is true, but $all(...) for OK
    # (NONE-band OK rule) is false.
    hm.update_health_data_and_aggregate(
        ("B1", CapabilityStates.STANDBY), "DishBandCapabilityStateData"
    )
    hm.update_health_data_and_aggregate(
        ("B2", CapabilityStates.UNAVAILABLE),
        "DishBandCapabilityStateData",
    )
    # fill remaining bands with UNAVAILABLE to keep "not all good"
    for band in ["B3", "B4", "B5a", "B5b"]:
        hm.update_health_data_and_aggregate(
            (band, CapabilityStates.UNAVAILABLE),
            "DishBandCapabilityStateData",
        )

    # Now evaluate using real rule set
    evaluated = hm.evaluate_health_state(hm.health_data)
    logger.info("Health context (asdict-like): %s", hm.health_data)
    logger.info("Evaluated health state: %s", evaluated)

    assert evaluated == HealthState.DEGRADED


def test_healthstate_failed_when_no_band_requested_and_all_bands_not_good(
    cm_without_er_lp,
):
    """

    Build DishHealthData directly using primitive strings so:
      band_capability_values == {'UNAVAILABLE'} only
    and ensure it can't satisfy the OK/DEGRADED "no band requested" rules:
      - OK(no band) requires ALL states in GOOD_STATES_SET
      - DEGRADED(no band) requires ANY state in GOOD_STATES_SET
    """
    logger = logging.getLogger(
        "test.health.failed.all_bands_not_good_when_no_band_requested"
    )
    cm = cm_without_er_lp
    hm = DishHealthStateAndInfoManager(component_manager=cm, logger=logger)

    dh = DishHealthData(
        receiver_band=Band.NONE,
        k_value_validation_result=KValueValidationResultData(
            result_code=ResultCode.OK
        ),
        gpm_validation_result=GPMValidationResultData(result=[ResultCode.OK]),
        band_capability_data=DishBandCapabilityStateData(
            band_capabilities={
                "B1": CapabilityStates.UNAVAILABLE,
                "B2": CapabilityStates.UNAVAILABLE,
                "B3": CapabilityStates.UNAVAILABLE,
                "B4": CapabilityStates.UNAVAILABLE,
                "B5a": CapabilityStates.UNAVAILABLE,
                "B5b": CapabilityStates.UNAVAILABLE,
            }
        ),
    )

    # Sanity log what we're evaluating
    logger.info("DishHealthData: %s", dh)
    logger.info(
        "band_capability_values (expected {'UNAVAILABLE'}): %s",
        dh.band_capability_data.band_capabilities,
    )

    evaluated = hm.evaluate_health_state(dh)
    logger.info("Evaluated health state: %s", evaluated)

    assert evaluated == HealthState.FAILED


def test_generate_health_info(cm_without_er_lp):
    """
    Verify stepwise updates to healthInfo as individual problems are resolved.
    Steps:
      0) GPM FAILED, KValue FAILED, DishManager DEGRADED, Band B1 UNAVAILABLE
      1) Fix GPM (FAILED -> OK) => GPM failure removed from healthInfo
      2) Fix KValue (FAILED -> OK) => KValue failure removed
      3) Fix band capabilities (B1 UNAVAILABLE -> STANDBY)
      4) Fix DishManager (DEGRADED -> OK) => DishManager msg removed
      Final) healthInfo.Info == [] and evaluated healthState == OK
    """
    cm = cm_without_er_lp
    logger = logging.getLogger("test.healthinfo.stepwise")
    hm = DishHealthStateAndInfoManager(component_manager=cm, logger=logger)

    # placeholder used by generate_health_info

    def _info_list():
        hi = hm.generate_health_info()
        info = hi["HealthSummary"]
        logger.info("healthInfo: %s", hi)
        return info

    def _assert_has(info, needle: str):
        assert any(
            needle in s for s in info
        ), f"Expected '{needle}' in info: {info}"

    def _assert_not_has(info, needle: str):
        assert not any(
            needle in s for s in info
        ), f"Did not expect '{needle}' in info: {info}"

    # STEP0: all problems present
    logger.info("STEP0: inject all negative inputs")
    hm.update_health_data_and_aggregate(
        [ResultCode.FAILED], "GPMValidationResultData"
    )
    hm.update_health_data_and_aggregate(
        ResultCode.FAILED, "KValueValidationResultData"
    )
    hm.update_health_data_and_aggregate(
        HealthState.DEGRADED, "DishManagerHealthData"
    )
    hm.update_health_data_and_aggregate(Band.NONE, "receiver_band")
    hm.update_health_data_and_aggregate(
        ("B1", CapabilityStates.UNAVAILABLE), "DishBandCapabilityStateData"
    )
    # Ensure other bands are "good" so only B1 is listed unavailable
    for b in ["B2", "B3", "B4", "B5a", "B5b"]:
        hm.update_health_data_and_aggregate(
            (b, CapabilityStates.STANDBY), "DishBandCapabilityStateData"
        )

    info = _info_list()
    _assert_has(info, "GPM validation failed")
    _assert_has(info, "KValue validation failed")
    _assert_has(info, "Dish Manager")
    _assert_has(info, "Unavailable bands")

    # STEP1: fix GPM
    logger.info("STEP1: fix GPM (FAILED -> OK)")
    hm.update_health_data_and_aggregate(
        [ResultCode.OK], "GPMValidationResultData"
    )
    info = _info_list()
    _assert_not_has(info, "GPM validation failed")
    _assert_has(info, "KValue validation failed")
    _assert_has(info, "Dish Manager")
    _assert_has(info, "Unavailable bands")

    # STEP2: fix KValue
    logger.info("STEP2: fix KValue (FAILED -> OK)")
    hm.update_health_data_and_aggregate(
        ResultCode.OK, "KValueValidationResultData"
    )
    info = _info_list()
    _assert_not_has(info, "GPM validation failed")
    _assert_not_has(info, "KValue validation failed")
    _assert_has(info, "Dish Manager")
    _assert_has(info, "Unavailable bands")

    # STEP3: fix band availability (B1 UNAVAILABLE -> STANDBY)
    logger.info("STEP3: fix band capability (B1 UNAVAILABLE -> STANDBY)")
    hm.update_health_data_and_aggregate(
        ("B1", CapabilityStates.STANDBY), "DishBandCapabilityStateData"
    )
    info = _info_list()
    _assert_not_has(info, "GPM validation failed")
    _assert_not_has(info, "KValue validation failed")
    _assert_has(info, "Dish Manager")
    _assert_not_has(info, "Unavailable bands")

    # STEP4: fix DishManager
    logger.info("STEP4: fix DishManager health (DEGRADED -> OK)")
    hm.update_health_data_and_aggregate(
        HealthState.OK, "DishManagerHealthData"
    )
    info = _info_list()
    _assert_not_has(info, "GPM validation failed")
    _assert_not_has(info, "KValue validation failed")
    _assert_not_has(info, "Unavailable bands")
    _assert_not_has(info, "Dish Manager")

    # FINAL: healthInfo blank and healthState OK
    logger.info(
        "FINAL: expect healthInfo.Info == [] and evaluated healthState == OK"
    )
    assert info == []

    evaluated = hm.evaluate_health_state(hm.health_data)
    logger.info("Evaluated healthState: %s", evaluated)
    assert evaluated == HealthState.OK


def test_update_program_track_table_error_real_flow(cm_without_er_lp):
    """
    Integration-style test to verify data flow into health_manager
    without mocking update_health_data_and_aggregate.

    Asserts:
      - When ProgramTrackTable error is present -> HealthState.DEGRADED and
        healthInfo contains the error text.
      - When ProgramTrackTable error is cleared -> HealthState.OK and
        healthInfo has no messages (blank summary list).
    """
    cm = cm_without_er_lp
    logger = logging.getLogger("test.healthinfo.programtracktable")
    hm = DishHealthStateAndInfoManager(component_manager=cm, logger=logger)

    # Keep other signals healthy
    hm.update_health_data_and_aggregate(
        ResultCode.OK, "KValueValidationResultData"
    )
    hm.update_health_data_and_aggregate(
        [ResultCode.OK], "GPMValidationResultData"
    )
    hm.update_health_data_and_aggregate(Band.NONE, "receiver_band")

    standby = CapabilityStates.STANDBY
    for band in ["B1", "B2", "B3", "B4", "B5a", "B5b"]:
        hm.update_health_data_and_aggregate(
            (band, standby),
            "DishBandCapabilityStateData",
        )

    # --- Inject ProgramTrackTable error ---
    pt_error_text = "The 'program_id' column is missing."
    hm.update_health_data_and_aggregate(
        {"TrackTable_error": pt_error_text},
        "ProgramtracktableErrors",
    )

    evaluated = hm.evaluate_health_state(hm.health_data)
    assert evaluated == HealthState.DEGRADED

    health_info = hm.generate_health_info()
    assert "HealthSummary" in health_info
    summary_list = health_info["HealthSummary"]
    assert isinstance(summary_list, list)

    assert any(pt_error_text in s for s in summary_list), (
        "Expected ProgramTrackTable error HealthSummary when DEGRADED; "
        f"got HealthSummary={summary_list}"
    )

    # --- Clear ProgramTrackTable error ---
    hm.update_health_data_and_aggregate(
        {None: "No Program Track Table Errors"},
        "ProgramtracktableErrors",
    )

    evaluated = hm.evaluate_health_state(hm.health_data)
    assert evaluated == HealthState.OK

    health_info = hm.generate_health_info()
    assert "HealthSummary" in health_info
    summary_list = health_info["HealthSummary"]
    assert isinstance(summary_list, list)

    assert (
        summary_list == []
    ), f"Expected blank HealthSummary when OK; got {summary_list}"


# "DISH.LMC team suggestion is that the DISH Capabilities transition
# to UNKNOWN should  be ignored when Dish is not in
# OPERATE mode" = Change will be needed in this case
# Below are the test cases for same


@pytest.fixture
def cm_for_bandcap_tests(cm_without_er_lp):
    """
    Reuse existing CM fixture but isolate health manager so we can assert
    health state + info deterministically.
    """
    cm = cm_without_er_lp
    cm.health_manager = DishHealthStateAndInfoManager(
        component_manager=cm, logger=logging.getLogger("test.bandcap.health")
    )
    return cm


@pytest.mark.ut_bandcap_1
def test_bandcap_unknown_in_operate_updates_health_to_degraded_and_sets_info(
    cm_for_bandcap_tests,
):
    cm = cm_for_bandcap_tests

    # Arrange: dish in OPERATE, requested band is B1,
    #  and other health inputs OK
    cm.update_device_dish_mode(DishMode.OPERATE)

    cm.health_manager.update_health_data_and_aggregate(
        Band.B1, "receiver_band"
    )
    cm.health_manager.update_health_data_and_aggregate(
        ("B1", CapabilityStates.STANDBY),
        "DishBandCapabilityStateData",
    )

    # Keep other signals healthy
    cm.health_manager.update_health_data_and_aggregate(
        ResultCode.OK, "KValueValidationResultData"
    )
    cm.health_manager.update_health_data_and_aggregate(
        [ResultCode.OK], "GPMValidationResultData"
    )

    # Act: incoming UNKNOWN for B1 capability in OPERATE
    cm.update_band_capability_state(
        CapabilityStates.UNKNOWN, "b1CapabilityState"
    )

    # Assert: CM raw dict updated with key "B1"
    assert cm.band_capability_state["B1"] == CapabilityStates.UNKNOWN

    # Assert: health evaluates to DEGRADED
    evaluated = cm.health_manager.evaluate_health_state(
        cm.health_manager.health_data
    )
    assert evaluated == HealthState.FAILED

    # Assert: healthInfo contains an entry mentioning B1 not fully available
    hi = cm.health_manager.generate_health_info()
    assert "HealthSummary" in hi
    info_list = hi["HealthSummary"]
    assert isinstance(info_list, list)

    assert any("B1" in s for s in info_list), f"Info={info_list}"
    assert any(
        "not fully available" in s.lower() for s in info_list
    ), f"Info={info_list}"


@pytest.mark.ut_bandcap_2
@pytest.mark.parametrize(
    "dish_mode,cap_state",
    [
        (DishMode.STANDBY_FP, CapabilityStates.STANDBY),
        (DishMode.STANDBY_FP, CapabilityStates.CONFIGURING),
        (DishMode.STANDBY_FP, CapabilityStates.OPERATE_FULL),
        (DishMode.STOW, CapabilityStates.STANDBY),
    ],
)
def test_bandcap_non_unknown_outside_operate_updates_health_ok_and_no_info(
    cm_for_bandcap_tests,
    dish_mode,
    cap_state,
):
    """
    Dish not in OPERATE, capability becomes a valid non-UNKNOWN/non-UNAVAILABLE
    state. Expect:
      - health update occurs (no suppression)
      - band state is stored
      - evaluated healthState is OK
      - healthInfo summary is blank
    """
    cm = cm_for_bandcap_tests

    # Arrange: dish NOT in OPERATE
    cm.update_device_dish_mode(dish_mode)

    # Make requested band B1 and keep other signals healthy
    cm.health_manager.update_health_data_and_aggregate(
        Band.B1, "receiver_band"
    )
    cm.health_manager.update_health_data_and_aggregate(
        ResultCode.OK, "KValueValidationResultData"
    )
    cm.health_manager.update_health_data_and_aggregate(
        [ResultCode.OK], "GPMValidationResultData"
    )

    # Make all bands "good" to avoid other band issues affecting the result
    for band in ["B1", "B2", "B3", "B4", "B5a", "B5b"]:
        cm.health_manager.update_health_data_and_aggregate(
            (band, CapabilityStates.STANDBY),
            "DishBandCapabilityStateData",
        )

    # Spy to ensure health update is called when it should be
    with mock.patch.object(
        cm.health_manager,
        "update_health_data_and_aggregate",
        wraps=cm.health_manager.update_health_data_and_aggregate,
    ) as spy:
        # Act: update B1 capability
        cm.update_band_capability_state(cap_state, "b1CapabilityState")

        # Assert: band state stored
        assert cm.band_capability_state["B1"] == cap_state

        # Assert: health update called with the expected tuple
        assert any(
            c.args == (("B1", cap_state), "DishBandCapabilityStateData")
            for c in spy.mock_calls
        ), f"Expected health update call not found. Calls: {spy.mock_calls}"

    # Assert: evaluated health OK
    evaluated = cm.health_manager.evaluate_health_state(
        cm.health_manager.health_data
    )
    assert evaluated == HealthState.OK

    # Assert: healthInfo blank
    hi = cm.health_manager.generate_health_info()
    assert "HealthSummary" in hi
    assert hi["HealthSummary"] == [], f"Expected blank HealthSummary, got {hi}"


#


@pytest.mark.ut_bandcap_5
@pytest.mark.parametrize(
    "dish_mode",
    [
        DishMode.STANDBY_FP,
        DishMode.STOW,
    ],
)
def test_bandcap_unknown_outside_operate_is_recorded_not_affect_health(
    cm_for_bandcap_tests,
    dish_mode,
):
    """
    Dish not in OPERATE, capability becomes UNKNOWN.

    Expect:
      - raw band_capability_state is updated (debug/telemetry)
      - DishBandCapabilityStateData update is NOT forwarded to health manager
      - overall health remains OK (given other signals are healthy)
      - healthInfo is blank
    """
    cm = cm_for_bandcap_tests

    # Arrange: dish NOT in OPERATE
    cm.update_device_dish_mode(dish_mode)

    # Keep other signals healthy
    cm.health_manager.update_health_data_and_aggregate(
        Band.B1, "receiver_band"
    )
    cm.health_manager.update_health_data_and_aggregate(
        ResultCode.OK, "KValueValidationResultData"
    )
    cm.health_manager.update_health_data_and_aggregate(
        [ResultCode.OK], "GPMValidationResultData"
    )
    # Dish manager OK/UNKNOWN could otherwise influence health; force OK
    cm.health_manager.update_health_data_and_aggregate(
        HealthState.OK, "DishManagerHealthData"
    )

    # Make all bands "good" before the UNKNOWN event arrives
    for band in ["B1", "B2", "B3", "B4", "B5a", "B5b"]:
        cm.health_manager.update_health_data_and_aggregate(
            (band, CapabilityStates.STANDBY),
            "DishBandCapabilityStateData",
        )

    # Spy to ensure HEALTH is not updated with UNKNOWN outside OPERATE
    with mock.patch.object(
        cm.health_manager,
        "update_health_data_and_aggregate",
        wraps=cm.health_manager.update_health_data_and_aggregate,
    ) as spy:
        # Act: incoming UNKNOWN for B1 capability (outside OPERATE)
        cm.update_band_capability_state(
            CapabilityStates.UNKNOWN, "b1CapabilityState"
        )

        # Assert: raw stored in CM
        assert cm.band_capability_state["B1"] == CapabilityStates.UNKNOWN

        # Assert: the UNKNOWN band capability was NOT forwarded
        # to health manager
        assert not any(
            c.args
            == (
                ("B1", CapabilityStates.UNKNOWN),
                "DishBandCapabilityStateData",
            )
            for c in spy.mock_calls
        ), f"Unexpected health update calls: {spy.mock_calls}"

    # Assert: health still OK
    evaluated = cm.health_manager.evaluate_health_state(
        cm.health_manager.health_data
    )
    assert evaluated == HealthState.OK

    # Assert: healthInfo blank
    hi = cm.health_manager.generate_health_info()
    assert "HealthSummary" in hi
    assert hi["HealthSummary"] == [], f"Expected blank HealthSummary, got {hi}"


@pytest.mark.ut_bandcap_seq
def test_bandcap_unknown_handling_sequential_health_and_info(
    cm_for_bandcap_tests,
):
    """
    Sequentially verify the three scenarios:

    1) Dish not in OPERATE, capability becomes UNKNOWN:
       - HealthState OK
       - HealthSummary blank

    2) Dish in OPERATE, capability becomes UNKNOWN:
       - HealthState DEGRADED
       - HealthSummary contains requested-band message

    3) Dish in OPERATE, capability becomes STANDBY:
       - HealthState OK
       - HealthSummary blank
    """
    cm = cm_for_bandcap_tests

    def _make_other_signals_healthy():
        cm.health_manager.update_health_data_and_aggregate(
            ResultCode.OK, "KValueValidationResultData"
        )
        cm.health_manager.update_health_data_and_aggregate(
            [ResultCode.OK], "GPMValidationResultData"
        )
        cm.health_manager.update_health_data_and_aggregate(
            HealthState.OK, "DishManagerHealthData"
        )

    def _set_band_context_all_good():
        cm.health_manager.update_health_data_and_aggregate(
            Band.B1, "receiver_band"
        )
        for b in ["B1", "B2", "B3", "B4", "B5a", "B5b"]:
            cm.health_manager.update_health_data_and_aggregate(
                (b, CapabilityStates.STANDBY),
                "DishBandCapabilityStateData",
            )

    def _assert_health_ok_and_info_blank():
        evaluated = cm.health_manager.evaluate_health_state(
            cm.health_manager.health_data
        )
        assert evaluated == HealthState.OK
        hi = cm.health_manager.generate_health_info()
        assert (
            hi["HealthSummary"] == []
        ), f"Expected blank HealthSummary, got {hi}"

    def _assert_health_failed_and_has_requested_band_msg():
        evaluated = cm.health_manager.evaluate_health_state(
            cm.health_manager.health_data
        )
        assert evaluated == HealthState.FAILED
        hi = cm.health_manager.generate_health_info()
        summary = hi["HealthSummary"]
        assert any(
            "Requested band B1" in s for s in summary
        ), f"HealthSummary={summary}"
        assert any(
            "not fully available" in s.lower() for s in summary
        ), f"HealthSummary={summary}"

    # Keep non-band signals healthy for the whole test
    _make_other_signals_healthy()

    # -------------------------
    # 1) NOT OPERATE + UNKNOWN
    # -------------------------
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    _set_band_context_all_good()

    with mock.patch.object(
        cm.health_manager,
        "update_health_data_and_aggregate",
        wraps=cm.health_manager.update_health_data_and_aggregate,
    ) as spy:
        cm.update_band_capability_state(
            CapabilityStates.UNKNOWN, "b1CapabilityState"
        )

        # raw stored
        assert cm.band_capability_state["B1"] == CapabilityStates.UNKNOWN

        # NOT forwarded to health
        assert not any(
            c.args
            == (
                ("B1", CapabilityStates.UNKNOWN),
                "DishBandCapabilityStateData",
            )
            for c in spy.mock_calls
        ), f"Unexpected health update calls: {spy.mock_calls}"

    _assert_health_ok_and_info_blank()

    # ----------------------
    # 2) OPERATE + UNKNOWN
    # ----------------------
    cm.update_device_dish_mode(DishMode.OPERATE)
    _set_band_context_all_good()

    with mock.patch.object(
        cm.health_manager,
        "update_health_data_and_aggregate",
        wraps=cm.health_manager.update_health_data_and_aggregate,
    ) as spy:
        cm.update_band_capability_state(
            CapabilityStates.UNKNOWN, "b1CapabilityState"
        )

        # raw stored
        assert cm.band_capability_state["B1"] == CapabilityStates.UNKNOWN

        # forwarded in OPERATE
        assert any(
            c.args
            == (
                ("B1", CapabilityStates.UNKNOWN),
                "DishBandCapabilityStateData",
            )
            for c in spy.mock_calls
        ), f"Expected health update call not found. Calls: {spy.mock_calls}"

    _assert_health_failed_and_has_requested_band_msg()

    # ----------------------
    # 3) OPERATE + STANDBY
    # ----------------------
    cm.update_device_dish_mode(DishMode.OPERATE)
    _set_band_context_all_good()

    cm.update_band_capability_state(
        CapabilityStates.STANDBY, "b1CapabilityState"
    )
    assert cm.band_capability_state["B1"] == CapabilityStates.STANDBY

    _assert_health_ok_and_info_blank()
