from ska_tango_base.commands import ResultCode


# Added unit test cases for tango device class
def test_setstandbyfpmode_command(dishln_device):
    result_code, _ = dishln_device.SetStandbyFPMode()
    assert result_code[0] == ResultCode.QUEUED


def test_setstandbylpmode_command(dishln_device):
    result_code, _ = dishln_device.SetStandbyLPMode()
    assert result_code[0] == ResultCode.QUEUED
