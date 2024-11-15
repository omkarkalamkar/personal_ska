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
    dish_master_dev.subscribe_event(
        "band2PointingModelParams",
        tango.EventType.CHANGE_EVENT,
        group_callback["band2PointingModelParams"],
    )

    result, unique_id = dish_leaf_node.ApplyPointingModel(gpm_json)

    logger.info(f"Command ID: {unique_id} Returned result: {result}")

    assert result[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], COMMAND_COMPLETED),
        lookahead=8,
    )
    group_callback["globalPointingModelParams"].assert_change_event(
        GPM_JSON,
        lookahead=8,
    )


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
    assert "Error in Loading global pointing" in message


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


@pytest.mark.test
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
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
