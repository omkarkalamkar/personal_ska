import pytest
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.abort_command import AbortCommands
from tests.settings import logger


@pytest.mark.test1
def test_abort_command(tango_context, cm):
    logger.info("%s", tango_context)
    abort_command = AbortCommands(cm, logger=logger)
    result_code, message = abort_command.do()
    assert result_code == ResultCode.OK
    assert message == "Command Completed"
