"""Unit tests for Abort command"""
from unittest import mock

from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from ska_tmc_dishleafnode.commands.abort_command import Abort
from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import logger


def test_abort_command(cm_without_er_lp):
    cm = cm_without_er_lp
    attrs = {
        'Abort.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(**attrs)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    abort_command = Abort(cm, cm.op_state_model, cm.adapter_factory, logger)
    abort_command._adapter_factory = adapter_factory
    result_code, message = abort_command.do()
    assert result_code == ResultCode.OK
    assert message == COMMAND_COMPLETION_MESSAGE


def test_cm_abort(cm_without_er_lp, task_callback):
    task_status, message = cm_without_er_lp.abort(task_callback=task_callback)
    assert task_status == TaskStatus.IN_PROGRESS
    assert message == "Aborting tasks"
