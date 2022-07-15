import time

import pytest
from ska_tango_base.commands import TaskStatus
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_dishleafnode.commands.setstandbyfpmode_command import (
    SetStandbyFPMode,
)
from tests.mock_callable import MockCallable
from tests.settings import create_cm, logger


@pytest.mark.long_running
def test_setstandbyfpmode_command(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    adapter_factory = HelperAdapterFactory()

    setstandbyfpmode_command = SetStandbyFPMode(
        cm, cm.op_state_model, adapter_factory, logger
    )
    assert setstandbyfpmode_command.check_allowed()
    unique_id = f"{time.time()}_SetStandbyFPMode"
    task_callback = MockCallable(unique_id)

    task_status, _ = cm.setstandbyfpmode(
        setstandbyfpmode_command, task_callback=task_callback
    )
    assert task_status == TaskStatus.QUEUED
    assert task_callback.status == TaskStatus.QUEUED
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.COMPLETED
    adapter = adapter_factory.get_or_create_adapter(dish_master_device)
    adapter.proxy.SetStandbyFPMode.assert_called_once_with()


@pytest.mark.long_running
def test_setstandbyfpmode_command_exception(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    adapter_factory = HelperAdapterFactory()

    adapter_factory.get_or_create_adapter(
        dish_master_device, attrs={"SetStandbyFPMode.side_effect": Exception}
    )
    setstandbyfpmode_command = SetStandbyFPMode(
        cm, cm.op_state_model, adapter_factory, logger
    )
    assert setstandbyfpmode_command.check_allowed()
    unique_id = f"{time.time()}_SetStandbyFPMode"
    task_callback = MockCallable(unique_id)

    cm.setstandbyfpmode(setstandbyfpmode_command, task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.FAILED
    failed_message = "The invocation of the SetStandbyFPMode command is failed"
    assert failed_message in task_callback.exception


@pytest.mark.long_running
def test_setstandbyfpmode_command_adapter_none(
    tango_context, dish_master_device
):
    cm = create_cm(dish_master_device)

    setstandbyfpmode_command = SetStandbyFPMode(cm, cm.op_state_model, logger)
    assert setstandbyfpmode_command.check_allowed()
    unique_id = f"{time.time()}_SetStandbyFPMode"
    task_callback = MockCallable(unique_id)

    cm.setstandbyfpmode(setstandbyfpmode_command, task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.FAILED
    failed_message = "Adapter is None"
    assert failed_message in task_callback.exception
