import json

import pytest
import tango
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tango_base.control_model import ObsState
from ska_tango_testing.mock.placeholders import Anything
from ska_tmc_common import DevFactory, FaultType
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from tests.settings import DISH_MASTER_DEVICE, logger, wait_for_dish_mode


def test_configure_command_completed(
    tango_context,
    cm,
    task_callback,
    json_factory,
):
    cm.update_device_dish_mode(DishMode.STANDBY_LP)
    cm.is_setstandbyfpmode_allowed()
    cm.setstandbyfpmode(task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK},
        lookahead=4,
    )


@pytest.mark.skip(reason="Test fails randomly and need investigation")
def test_configure_command_completed_partial_config(
    tango_context, cm, task_callback, json_factory, group_callback
):
    """Test partial configure functionality"""
    cm.update_device_dish_mode(DishMode.OPERATE)
    dish_device = DevFactory().get_device("ska001/elt/master")
    dish_device.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        group_callback["longRunningCommandStatus"],
        stateless=True,
    )
    assert wait_for_dish_mode(cm, DishMode.OPERATE)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("partial_configure")

    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    group_callback["longRunningCommandStatus"].assert_change_event(
        (Anything, "COMPLETED"),
        lookahead=6,
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK},
        lookahead=4,
    )


@pytest.mark.skip(reason="Test fails randomly and need investigation")
def test_configure_command_completed_partial_config_missing_key(
    tango_context, cm, task_callback, json_factory
):
    """Test partial configure functionality"""
    cm.update_device_dish_mode(DishMode.OPERATE)

    assert cm.is_configure_allowed()
    configure_input_str = json_factory("partial_configure")
    config_json = json.loads(configure_input_str)
    del config_json["pointing"]["target"]["ca_offset_arcsec"]
    configure_input_str = json.dumps(config_json)

    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    logger.debug("Waiting for command completion")
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK},
        lookahead=10,
    )


@pytest.mark.skip(
    reason="Test case runs with CORBA exception for indefinite time"
)
def test_configure_command_adapter_none(task_callback, cm, json_factory):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, result=ResultCode.FAILED
    )


@pytest.mark.parametrize("key", ["pointing", "dish"])
def test_json_validation(tango_context, task_callback, cm, json_factory, key):
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    configure_input_str = json_factory("dishleafnode_configure")
    config_json = json.loads(configure_input_str)
    del config_json[key]
    configure_input_str = json.dumps(config_json)
    result, message = cm.configure(
        configure_input_str, task_callback=task_callback
    )
    assert result == ResultCode.FAILED
    assert f"{key} key is not present" in message


def test_configure_command_not_allowed(tango_context, cm):
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_configure_allowed()


@pytest.mark.manual10
def test_configure_timeout(tango_context, cm, task_callback, json_factory):
    cm.update_device_dish_mode(DishMode.STANDBY_LP)
    cm.is_setstandbyfpmode_allowed()
    cm.setstandbyfpmode(task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.COMPLETED, "result": ResultCode.OK}
    )
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)

    configure_input_str = json_factory("dishleafnode_configure")

    defect = {
        "enabled": True,
        "fault_type": FaultType.STUCK_IN_INTERMEDIATE_STATE,
        "error_message": "Command stuck in processing",
        "result": ResultCode.FAILED,
        "intermediate_state": ObsState.RESOURCING,
    }

    dev_factory = DevFactory()
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    dish_master.SetDirectDishMode(DishMode.STANDBY_LP)
    dish_master.SetDefective(json.dumps(defect))
    assert cm.is_configure_allowed()
    cm.configure(configure_input_str, task_callback=task_callback)

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED,
        result=ResultCode.FAILED,
        exception="Timeout has occurred, command failed",
    )
    dish_master.SetDefective(json.dumps({"enabled": False}))
