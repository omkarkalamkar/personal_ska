import logging

import pytest
from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode

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
def test_generate_health_info_collects_expected_errors(cm_without_er_lp):
    cm = cm_without_er_lp
    logger = logging.getLogger("test")
    hm = HealthManager(component_manager=cm, logger=logger)

    # Build a context with multiple error conditions
    context = DishHealthData(
        gpm_validation_result=GPMValidationResultData(result=["FAILED"]),
        k_value_validation_result=KValueValidationResultData(
            result_code=ResultCode.FAILED.name
        ),
        dish_manager_health_data=DishManagerHealthData(
            health_state=HealthState.DEGRADED
        ),
        band_capability_data=DishBandCapabilityStateData(
            band_capabilities={"B1": CapabilityStates.UNAVAILABLE}
        ),
    )

    health_info = hm.generate_health_info(context)

    # The implementation uses a fixed placeholder
    # dish name "mid-tmc/leaf-node-dish/ska001"
    dish_key = "mid-tmc/leaf-node-dish/ska001"
    assert "HealthSummary" in health_info
    assert dish_key in health_info["HealthSummary"]
    info_list = health_info["HealthSummary"][dish_key]["Info"]

    # Check presence of each expected error message fragment
    assert any("GPM validation failed" in s for s in info_list)
    assert any("KValue validation failed" in s for s in info_list)
    assert any(
        "Dish Manager" in s and "health state reported" in s for s in info_list
    )
    assert any("Band B1 capability state is" in s for s in info_list)


@pytest.mark.ut1
@pytest.mark.parametrize(
    "gpm_result,kvalue_code,dish_state,expect_gpm_err,"
    "expect_k_err,expect_dish_err",
    [
        # GPM OK, KValue OK, Dish OK -> no errors
        (["OK"], ResultCode.OK.name, HealthState.OK, False, False, False),
        # GPM FAILED, KValue OK, Dish OK -> only GPM error
        (["FAILED"], ResultCode.OK.name, HealthState.OK, True, False, False),
        # GPM OK, KValue FAILED, Dish OK -> only KValue error
        (["OK"], ResultCode.FAILED.name, HealthState.OK, False, True, False),
        # GPM OK, KValue OK, Dish DEGRADED -> only Dish Manager error
        (["OK"], ResultCode.OK.name, HealthState.DEGRADED, False, False, True),
        # GPM OK, KValue OK, Dish FAILED -> only Dish Manager error
        (["OK"], ResultCode.OK.name, HealthState.FAILED, False, False, True),
        # GPM OK, KValue OK, Dish UNKNOWN -> only Dish Manager error
        (["OK"], ResultCode.OK.name, HealthState.UNKNOWN, False, False, True),
        # Combined: GPM FAILED, KValue FAILED, Dish UNKNOWN -> all errors
        (
            ["FAILED"],
            ResultCode.FAILED.name,
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
    hm = HealthManager(component_manager=cm, logger=logger)

    context = DishHealthData(
        gpm_validation_result=GPMValidationResultData(result=gpm_result),
        k_value_validation_result=KValueValidationResultData(
            result_code=kvalue_code
        ),
        dish_manager_health_data=DishManagerHealthData(
            health_state=dish_state
        ),
        band_capability_data=DishBandCapabilityStateData(
            band_capabilities={"B1": CapabilityStates.OPERATE_FULL}
        ),
    )

    health_info = hm.generate_health_info(context)
    # generate_health_info uses a fixed placeholder
    # key "mid-tmc/leaf-node-dish/ska001"
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
