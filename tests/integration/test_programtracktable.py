import time

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory, DishMode, PointingState

from ska_tmc_dishleafnode.constants import TRACK_TABLE_ENTRY_SIZE
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    logger,
    tear_down,
)


def check_track_table(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
):
    try:
        logger.info(f"{tango_context}")
        dev_factory = DevFactory()
        dish_leaf_node = dev_factory.get_device(dishln_name)
        dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
        dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
        dishmode_event_id = dish_leaf_node.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            group_callback["dishMode"],
        )
        pointing_state_event_id = dish_leaf_node.subscribe_event(
            "pointingState",
            tango.EventType.CHANGE_EVENT,
            group_callback["pointingState"],
        )

        group_callback["dishMode"].assert_change_event(
            (DishMode.STANDBY_LP),
            lookahead=2,
        )

        result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
        assert result_fp[0] == ResultCode.QUEUED

        cmd_result_event_id = dish_leaf_node.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            group_callback["longRunningCommandResult"],
        )

        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id_fp[0], str(int(ResultCode.OK))),
            lookahead=5,
        )

        result_config, unique_id_config = dish_leaf_node.Configure(
            configure_input_str
        )
        assert result_config[0] == ResultCode.QUEUED

        logger.info(
            f"Command ID: {unique_id_config} Returned result: {result_config}"
        )

        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id_config[0], str(int(ResultCode.OK))),
            lookahead=6,
        )
        group_callback["pointingState"].assert_change_event(
            (PointingState.TRACK, PointingState.SLEW),
            lookahead=6,
        )

        TIMEOUT = 10
        start_time = time.time()
        while (time.time() - start_time) < TIMEOUT:
            if len(dish_master.programTrackTable) != 0:
                break
            time.sleep(0.5)

        program_track_table = dish_master.programTrackTable

        if len(program_track_table) == 0:
            raise Exception(
                "TrackTable is not generated, Timeout has occurred"
            )

        logger.info(f"ProgramTrackTable: {program_track_table}")

        assert (
            len(program_track_table) > 0
            and len(program_track_table) % TRACK_TABLE_ENTRY_SIZE == 0
        )

        for item in program_track_table:
            assert isinstance(item, float)

        result_config, unique_id_config = dish_leaf_node.TrackStop()

        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id_config[0], str(int(ResultCode.OK))),
            lookahead=6,
        )

        group_callback["pointingState"].assert_change_event(
            (PointingState.READY),
            lookahead=6,
        )

        tear_down(dish_leaf_node, dish_master, group_callback)

        dish_leaf_node.unsubscribe_event(dishmode_event_id)
        dish_leaf_node.unsubscribe_event(pointing_state_event_id)
        dish_leaf_node.unsubscribe_event(cmd_result_event_id)
    except Exception as exception:
        logger.exception(exception)
        tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_program_track_table(tango_context, group_callback, json_factory):
    check_track_table(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
    )
