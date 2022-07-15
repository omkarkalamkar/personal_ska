import time

import pytest
from ska_tango_base.commands import TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed
from tango import DevState

from tests.mock_callable import MockCallable
from tests.settings import create_cm


@pytest.mark.long_running
def test_setstandbyfpmode_command(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    assert cm.is_command_allowed("SetStandbyFPMode")

    unique_id = f"{time.time()}_SetStandbyFPMode"
    task_callback = MockCallable(unique_id)
    cm.setstandbyfpmode(task_callback=task_callback)
    assert task_callback.status == TaskStatus.COMPLETED


@pytest.mark.long_running
def test_setstandbyfpmode_command_adapter_none(
    tango_context, dish_master_device
):
    cm = create_cm(dish_master_device)
    cm.timeout = 0
    assert cm.is_command_allowed("SetStandbyFPMode")

    unique_id = f"{time.time()}_SetStandbyFPMode"
    task_callback = MockCallable(unique_id)
    cm.setstandbyfpmode(task_callback=task_callback)
    assert task_callback.status == TaskStatus.FAILED


@pytest.mark.long_running
def test_setstandbyfpmode_command_not_allowed(
    tango_context, dish_master_device
):
    cm = create_cm(dish_master_device)
    cm.op_state_model.op_state = DevState.FAULT
    with pytest.raises(CommandNotAllowed):
        cm.is_command_allowed("SetStandbyFPMode")
