import json
from time import sleep

import pytest
import tango
from astropy import units as u
from astropy.coordinates import Angle
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory, DishMode, PointingState

from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    DISHLN_POINTING_DEVICE,
    NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES,
    build_partial_configure_data,
    get_non_sidereal_json_for_now,
    logger,
    tear_down,
)

OFFSET = 5.0


def configure_dish_leaf_node(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dishln_pointing_device = dev_factory.get_device(DISHLN_POINTING_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )
    dishpd_event_id = dishln_pointing_device.subscribe_event(
        "pointingProgramTrackTable",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingProgramTrackTable"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )

    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )
    group_callback["pointingState"].assert_change_event(
        (PointingState.TRACK),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )

    # Validate number of program track table entries is 150
    assert (
        len(json.loads(dishln_pointing_device.pointingProgramTrackTable))
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )

    result_config, unique_id_config = dish_leaf_node.TrackStop()
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )
    group_callback["pointingProgramTrackTable"].assert_change_event(
        ("[]"),
        lookahead=8,
    )
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    dishln_pointing_device.unsubscribe_event(dishpd_event_id)
    tear_down(dish_leaf_node, dish_master, group_callback)

@pytest.skip("Skipping non_sidereal_tracking test due to ongoing investigation")
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "json_to_use", ["dishleafnode_configure", "non_sidereal_tracking"]
)
def test_configure_command(
    tango_context, group_callback, json_factory, json_to_use, cm_pointig_device
):
    if json_to_use == "non_sidereal_tracking":
        pytest.skip("Skipping non_sidereal_tracking test due to ongoing investigation")
        json_to_use = get_non_sidereal_json_for_now(
            json_factory(json_to_use), cm_pointig_device
        )
        configure_dish_leaf_node(
            tango_context,
            DISH_LEAF_NODE_DEVICE,
            group_callback,
            json_to_use,
        )
    else:
        configure_dish_leaf_node(
            tango_context,
            DISH_LEAF_NODE_DEVICE,
            group_callback,
            json_factory(json_to_use),
        )


def partial_configure_dish_leaf_node(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
    partial_configure_input_str,
):
    """Partial configure flow for dish leaf node."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    sleep(1)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )

    source_offset_event_id = dish_leaf_node.subscribe_event(
        "sourceOffset",
        tango.EventType.CHANGE_EVENT,
        group_callback["sourceOffset"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=2,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )
    result_config, unique_id_config = dish_leaf_node.Configure(
        configure_input_str
    )
    assert result_config[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    partial_configurations = build_partial_configure_data(
        partial_configure_input_str, OFFSET
    )
    count = 0
    for input_str in partial_configurations:
        # Give a pause before invoking next configuration
        sleep(3)
        result_config, unique_id_config = dish_leaf_node.Configure(input_str)
        assert result_config[0] == ResultCode.QUEUED
        load_conf = json.loads(input_str)
        ca_offset = load_conf["pointing"]["target"]["ca_offset_arcsec"]
        ie_offset = load_conf["pointing"]["target"]["ie_offset_arcsec"]
        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id_config[0], COMMAND_COMPLETED),
            lookahead=8,
        )
        # Assert change event is occuring and values are reflecting
        # on sourceOffset attribute.
        group_callback["sourceOffset"].assert_change_event(
            [ca_offset, ie_offset],
            lookahead=2,
        )
        count += 1

    result_trackstop, unique_id_trackstop = dish_leaf_node.TrackStop()
    assert result_trackstop[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_trackstop[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )

    dish_leaf_node.unsubscribe_event(source_offset_event_id)
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_partial_configure_command(
    tango_context, group_callback, json_factory
):
    """Test partial configure functionality on Dish Leaf Node."""
    partial_configure_dish_leaf_node(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure"),
        json_factory("partial_configure"),
    )


def configure_with_wrap_sector(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
    wrap_sector,
):
    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dishln_pointing_device = dev_factory.get_device(DISHLN_POINTING_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dishmode_event_id = dish_leaf_node.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        group_callback["dishMode"],
    )
    pointingstate_event_id = dish_leaf_node.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingState"],
    )
    dishpd_event_id = dishln_pointing_device.subscribe_event(
        "pointingProgramTrackTable",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingProgramTrackTable"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    sleep(1)
    assert result_fp[0] == ResultCode.QUEUED

    lrcr_event_id = dish_leaf_node.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandResult"],
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_fp[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_FP),
        lookahead=6,
    )
    configure_input = json.loads(configure_input_str)
    configure_input['pointing']['wrap_sector'] = wrap_sector
    result_config, unique_id_config = dish_leaf_node.Configure(
        json.dumps(configure_input)
    )
    assert result_config[0] == ResultCode.QUEUED
    logger.info(
        f"Command ID: {unique_id_config} Returned result: {result_config}"
    )

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )
    group_callback["pointingState"].assert_change_event(
        (PointingState.TRACK),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )

    # Validate number of program track table entries is 150
    assert (
        len(json.loads(dishln_pointing_device.pointingProgramTrackTable))
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )

    result_config, unique_id_config = dish_leaf_node.TrackStop()
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    actualPointing = json.loads(dish_leaf_node.actualPointing)
    ra = actualPointing[1]
    dec = actualPointing[2]

    ra = Angle(ra, u.hour).deg
    dec = Angle(dec, u.deg).deg
    c1 = configure_input['pointing']['field']['attrs']['c1']
    c2 = configure_input['pointing']['field']['attrs']['c2']

    # Assert ra and dec is consistent with wrap_sector key change
    assert round(ra, 2) == round(c1, 2)
    assert round(dec, 2) == round(c2, 2)

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )
    group_callback["pointingProgramTrackTable"].assert_change_event(
        ("[]"),
        lookahead=8,
    )
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    dishln_pointing_device.unsubscribe_event(dishpd_event_id)
    tear_down(dish_leaf_node, dish_master, group_callback)


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize("wrap_sector", [0, -1])
def test_configure_command_with_wrap_sector(
    tango_context,
    group_callback,
    json_factory,
    wrap_sector,
):
    configure_with_wrap_sector(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure_adr106"),
        wrap_sector,
    )
