import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    GPM_JSON,
    logger,
    wait_and_validate_attribute_value_available,
)


def apply_pointing_model(tango_context, dishln_name, group_callback, gpm_json):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master_dev = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )
    dish_leaf_node.subscribe_event(
        "globalPointingModelParams",
        tango.EventType.CHANGE_EVENT,
        group_callback["globalPointingModelParams"],
    )
    dish_leaf_node.subscribe_event(
        "gpmVersion",
        tango.EventType.CHANGE_EVENT,
        group_callback["gpmVersion"],
    )
    dish_master_dev.subscribe_event(
        "band2PointingModelParams",
        tango.EventType.CHANGE_EVENT,
        group_callback["band2PointingModelParams"],
    )

    gpm_version = json.loads(dish_leaf_node.gpmversion)

    # Initial DLN gpmversion assertion
    for band, _ in gpm_version.items():
        assert gpm_version[band] == 'UNKNOWN'

    result, unique_id = dish_leaf_node.ApplyPointingModel(gpm_json)

    logger.info(f"Command ID: {unique_id} Returned result: {result}")

    assert result[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], '[0, "Successfully wrote the GPM values"]'),
        lookahead=8,
    )
    group_callback["globalPointingModelParams"].assert_change_event(
        GPM_JSON,
        lookahead=2,
    )

    group_callback["gpmVersion"].assert_change_event(
        Anything,
        lookahead=2,
    )

    gpm_version = json.loads(dish_leaf_node.gpmversion)

    assert gpm_version['Band_2'] == 'main'


def ApplyPointingModel_with_invalid_tm_path(
    tango_context, dishln_name, group_callback, gpm_json
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)

    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    result, unique_id = dish_leaf_node.ApplyPointingModel(gpm_json)

    logger.info(f"Command ID: {unique_id} Returned result: {result}")

    assert result[0] == ResultCode.QUEUED

    unique_id, message = group_callback[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=4,
    )[
        "attribute_value"
    ]

    assert "ApplyPointingModel" in unique_id
    assert "Error in loading global pointing" in message


def ApplyPointingModel_with_invalid_dish_id(
    tango_context, dishln_name, group_callback, gpm_json
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)

    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    result, unique_id = dish_leaf_node.ApplyPointingModel(gpm_json)

    logger.info(f"Command ID: {unique_id} Returned result: {result}")

    assert result[0] == ResultCode.QUEUED

    unique_id, message = group_callback[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=4,
    )[
        "attribute_value"
    ]

    assert "ApplyPointingModel" in unique_id
    assert "Global pointing antenna SKA002 is not matching" in message


def ApplyPointingModel_with_invalid_json(
    tango_context, dishln_name, group_callback, gpm_json
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)

    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    result, unique_id = dish_leaf_node.ApplyPointingModel(gpm_json)

    logger.info(f"Command ID: {unique_id} Returned result: {result}")

    assert result[0] == ResultCode.QUEUED

    unique_id, message = group_callback[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=4,
    )[
        "attribute_value"
    ]

    assert "ApplyPointingModel" in unique_id
    assert "JSON Error" in message


def gpm_version_restart_scenario(
    tango_context, dishln_name, group_callback, gpm_json
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_leaf_node.subscribe_event(
        "gpmVersion",
        tango.EventType.CHANGE_EVENT,
        group_callback["gpmVersion"],
    )

    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    gpm_version = json.loads(dish_leaf_node.gpmversion)
    flag = True
    band_name = 'Band_2'
    band_version = 'main'
    # Check band version is already set, if any
    for band, _ in gpm_version.items():
        if gpm_version[band] != 'UNKNOWN':
            band_name = band
            band_version = gpm_version[band]
            flag = False
            break

    if flag:
        result, unique_id = dish_leaf_node.ApplyPointingModel(gpm_json)
        logger.info(f"Command ID: {unique_id} Returned result: {result}")
        assert result[0] == ResultCode.QUEUED

        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id[0], COMMAND_COMPLETED),
            lookahead=8,
        )
        group_callback["gpmVersion"].assert_change_event(
            Anything,
            lookahead=2,
        )

    dish_leaf_node.init()

    assert wait_and_validate_attribute_value_available(
        dish_leaf_node,
        "lastPointingData",
        'Not Set',
    )

    assertion_data = group_callback["gpmVersion"].assert_change_event(
        Anything,
        lookahead=2,
    )
    gpm_version_data = json.loads(assertion_data["attribute_value"])
    assert gpm_version_data[band_name] == band_version


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.skip(reason="interminent failure")
def test_apply_pointing_model(tango_context, group_callback, json_factory):
    """Test to check ApplyPointingModel command with valid TM path"""
    apply_pointing_model(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("global_pointing_model"),
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_ApplyPointingModel_invalid_tm_path(
    tango_context, group_callback, json_factory
):
    """Test to check ApplyPointingModel command with invalid TM path"""

    gpm_tm_path = json.loads(json_factory("global_pointing_model"))
    gpm_tm_path["tm_data_sources"] = "Invalid_source"
    ApplyPointingModel_with_invalid_tm_path(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json.dumps(gpm_tm_path),
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_apply_pointing_model_with_erroneous_json(
    tango_context, group_callback, json_factory
):
    """Test to check ApplyPointingModel command with valid TM path"""
    ApplyPointingModel_with_invalid_json(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("global_pointing_model_faulty"),
    )


@pytest.mark.post_deployment
@pytest.mark.restart_device_server
@pytest.mark.xfail(reason="Restarting device sometimes make the pod unstable")
def test_gpm_restart_scenario(tango_context, group_callback, json_factory):
    """Test to check GPM version memorization"""
    gpm_version_restart_scenario(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("global_pointing_model"),
    )
