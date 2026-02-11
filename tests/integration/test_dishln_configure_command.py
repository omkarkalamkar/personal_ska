import json
import math
import time

import pytest
import tango
from astropy import units as u
from astropy.coordinates import Angle
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory, DishMode, PointingState
from tango import DeviceProxy

from tests.settings import (
    COMMAND_COMPLETED,
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    DISHLN_POINTING_DEVICE,
    NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES,
    build_delta_configure_data,
    build_partial_configure_data,
    get_non_sidereal_json_for_now,
    logger,
    tear_down,
    wait_and_validate_attribute_value_available,
)

TIMEOUT_ACTUAL_POINTING = 10
OFFSET = 5.0


def wait_for_actual_pointing_value(
    device: DeviceProxy, attribute_name: str, c1: float, c2: float
) -> bool:
    """Waits for attribute value to change on the given device."""
    start_time = time.time()
    while time.time() - start_time <= TIMEOUT_ACTUAL_POINTING:
        time.sleep(1)
        actual_pointing = device.read_attribute(attribute_name).value
        if not actual_pointing:
            continue
        act_point_json = json.loads(actual_pointing)
        logger.info("Expected Pointing: c1: %s, c2: %s", c1, c2)
        logger.info("ActualPointing: %s,c1: %s,c2: %s", act_point_json, c1, c2)
        if act_point_json:
            ra = act_point_json[1]
            dec = act_point_json[2]
            ra = Angle(ra, u.hour).deg
            dec = Angle(dec, u.deg).deg

            logger.info("Expected: RA=%.20f, Dec=%.20f", c1, c2)
            logger.info("Actual:   RA=%.20f, Dec=%.20f", ra, dec)
            diff_ra = ra - c1
            diff_dec = dec - c2
            logger.info("Diff: RA=%.20f°, Dec=%.20f°", diff_ra, diff_dec)

            if math.isclose(ra, c1, abs_tol=0.9) and math.isclose(
                dec, c2, abs_tol=0.02
            ):
                return True

    return False


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
    time.sleep(1)
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
        (PointingState.SLEW),
        lookahead=6,
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )
    wait_and_validate_attribute_value_available(
        dish_leaf_node, "pointingState", PointingState.TRACK, timeout=30
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
    # same event no event
    # group_callback["dishMode"].assert_change_event(
    #     (DishMode.OPERATE),
    #     lookahead=6,
    # )
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
@pytest.mark.parametrize(
    "json_to_use", ["dishleafnode_configure", "non_sidereal_tracking"]
)
def test_configure_command(
    tango_context, group_callback, json_factory, json_to_use, cm_pointig_device
):
    if json_to_use == "non_sidereal_tracking":
        json_to_use = get_non_sidereal_json_for_now(
            json_factory(json_to_use), cm_pointig_device
        )
        # It was found that some times targets are not visible,during specific
        # IST morning hours
        # so we can skip test in that case.
        if json_to_use:
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
    time.sleep(1)
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
    time.sleep(1)
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
        time.sleep(3)
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


def delta_configure_dish_leaf_node(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
    delta_config_str,
    is_default_offset,
    delta_only_once=False,
):
    """Delta configure flow for dish leaf node."""
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(dishln_name)
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_pointing_device = dev_factory.get_device(DISHLN_POINTING_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    time.sleep(1)
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

    ptt_event_id = dish_pointing_device.subscribe_event(
        "pointingProgramTrackTable",
        tango.EventType.CHANGE_EVENT,
        group_callback["pointingProgramTrackTable"],
    )

    group_callback["dishMode"].assert_change_event(
        (DishMode.STANDBY_LP),
        lookahead=2,
    )

    result_fp, unique_id_fp = dish_leaf_node.SetStandbyFPMode()
    time.sleep(1)
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
    configure_input = json.loads(configure_input_str)
    if not is_default_offset:
        configure_input["pointing"]["trajectory"]["attrs"] = {
            "x": 1.0,
            "y": 2.0,
        }
    result_config, unique_id_config = dish_leaf_node.Configure(
        json.dumps(configure_input)
    )
    assert result_config[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )
    if not delta_only_once:
        delta_configurations = build_delta_configure_data(
            delta_config=delta_config_str,
            x_offsets=[-5.0, 5.0, 3.0, 2.0, 1.0, 2.0],
            y_offsets=[5.0, 1.0, 3.0, 2.0, -2.0, -1.0],
        )
        count = 0
        for input_str in delta_configurations:
            # Give a pause before invoking next configuration
            time.sleep(3)
            result_config, unique_id_config = dish_leaf_node.Configure(
                input_str
            )
            assert result_config[0] == ResultCode.QUEUED
            group_callback["longRunningCommandResult"].assert_change_event(
                (unique_id_config[0], COMMAND_COMPLETED),
                lookahead=8,
            )
            count += 1
    else:
        result_config, unique_id_config = dish_leaf_node.Configure(
            delta_config_str
        )
        assert result_config[0] == ResultCode.QUEUED
        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id_config[0], COMMAND_COMPLETED),
            lookahead=8,
        )
    # if collimation offsets provided then validate source offset
    delta_json = json.loads(delta_config_str)
    if "ie_offset_arcsec" in delta_json.get(
        "pointing", {}
    ) or "ca_offset_arcsec" in delta_json.get("pointing", {}):
        collimation_offsets = [
            delta_json["pointing"].get("ca_offset_arcsec", 0.0),
            delta_json["pointing"].get("ie_offset_arcsec", 0.0),
        ]
        group_callback["sourceOffset"].assert_change_event(
            collimation_offsets,
            lookahead=2,
        )

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

    group_callback["pointingProgramTrackTable"].assert_change_event(
        ("[]"),
        lookahead=8,
    )

    dish_leaf_node.unsubscribe_event(source_offset_event_id)
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    dish_pointing_device.unsubscribe_event(ptt_event_id)
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


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_delta_configure_command(tango_context, group_callback, json_factory):
    """Test delta configure functionality on Dish Leaf Node."""
    delta_configure_dish_leaf_node(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure_adr106"),
        json_factory("delta_configure"),
        is_default_offset=True,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "delta_configure_type",
    [
        "only_trajectory",
        "only_receiver_band",
        "trajectory_receiver_band",
        "only_projection",
        "field_trajectory",
        "only_collimation_offsets",
    ],
)
def test_delta_configure_with_possible_json(
    tango_context, group_callback, json_factory, delta_configure_type
):
    """Test delta configure json with all possible combination"""
    delta_configure = json.loads(json_factory("delta_configure"))
    if delta_configure_type == "only_trajectory":
        delta_configure["pointing"].pop("projection")
    elif delta_configure_type == "only_receiver_band":
        delta_configure.pop("pointing")
        delta_configure["dish"] = {}
        delta_configure["dish"]["receiver_band"] = "2"
    elif delta_configure_type == "trajectory_receiver_band":
        delta_configure["pointing"].pop("projection")
        delta_configure["dish"] = {}
        delta_configure["dish"]["receiver_band"] = "2"
    elif delta_configure_type == "only_projection":
        delta_configure["pointing"].pop("trajectory")
    elif delta_configure_type == "field_trajectory":
        delta_configure["pointing"].pop("trajectory")
        delta_configure["pointing"]["field"] = {
            "reference_frame": "icrs",
            "target_name": "Cen-A",
            "attrs": {"c1": 317.19966666666666, "c2": -88.95636111111111},
        }
    elif delta_configure_type == "only_collimation_offsets":
        delta_configure["pointing"].pop("trajectory")
        delta_configure["pointing"].pop("projection")
        delta_configure["pointing"] = {
            "ca_offset_arcsec": 0.0,
            "ie_offset_arcsec": 5.0,
        }

    delta_configure_dish_leaf_node(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure_adr106"),
        json.dumps(delta_configure),
        is_default_offset=True,
        delta_only_once=True,
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_delta_configure_command_with_different_offset(
    tango_context, group_callback, json_factory
):
    """Test delta configure functionality on Dish Leaf Node."""
    delta_configure_dish_leaf_node(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("dishleafnode_configure_adr106"),
        json_factory("delta_configure"),
        is_default_offset=False,
    )


def configure_with_wrap_sector(
    tango_context,
    dishln_name,
    group_callback,
    configure_input_str,
    wrap_sector,
    partial_or_delta_configure,
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
    time.sleep(1)
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
        (PointingState.SLEW),
        lookahead=6,
    )

    wait_and_validate_attribute_value_available(
        dish_leaf_node, "pointingState", PointingState.TRACK, timeout=30
    )
    group_callback["dishMode"].assert_change_event(
        (DishMode.OPERATE),
        lookahead=6,
    )
    field = json.loads(configure_input_str)["pointing"].get("field", {})
    if field:
        c1 = configure_input['pointing']['field']['attrs']['c1']
        c2 = configure_input['pointing']['field']['attrs']['c2']
    else:
        c1 = configure_input["pointing"]["target"]["ra"]
        c2 = configure_input["pointing"]["target"]["dec"]
        c1 = Angle(c1, u.hour).deg
        c2 = Angle(c2, u.deg).deg

    # Main configure
    assert wait_for_actual_pointing_value(
        dish_leaf_node, "actualPointing", c1, c2
    )

    # Validate number of program track table entries is 150
    assert (
        len(json.loads(dishln_pointing_device.pointingProgramTrackTable))
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )

    # Verify wrap_sector set on dish pointing device.
    assert (
        wrap_sector
        == json.loads(dishln_pointing_device.targetdata)["pointing"][
            "wrap_sector"
        ]
    )

    flag = False
    timeout = 0

    while not flag and timeout <= 5:
        # Verify that program track table gets affected with main configure
        program_track_table = json.loads(
            dishln_pointing_device.pointingprogramtracktable
        )
        # when wrap_sector = 0
        if (not wrap_sector and program_track_table[1] > 0) or (
            wrap_sector and program_track_table[1] < 0
        ):  # when wrap_sector = -1
            flag = True
        else:
            # Safe check: Allow some time to generate PTT
            time.sleep(1)
            timeout += 1

    assert flag  # Verify PTT updated.
    # Delta/Partial configure
    partial_or_delta_configure_json = json.loads(partial_or_delta_configure)
    old_partial_configure = (
        partial_or_delta_configure_json.get("pointing")
        .get("target", {})
        .get("ca_offset_arcsec", None)
    )
    if old_partial_configure:
        # Invoke old partial configure json with wrap sector key
        # Update the wrap sector value, different from main configure
        if not wrap_sector:
            wrap_sector = -1
        else:
            wrap_sector = 0
        partial_or_delta_configure_json["pointing"][
            "wrap_sector"
        ] = wrap_sector
        result_config, unique_id_config = dish_leaf_node.Configure(
            json.dumps(partial_or_delta_configure_json)
        )
        assert result_config[0] == ResultCode.QUEUED
        load_conf = json.loads(partial_or_delta_configure)
        ca_offset = load_conf["pointing"]["target"]["ca_offset_arcsec"]
        ie_offset = load_conf["pointing"]["target"]["ie_offset_arcsec"]
        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id_config[0], COMMAND_COMPLETED),
            lookahead=8,
        )
        group_callback["sourceOffset"].assert_change_event(
            [ca_offset, ie_offset],
            lookahead=2,
        )
    else:
        # Delete unnecessary keys from adr-106 delta conf json
        if "trajectory" in partial_or_delta_configure_json["pointing"]:
            del partial_or_delta_configure_json["pointing"]["trajectory"]
        if "projection" in partial_or_delta_configure_json["pointing"]:
            del partial_or_delta_configure_json["pointing"]["projection"]
        if "field" in partial_or_delta_configure_json["pointing"]:
            del partial_or_delta_configure_json["pointing"]["field"]

        if not wrap_sector:
            wrap_sector = -1
        else:
            wrap_sector = 0
        partial_or_delta_configure_json["pointing"][
            "wrap_sector"
        ] = wrap_sector
        result_config, unique_id_config = dish_leaf_node.Configure(
            json.dumps(partial_or_delta_configure_json)
        )
        assert result_config[0] == ResultCode.QUEUED
        group_callback["longRunningCommandResult"].assert_change_event(
            (unique_id_config[0], COMMAND_COMPLETED),
            lookahead=8,
        )

    # Verify wrap_sector set on dish pointing device
    assert (
        wrap_sector
        == json.loads(dishln_pointing_device.targetdata)["pointing"][
            "wrap_sector"
        ]
    )

    flag = False
    timeout = 0

    while not flag and timeout <= 5:
        # Verify that program track table gets affected with
        # partial/delta configure
        program_track_table = json.loads(
            dishln_pointing_device.pointingprogramtracktable
        )
        # when wrap_sector = 0
        if (not wrap_sector and program_track_table[1] > 0) or (
            wrap_sector and program_track_table[1] < 0
        ):  # when wrap_sector = -1
            flag = True
        else:
            # Safe check: Allow some time to generate PTT
            time.sleep(1)
            timeout += 1

    assert flag  # Verify PTT updated.

    result_config, unique_id_config = dish_leaf_node.TrackStop()
    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id_config[0], COMMAND_COMPLETED),
        lookahead=6,
    )

    group_callback["pointingState"].assert_change_event(
        (PointingState.READY),
        lookahead=6,
    )

    # group_callback["dishMode"].assert_change_event(
    #     (DishMode.OPERATE),
    #     lookahead=6,
    # ) same event

    group_callback["pointingProgramTrackTable"].assert_change_event(
        ("[]"),
        lookahead=8,
    )
    dish_leaf_node.unsubscribe_event(dishmode_event_id)
    dish_leaf_node.unsubscribe_event(pointingstate_event_id)
    dish_leaf_node.unsubscribe_event(lrcr_event_id)
    dishln_pointing_device.unsubscribe_event(dishpd_event_id)
    tear_down(dish_leaf_node, dish_master, group_callback)


# @pytest.mark.xfail(
#     reason="Test is failing due to mismatch of " "expected and actual values"
# )
@pytest.mark.post_deployment
@pytest.mark.SKA_mid
@pytest.mark.parametrize(
    "wrap_sector, json_to_use, partial_or_delta_conf",
    [
        (wrap_sector, main_conf_type, partial_conf_type)
        for wrap_sector in [0, -1]
        for main_conf_type in [
            "dishleafnode_configure",
            "dishleafnode_configure_adr106",
        ]
        for partial_conf_type in ["partial_configure", "delta_configure"]
    ],
)
def test_configure_command_with_wrap_sector(
    tango_context,
    group_callback,
    json_factory,
    wrap_sector,
    json_to_use,
    partial_or_delta_conf,
):
    configure_with_wrap_sector(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory(json_to_use),
        wrap_sector,
        json_factory(partial_or_delta_conf),
    )
