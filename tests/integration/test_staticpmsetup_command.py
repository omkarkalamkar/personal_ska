import json

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import COMMAND_COMPLETED, DISH_LEAF_NODE_DEVICE, logger


def static_pm_setup(tango_context, dishln_name, group_callback, gpm_json):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)

    dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    result, unique_id = dish_leaf_node.StaticPmSetup(gpm_json)

    logger.info(f"Command ID: {unique_id} Returned result: {result}")

    assert result[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], COMMAND_COMPLETED),
        lookahead=2,
    )


def staticpmsetup_with_invalid_tm_path(
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

    result, unique_id = dish_leaf_node.StaticPmSetup(gpm_json)

    logger.info(f"Command ID: {unique_id} Returned result: {result}")

    assert result[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], '[5, "Error in TelModel path"]'),
        lookahead=2,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_static_pm_setup(tango_context, group_callback, json_factory):
    """Test to check StaticPmSetup command with valid TM path"""
    static_pm_setup(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("global_pointing_model"),
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_staticpmsetup_invalid_tm_path(
    tango_context, group_callback, json_factory
):
    """Test to check StaticPmSetup command with invalid TM path"""

    gpm_tm_path = json.loads(json_factory("global_pointing_model"))
    gpm_tm_path["tm_data_sources"] = "Invalid_source"
    staticpmsetup_with_invalid_tm_path(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json.dumps(gpm_tm_path),
    )
