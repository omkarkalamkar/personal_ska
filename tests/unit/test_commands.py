from ska_tango_base.commands import ResultCode


def test_setstandbyfpmode_command(dishln_device):
    result_code, _ = dishln_device.SetStandbyFPMode()
    assert result_code[0] == ResultCode.QUEUED
