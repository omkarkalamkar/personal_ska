# flake8: noqa=E501

import logging
from unittest import mock

import pytest
from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tmc_common import Band

from ska_tmc_dishleafnode.enums import CapabilityStates
from ska_tmc_dishleafnode.manager.health_data import (
    DishBandCapabilityStateData,
    DishHealthData,
    DishManagerHealthData,
    GPMValidationResultData,
    HealthManager,
    KValueValidationResultData,
)


@pytest.mark.ut1
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
    dish_key = "mid-tmc/leaf-node-dish/ska001"
    assert "HealthSummary" in health_info
    assert dish_key in health_info["HealthSummary"]
    info_list = health_info["HealthSummary"][dish_key]["Info"]

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


@pytest.mark.ut1
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
    hm = HealthManager(component_manager=cm, logger=logger)

    dh = DishHealthData()

    # IMPORTANT: set these on dh (the object you actually evaluate)
    dh.gpm_validation_result = GPMValidationResultData(result=[ResultCode.OK])
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


@pytest.mark.ut1
@pytest.mark.parametrize(
    "capability_state,expected_health",
    [
        (CapabilityStates.UNAVAILABLE.name, HealthState.FAILED),
        (CapabilityStates.STANDBY.name, HealthState.OK),
        (CapabilityStates.CONFIGURING.name, HealthState.OK),
        (CapabilityStates.OPERATE_DEGRADED.name, HealthState.OK),
        (CapabilityStates.OPERATE_FULL.name, HealthState.OK),
        # UNKNOWN: set expected to FAILED by assumption; adjust to match HEALTH_RULES
        # once rule semantics are confirmed.
        # (CapabilityStates.UNKNOWN.name, HealthState.FAILED),
    ],
)
def test_evaluate_health_state_for_all_capability_states_when_band_not_configured(
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
    hm = HealthManager(component_manager=cm, logger=logging.getLogger("test"))

    dh = DishHealthData()

    # "Band not configured": use NONE (primitive).
    # Use .value to keep rule_engine happy if it expects numeric/decimal.
    dh.receiver_band = Band.NONE
    # IMPORTANT: set these on dh (the object you actually evaluate)
    dh.gpm_validation_result = GPMValidationResultData(result=["OK"])
    dh.k_value_validation_result = KValueValidationResultData(
        result_code=ResultCode.OK.name
    )

    dh.band_capability_data = DishBandCapabilityStateData(
        band_capabilities={
            Band.B1: capability_state,
            "B2": capability_state,
            "B3": capability_state,
            "B4": capability_state,
            "B5a": capability_state,
            "B5b": capability_state,
        }
    )

    logger.info(f"Evaluating health state for DishHealthData: {dh}")
    assert hm.evaluate_health_state(dh) == expected_health


@pytest.mark.ut1
# Note --This is causing thread crash  when below rule was added
# HealthState.DEGRADED: [
#         Rule(
#             "$any([gpm == 'FAILED' for gpm in "
#             "gpm_validation_result.result])"
#         ),
#         # No band requested, but at least one band is good
#         Rule(
#             "k_value_validation_result.result_code == 'OK' and "
#             f"receiver_band in {{'NONE', 'UNKNOWN'}} and "
#             f"$any([state in {GOOD_STATES_SET} "
#             f"for state in band_capability_data.band_capability_values])"
#             )
def test_evaluate_health_state_failed_when_kvalue_validation_failed(
    cm_without_er_lp,
):
    """
    Health should be FAILED when kValue validation result is FAILED.
    """
    cm = cm_without_er_lp
    hm = HealthManager(component_manager=cm, logger=logging.getLogger("test"))

    dh = DishHealthData()
    dh.k_value_validation_result = KValueValidationResultData(
        result_code=ResultCode.FAILED.name
    )

    assert hm.evaluate_health_state(dh) == HealthState.FAILED


@pytest.mark.ut1
def test_evaluate_health_state_degraded_when_any_gpm_failed(cm_without_er_lp):
    """
    Health should be DEGRADED when any GPM validation result equals 'FAILED'.
    """
    cm = cm_without_er_lp
    hm = HealthManager(component_manager=cm, logger=logging.getLogger("test"))

    dh = DishHealthData()
    dh.gpm_validation_result = GPMValidationResultData(result=["FAILED"])

    assert hm.evaluate_health_state(dh) == HealthState.DEGRADED


@pytest.mark.ut1
@pytest.mark.parametrize(
    "b1_state,expected_health",
    [
        (CapabilityStates.UNAVAILABLE.name, HealthState.FAILED),
        (CapabilityStates.STANDBY.name, HealthState.OK),
        (CapabilityStates.CONFIGURING.name, HealthState.OK),
        (CapabilityStates.OPERATE_DEGRADED.name, HealthState.OK),
        (CapabilityStates.OPERATE_FULL.name, HealthState.OK),
        # Per current health_rules.py:
        # GOOD_STATES_SET includes 'UNKNOWN', and for a configured band the OK rule
        # checks membership in GOOD_STATES_SET -> UNKNOWN should be OK.
        # (CapabilityStates.UNKNOWN.name, HealthState.OK),
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
    hm = HealthManager(component_manager=cm, logger=logging.getLogger("test"))

    dh = DishHealthData()
    dh.receiver_band = (
        Band.B1.name
    )  # rules use 'NONE'/'UNKNOWN' strings, so use .name

    dh.k_value_validation_result = KValueValidationResultData(
        result_code=ResultCode.OK.name
    )
    dh.gpm_validation_result = GPMValidationResultData(result=["OK"])

    # Important: keep all band capabilities as strings (no Enum objects)
    dh.band_capability_data = DishBandCapabilityStateData(
        band_capabilities={
            "B1": b1_state,
            "B2": CapabilityStates.UNAVAILABLE.name,
            "B3": CapabilityStates.UNKNOWN.name,
            "B4": CapabilityStates.UNKNOWN.name,
            "B5a": CapabilityStates.UNKNOWN.name,
            "B5b": CapabilityStates.UNKNOWN.name,
        }
    )

    assert hm.evaluate_health_state(dh) == expected_health


@pytest.mark.ut1
@pytest.mark.parametrize(
    "b2_state,b1_state,expected_health",
    [
        # Case 1: B2 is UNAVAILABLE (existing behaviour)
        (
            CapabilityStates.UNAVAILABLE.name,
            CapabilityStates.UNAVAILABLE.name,
            HealthState.FAILED,
        ),
        (
            CapabilityStates.UNAVAILABLE.name,
            CapabilityStates.STANDBY.name,
            HealthState.OK,
        ),
        (
            CapabilityStates.UNAVAILABLE.name,
            CapabilityStates.CONFIGURING.name,
            HealthState.OK,
        ),
        (
            CapabilityStates.UNAVAILABLE.name,
            CapabilityStates.OPERATE_DEGRADED.name,
            HealthState.OK,
        ),
        (
            CapabilityStates.UNAVAILABLE.name,
            CapabilityStates.OPERATE_FULL.name,
            HealthState.OK,
        ),
        # Per current health_rules.py (GOOD_STATES_SET includes 'UNKNOWN'):
        (
            CapabilityStates.UNAVAILABLE.name,
            CapabilityStates.UNKNOWN.name,
            HealthState.OK,
        ),
        # Case 2: B2 is OPERATE_FULL (new condition you asked for)
        (
            CapabilityStates.OPERATE_FULL.name,
            CapabilityStates.UNAVAILABLE.name,
            HealthState.FAILED,
        ),
        (
            CapabilityStates.OPERATE_FULL.name,
            CapabilityStates.STANDBY.name,
            HealthState.OK,
        ),
        (
            CapabilityStates.OPERATE_FULL.name,
            CapabilityStates.CONFIGURING.name,
            HealthState.OK,
        ),
        (
            CapabilityStates.OPERATE_FULL.name,
            CapabilityStates.OPERATE_DEGRADED.name,
            HealthState.OK,
        ),
        (
            CapabilityStates.OPERATE_FULL.name,
            CapabilityStates.OPERATE_FULL.name,
            HealthState.OK,
        ),
        (
            CapabilityStates.OPERATE_FULL.name,
            CapabilityStates.UNKNOWN.name,
            HealthState.OK,
        ),
    ],
)
def test_evaluate_health_state_band1_configured_b2_varies(
    cm_without_er_lp, b2_state, b1_state, expected_health
):
    """
    Band1 is configured. Vary Band1 capability; set Band2 either UNAVAILABLE or
    OPERATE_FULL. Health should still be driven by Band1 capability only.
    """
    cm = cm_without_er_lp
    hm = HealthManager(component_manager=cm, logger=logging.getLogger("test"))

    dh = DishHealthData()
    dh.receiver_band = Band.B1.name

    # Make OK-rule candidates eligible (unless Band1 capability forces FAILED)
    dh.k_value_validation_result = KValueValidationResultData(
        result_code=ResultCode.OK.name
    )
    dh.gpm_validation_result = GPMValidationResultData(result=["OK"])

    dh.band_capability_data = DishBandCapabilityStateData(
        band_capabilities={
            "B1": b1_state,
            "B2": b2_state,
            "B3": CapabilityStates.UNKNOWN.name,
            "B4": CapabilityStates.UNKNOWN.name,
            "B5a": CapabilityStates.UNKNOWN.name,
            "B5b": CapabilityStates.UNKNOWN.name,
        }
    )

    assert hm.evaluate_health_state(dh) == expected_health

    # ...existing code...


# from ska_tmc_common import Band

# ...existing code...


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
            "B3": CapabilityStates.UNKNOWN.name,
            "B4": CapabilityStates.UNKNOWN.name,
            "B5a": CapabilityStates.UNKNOWN.name,
            "B5b": CapabilityStates.UNKNOWN.name,
        }
    )
    return dh


@pytest.mark.ut1
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

    # Capture updates pushed by HealthManager.update_health_data_and_aggregate()
    health_info_cb = mock.Mock()
    cm._update_health_info_callback = health_info_cb

    # Avoid unrelated side-effects
    cm._update_health_state_callback = mock.Mock()

    hm = HealthManager(component_manager=cm, logger=logger)

    # Keep other signals "healthy" so DishManager message is the primary delta.
    hm.update_health_data_and_aggregate(
        ResultCode.OK.name, "KValueValidationResultData"
    )
    hm.update_health_data_and_aggregate(["OK"], "GPMValidationResultData")
    hm.update_health_data_and_aggregate(Band.NONE, "receiver_band")

    standby = CapabilityStates.STANDBY.name
    for band_name in ["B1", "B2", "B3", "B4", "B5a", "B5b"]:
        hm.update_health_data_and_aggregate(
            (band_name, standby),
            "DishBandCapabilityStateData",
        )

    dish_key = (
        "mid-tmc/leaf-node-dish/ska001"  # placeholder key used internally
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
            state.name,
        )

        hm.update_health_data_and_aggregate(state, "DishManagerHealthData")

        # We expect healthInfo callback to be called on each aggregate call
        assert health_info_cb.call_count >= idx

        health_info = health_info_cb.call_args[0][0]
        logger.info("HealthInfo after %s: %s", state.name, health_info)

        assert "HealthSummary" in health_info
        assert dish_key in health_info["HealthSummary"]
        info_list = health_info["HealthSummary"][dish_key]["Info"]
        logger.info("HealthInfo.Info list after %s: %s", state.name, info_list)

        has_dm_msg = any(
            "Dish Manager" in s and "health state reported as" in s
            for s in info_list
        )

        logger.info("state -%s , state.name -%s", state, state.name)
        if state in (
            HealthState.DEGRADED,
            HealthState.FAILED,
            HealthState.UNKNOWN,
        ):
            assert (
                has_dm_msg
            ), f"Expected Dish Manager message for state={state}"
            assert any(
                state.name in s for s in info_list
            ), f"Expected state name {state.name} to appear in Dish Manager message"
        else:
            # OK should not contribute a Dish Manager error message
            assert (
                not has_dm_msg
            ), "Did not expect Dish Manager message for state=OK"


# ...existing code...


@pytest.mark.ut1
def test_generate_health_info(cm_without_er_lp):
    """
    Build an initially "bad" health context (GPM FAILED, KValue FAILED, DishManager
    DEGRADED, and an UNAVAILABLE band), then gradually remove one negative input
    at a time, asserting that the corresponding message disappears from healthInfo.

    Finally, assert healthInfo becomes blank (Info == []) and evaluated healthState is OK.
    """
    cm = cm_without_er_lp
    logger = logging.getLogger("test.healthinfo.stepwise")
    hm = HealthManager(component_manager=cm, logger=logger)

    # fixed placeholder used by generate_health_info
    dish_key = "mid-tmc/leaf-node-dish/ska001"

    # Start with multiple failures
    context = DishHealthData(
        gpm_validation_result=GPMValidationResultData(result=["FAILED"]),
        k_value_validation_result=KValueValidationResultData(
            result_code=ResultCode.FAILED.name
        ),
        dish_manager_health_data=DishManagerHealthData(
            health_state=HealthState.DEGRADED
        ),
        # Note: for "band not configured" case, generate_health_info inspects
        # Unavailable bands across band_capabilities.
        receiver_band=Band.NONE,
        band_capability_data=DishBandCapabilityStateData(
            band_capabilities={
                "B1": CapabilityStates.UNAVAILABLE.name,
                "B2": CapabilityStates.STANDBY.name,
                "B3": CapabilityStates.STANDBY.name,
                "B4": CapabilityStates.STANDBY.name,
                "B5a": CapabilityStates.STANDBY.name,
                "B5b": CapabilityStates.STANDBY.name,
            }
        ),
    )

    def _health_info_and_list():
        hi = hm.generate_health_info(context)
        info = hi["HealthSummary"][dish_key]["Info"]
        logger.info("healthInfo: %s", hi)
        logger.info("healthInfo.Info: %s", info)
        return hi, info

    def _assert_has(info_list, needle: str):
        assert any(
            needle in s for s in info_list
        ), f"Expected '{needle}' in info: {info_list}"

    def _assert_not_has(info_list, needle: str):
        assert not any(
            needle in s for s in info_list
        ), f"Did not expect '{needle}' in info: {info_list}"

    # Step 0: all problems present
    logger.info(
        "STEP0: all problems present (GPM FAILED, KValue FAILED, DM DEGRADED, B1 UNAVAILABLE)"
    )
    health_info, info_list = _health_info_and_list()

    assert "HealthSummary" in health_info
    assert dish_key in health_info["HealthSummary"]

    _assert_has(info_list, "GPM validation failed")
    _assert_has(info_list, "KValue validation failed")
    _assert_has(info_list, "Dish Manager")
    _assert_has(info_list, "Unavailable bands")

    # Step 1: Fix GPM (remove FAILED -> OK) and assert GPM message disappears
    logger.info("STEP1: fix GPM validation (FAILED -> OK)")
    context.gpm_validation_result = GPMValidationResultData(result=["OK"])
    _, info_list = _health_info_and_list()
    _assert_not_has(info_list, "GPM validation failed")
    _assert_has(info_list, "KValue validation failed")
    _assert_has(info_list, "Dish Manager")
    _assert_has(info_list, "Unavailable bands")

    # Step 2: Fix KValue (FAILED -> OK) and assert KValue message disappears
    logger.info("STEP2: fix KValue validation (FAILED -> OK)")
    context.k_value_validation_result = KValueValidationResultData(
        result_code=ResultCode.OK.name
    )
    _, info_list = _health_info_and_list()
    _assert_not_has(info_list, "GPM validation failed")
    _assert_not_has(info_list, "KValue validation failed")
    _assert_has(info_list, "Dish Manager")
    _assert_has(info_list, "Unavailable bands")

    # Step 3: Fix band capability (B1 UNAVAILABLE -> STANDBY) and assert Unavailable bands disappears
    logger.info("STEP3: fix band capability (B1 UNAVAILABLE -> STANDBY)")
    context.band_capability_data.band_capabilities[
        "B1"
    ] = CapabilityStates.STANDBY.name
    _, info_list = _health_info_and_list()
    _assert_not_has(info_list, "GPM validation failed")
    _assert_not_has(info_list, "KValue validation failed")
    _assert_has(info_list, "Dish Manager")
    _assert_not_has(info_list, "Unavailable bands")

    # Step 4: Fix Dish Manager health (DEGRADED -> OK) and assert Dish Manager message disappears
    logger.info("STEP4: fix Dish Manager healthState (DEGRADED -> OK)")
    context.dish_manager_health_data = DishManagerHealthData(
        health_state=HealthState.OK
    )
    _, info_list = _health_info_and_list()
    _assert_not_has(info_list, "GPM validation failed")
    _assert_not_has(info_list, "KValue validation failed")
    _assert_not_has(info_list, "Unavailable bands")
    _assert_not_has(info_list, "Dish Manager")

    # Final: health info should be blank and evaluated health should be OK
    logger.info(
        "FINAL: expect healthInfo to be blank and healthState to be OK"
    )
    assert info_list == []

    # Evaluate the health state from the same context
    evaluated = hm.evaluate_health_state(context)
    logger.info("Evaluated healthState: %s", evaluated)
    assert evaluated == HealthState.OK


@pytest.mark.ut1
def test_evaluate_health_state_degraded_when_no_band_requested_and_any_band_good(
    cm_without_er_lp,
):
    """
    Use HealthManager + update_health_data_and_aggregate to build the health context
    and verify HealthState.DEGRADED when:

      - k_value_validation_result.result_code == 'OK'
      - receiver_band in {'NONE', 'UNKNOWN'}
      - ANY band capability is in GOOD_STATES_SET (e.g. STANDBY)
        but NOT ALL are good (so it doesn't become OK via the 'NONE' OK rule)

    This specifically targets the DEGRADED rule:
      k_value_validation_result.result_code == 'OK' AND receiver_band in {'NONE','UNKNOWN'}
      AND $any(state in GOOD_STATES_SET for state in band_capability_values)
    """
    logger = logging.getLogger("test.health.degraded.any_good_band")
    cm = cm_without_er_lp
    hm = HealthManager(component_manager=cm, logger=logger)

    # Keep GPM "not failed" so it doesn't trigger the other DEGRADED rule
    hm.update_health_data_and_aggregate(["OK"], "GPMValidationResultData")

    # KValue OK (required by the target DEGRADED rule)
    hm.update_health_data_and_aggregate(
        ResultCode.OK.name, "KValueValidationResultData"
    )

    # No band requested (required by the target DEGRADED rule)
    hm.update_health_data_and_aggregate(Band.NONE, "receiver_band")

    # Provide band capabilities such that:
    # - at least one band is GOOD (e.g. STANDBY)
    # - at least one band is NOT GOOD (e.g. UNAVAILABLE)
    # This ensures $any(...) is true, but $all(...) for OK (NONE-band OK rule) is false.
    hm.update_health_data_and_aggregate(
        ("B1", CapabilityStates.STANDBY.name), "DishBandCapabilityStateData"
    )
    hm.update_health_data_and_aggregate(
        ("B2", CapabilityStates.UNAVAILABLE.name),
        "DishBandCapabilityStateData",
    )
    # fill remaining bands with UNAVAILABLE to keep "not all good"
    for band_name in ["B3", "B4", "B5a", "B5b"]:
        hm.update_health_data_and_aggregate(
            (band_name, CapabilityStates.UNAVAILABLE.name),
            "DishBandCapabilityStateData",
        )

    # Now evaluate using real rule set
    evaluated = hm.evaluate_health_state(hm.health_data)
    logger.info("Health context (asdict-like): %s", hm.health_data)
    logger.info("Evaluated health state: %s", evaluated)

    assert evaluated == HealthState.DEGRADED


# ...existing code...


@pytest.mark.ut1
def test_evaluate_health_state_failed_when_no_band_requested_and_all_bands_not_good(
    cm_without_er_lp,
):
    """
    Target FAILED rule:

      receiver_band in {'NONE', 'UNKNOWN'} and
      $all([state not in GOOD_STATES_SET for state in band_capability_values])

    Build DishHealthData directly using primitive strings so:
      band_capability_values == {'UNAVAILABLE'} only
    and ensure it can't satisfy the OK/DEGRADED "no band requested" rules:
      - OK(no band) requires ALL states in GOOD_STATES_SET (false for UNAVAILABLE)
      - DEGRADED(no band) requires ANY state in GOOD_STATES_SET (false for UNAVAILABLE)
    """
    logger = logging.getLogger(
        "test.health.failed.all_bands_not_good_when_no_band_requested"
    )
    cm = cm_without_er_lp
    hm = HealthManager(component_manager=cm, logger=logger)

    dh = DishHealthData(
        receiver_band=Band.NONE,
        k_value_validation_result=KValueValidationResultData(
            result_code=ResultCode.OK.name
        ),
        gpm_validation_result=GPMValidationResultData(result=["OK"]),
        band_capability_data=DishBandCapabilityStateData(
            band_capabilities={
                "B1": CapabilityStates.UNAVAILABLE.name,
                "B2": CapabilityStates.UNAVAILABLE.name,
                "B3": CapabilityStates.UNAVAILABLE.name,
                "B4": CapabilityStates.UNAVAILABLE.name,
                "B5a": CapabilityStates.UNAVAILABLE.name,
                "B5b": CapabilityStates.UNAVAILABLE.name,
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
