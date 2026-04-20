"""Test ConfigureBand command of DishLeafNode.
"""
import json
import threading
import time

import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.commands.configure_band_command import ConfigureBand
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import (
    DISH_CONFIGURE_1_0,
    DISH_MASTER_DEVICE,
    get_mock_adapter_factory,
    simulate_events_on_dish_device,
)


def test_configure_band_command_completed(task_callback, cm):
    command_id = f"{time.time()}_ConfigureBand"

    cm.adapter_factory = get_mock_adapter_factory(command_id)

    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configureband_allowed()

    argin = json.dumps({"dish": {"receiver_band": "1"}})
    config_band = ConfigureBand(
        cm, cm.op_state_model, cm.adapter_factory, cm.logger
    )
    simulate_events_on_dish_device(
        cm, [DISH_MASTER_DEVICE], DishMode.OPERATE, cmd_object=config_band
    )
    config_band.configure_band(
        argin, task_callback=task_callback, task_abort_event=threading.Event()
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )


def test_configureband_command_adapter_none(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configureband_allowed()
    argin = json.dumps({"dish": {"receiver_band": "1"}})

    cm.configureband(
        argin, task_callback=task_callback, task_abort_event=threading.Event()
    )

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, lookahead=4
    )
    assert ResultCode.FAILED == result["result"][0]
    assert "TRANSIENT_NoUsableProfile" in result["result"][1]


def test_configureband_command_not_allowed(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_configureband_allowed()


def test_configureband_command_with_spfrx_params(task_callback, cm):
    """Test ConfigureBand with spfrx parameters."""
    command_id = f"{time.time()}_ConfigureBand"
    cm.adapter_factory = get_mock_adapter_factory(command_id)

    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configureband_allowed()
    config_band = ConfigureBand(
        cm, cm.op_state_model, cm.adapter_factory, cm.logger
    )
    simulate_events_on_dish_device(
        cm, [DISH_MASTER_DEVICE], DishMode.OPERATE, cmd_object=config_band
    )
    config_band.configure_band(
        DISH_CONFIGURE_1_0,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )
