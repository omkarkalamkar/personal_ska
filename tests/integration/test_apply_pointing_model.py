import json
from time import sleep

import numpy as np
import pytest
import tango
from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    logger,
    wait_and_validate_attribute_value_available,
)


def gpm_validation_result(
    group_callback, band_name: str, band_result: str
) -> str:
    """Method to set gpm result for comparision in event callback"""
    timeout = 2
    flag = False
    while timeout >= 0:
        attribute_value = group_callback[
            "gpmValidationResult"
        ].assert_change_event(Anything, lookahead=5,)["attribute_value"]
        gpm_validation_result = json.loads(attribute_value)
        if gpm_validation_result[band_name] == band_result:
            flag = True
            break
        sleep(1)
        timeout -= 1
    assert flag


def apply_pointing_model(tango_context, dishln_name, group_callback, gpm_json):
    """Test to check ApplyPointingModel command with valid TM path"""

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
        "band1PointingModelParams",
        tango.EventType.CHANGE_EVENT,
        group_callback["band1PointingModelParams"],
    )
    dish_leaf_node.subscribe_event(
        "gpmvalidationresult",
        tango.EventType.CHANGE_EVENT,
        group_callback["gpmValidationResult"],
    )
    dish_leaf_node.subscribe_event(
        "healthState",
        tango.EventType.CHANGE_EVENT,
        group_callback["healthState"],
    )

    dish_leaf_node.gpmversion = """
    {"Band_1": "UNKNOWN",
    "Band_2": "UNKNOWN",
    "Band_3": "UNKNOWN",
    "Band_4": "UNKNOWN",
    "Band_5a": "UNKNOWN",
    "Band_5b": "UNKNOWN"
    }"""
    gpm_version = json.loads(dish_leaf_node.gpmversion)

    # Initial DLN gpmversion assertion
    for band, _ in gpm_version.items():
        assert gpm_version[band] == 'UNKNOWN'

    result, unique_id = dish_leaf_node.ApplyPointingModel(gpm_json)

    logger.info(f"Command ID: {unique_id} Returned result: {result}")

    assert result[0] == ResultCode.QUEUED

    group_callback["longRunningCommandResult"].assert_change_event(
        (unique_id[0], '[0, "Successfully wrote the GPM values"]'),
        lookahead=5,
    )
    group_callback["globalPointingModelParams"].assert_change_event(
        Anything,
        lookahead=5,
    )
    group_callback["gpmVersion"].assert_change_event(
        Anything,
        lookahead=5,
    )
    gpm_version = json.loads(dish_leaf_node.gpmversion)
    assert gpm_version['Band_1'] == 'main'

    # GPM validation scenarios
    # Scenario 1:
    # Validation success. Band params are matching for given band
    gpm_validation_result(group_callback, "Band_1", "OK")

    group_callback["healthState"].assert_change_event(
        HealthState.OK,
        lookahead=5,
    )

    # Scenario 2:
    # Validation failure. Band params are not matching for given band
    dish_band1pointingmodelparams = dish_master_dev.band1pointingmodelparams
    dish_band1pointingmodelparams = dish_band1pointingmodelparams.tolist()
    band1pointingmodelparams_index1 = dish_band1pointingmodelparams[1]
    band1pointingmodelparams_index1 += 1
    # Change the value on the given band
    dish_band1pointingmodelparams[1] = band1pointingmodelparams_index1
    dish_master_dev.band1pointingmodelparams = dish_band1pointingmodelparams
    group_callback["globalPointingModelParams"].assert_change_event(
        Anything,
        lookahead=5,
    )

    gpm_validation_result(group_callback, "Band_1", "FAILED")

    group_callback["healthState"].assert_change_event(
        HealthState.DEGRADED,
        lookahead=5,
    )
    gpm_version = json.loads(dish_leaf_node.gpmversion)
    assert gpm_version['Band_1'] == 'main'

    # Scenario 3:
    # Connection lost: Dish sent its event on band1PointingModelParams
    band1pointingmodelparams_index1 -= 1
    dish_band1pointingmodelparams[1] = band1pointingmodelparams_index1
    dish_master_dev.band1pointingmodelparams = dish_band1pointingmodelparams
    group_callback["globalPointingModelParams"].assert_change_event(
        Anything,
        lookahead=5,
    )
    gpm_validation_result(group_callback, "Band_1", "OK")
    group_callback["healthState"].assert_change_event(
        HealthState.OK,
        lookahead=5,
    )
    gpm_version = json.loads(dish_leaf_node.gpmversion)
    assert gpm_version['Band_1'] == 'main'

    # Scenario 4:
    # GPM version on Band_3 is Unknown and Dish band3 sent pointing model
    # param values
    dish_master_dev.band3pointingmodelparams = dish_band1pointingmodelparams
    group_callback["globalPointingModelParams"].assert_change_event(
        Anything,
        lookahead=5,
    )

    gpm_validation_result(group_callback, "Band_3", "FAILED")

    group_callback["healthState"].assert_change_event(
        HealthState.DEGRADED,
        lookahead=5,
    )
    gpm_version = json.loads(dish_leaf_node.gpmversion)
    assert gpm_version['Band_3'] == 'UNKNOWN'

    # Scenario 5:
    # Auto applying GPM if DLN has version for given band and dish sends empty
    # values for that band [Dish master restart scenario]
    dish_band5apointingmodelparams = dish_master_dev.band5apointingmodelparams
    # assert no value set on band_5a
    assert not dish_band5apointingmodelparams.tolist()

    # Set GPM version on Band_5a of DLN to 1.5.1
    gpm_version = json.loads(dish_leaf_node.gpmversion)
    assert gpm_version['Band_5a'] == 'UNKNOWN'
    gpm_version['Band_5a'] = '1.5.1'
    dish_leaf_node.gpmversion = json.dumps(gpm_version)
    gpm_version = json.loads(dish_leaf_node.gpmversion)
    assert gpm_version['Band_5a'] == '1.5.1'
    # Create an event on Band_5a of dish master with empty values in it
    dish_master_dev.band5apointingmodelparams = np.array([])
    group_callback["globalPointingModelParams"].assert_change_event(
        Anything,
        lookahead=5,
    )
    group_callback["gpmVersion"].assert_change_event(
        Anything,
        lookahead=5,
    )

    gpm_validation_result(group_callback, "Band_5a", "OK")

    group_callback["healthState"].assert_change_event(
        HealthState.DEGRADED,
        lookahead=5,
    )
    # Assert Band_5a contains values
    assert (dish_master_dev.band5apointingmodelparams).tolist()

    # Scenario 6:
    # GPM version doesnt change on APM command failure
    source_path = (
        "car://gitlab.com/ska-telescope/ska-tmc/"
        "ska-tmc-simulators?hm-808#tmdata"
    )
    file_path = (
        "instrument/ska_mid1/global_pointing_model_data"
        "/gpm-ska001-Band_5b.json"
    )
    gpm_json = {
        "interface": "https://schema.skao.int/ska-mid-cbf-initsysparam/1.0",
        "tm_data_sources": [source_path],
        "tm_data_filepath": file_path,
    }
    gpm_version = json.loads(dish_leaf_node.gpmversion)
    band_5b_version = gpm_version['Band_5b']
    result, unique_id = dish_leaf_node.ApplyPointingModel(json.dumps(gpm_json))
    logger.info(f"Command ID: {unique_id} Returned result: {result}")
    assert result[0] == ResultCode.QUEUED
    unique_id, message = group_callback[
        "longRunningCommandResult"
    ].assert_change_event(
        (unique_id[0], Anything),
        lookahead=5,
    )[
        "attribute_value"
    ]
    result_code, mesg = json.loads(message)
    assert result_code == ResultCode.FAILED
    assert 'ApplyPointingModel failed' in mesg
    gpm_version = json.loads(dish_leaf_node.gpmversion)
    assert band_5b_version == gpm_version['Band_5b']

    # Restore health state to OK for further tests
    dish_master_dev.band3pointingmodelparams = np.array([])

    gpm_validation_result(group_callback, "Band_3", "UNKNOWN")

    group_callback["healthState"].assert_change_event(
        HealthState.OK,
        lookahead=5,
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
        lookahead=5,
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
        lookahead=5,
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
        lookahead=5,
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
    band_name = 'Band_1'
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
            (unique_id[0], '[0, "Successfully wrote the GPM values"]'),
            lookahead=5,
        )
        group_callback["gpmVersion"].assert_change_event(
            Anything,
            lookahead=5,
        )

    dish_leaf_node.init()

    assert wait_and_validate_attribute_value_available(
        dish_leaf_node,
        "lastPointingData",
        'Not Set',
    )

    assertion_data = group_callback["gpmVersion"].assert_change_event(
        Anything,
        lookahead=5,
    )

    gpm_version_data = json.loads(assertion_data["attribute_value"])
    assert gpm_version_data[band_name] == band_version
    assert dish_leaf_node.gpmsourcepath
    assert dish_leaf_node.gpmfilepath


@pytest.mark.post_deployment
@pytest.mark.SKA_midskip
def test_apply_pointing_model(tango_context, group_callback, json_factory):
    """Test to check ApplyPointingModel command with valid TM path"""
    apply_pointing_model(
        tango_context,
        DISH_LEAF_NODE_DEVICE,
        group_callback,
        json_factory("global_pointing_model"),
    )


@pytest.mark.post_deployment
@pytest.mark.SKA_midskip
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
@pytest.mark.SKA_midskip
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
