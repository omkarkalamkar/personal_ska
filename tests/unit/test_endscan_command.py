import threading
import time

import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.commands import EndScan
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import (
    DISH_MASTER_DEVICE,
    get_mock_adapter_factory,
    simulate_events_on_dish_device,
)


def test_endscan_command(cm_without_er_lp, task_callback):
    cm = cm_without_er_lp
    command_id = f"{time.time()}_EndScan"
    cm.adapter_factory = get_mock_adapter_factory(command_id)
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_endscan_allowed()
    end_scan = EndScan(cm, cm.op_state_model, cm.adapter_factory, cm.logger)
    simulate_events_on_dish_device(
        cm, [DISH_MASTER_DEVICE], DishMode.OPERATE, cmd_object=end_scan
    )
    end_scan.endscan(
        task_callback=task_callback, task_abort_event=threading.Event()
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        }
    )


def test_endscan_command_adapter_none(cm_without_er_lp, task_callback):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_endscan_allowed()

    cm.endscan(task_callback=task_callback, task_abort_event=threading.Event())

    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(status=TaskStatus.COMPLETED)
    assert ResultCode.FAILED == result["result"][0]
    assert "TRANSIENT_NoUsableProfile" in result["result"][1]


def test_endscan_mode_command_not_allowed(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_endscan_allowed()
