# import json

import pytest
from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DevFactory

from tests.settings import DISHLN_POINTING_DEVICE


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_dishln_pointing_device():
    """Test the dishln pointing device is up and pingable"""

    dishln_pointing_device = DevFactory().get_device(DISHLN_POINTING_DEVICE)
    assert dishln_pointing_device.ping() > 0
    assert dishln_pointing_device.HealthState == HealthState.OK
    assert (
        dishln_pointing_device.dishlnPointingDeviceFqdn
        == DISHLN_POINTING_DEVICE
    )
    result_code, message = dishln_pointing_device.GenerateProgramTrackTable()
    assert result_code == [ResultCode.STARTED]
    assert message == ['ProgramTrackTable generation started']

    result_code, message = dishln_pointing_device.StopProgramTrackTable()
    assert result_code == [ResultCode.OK]
    assert message == ["Command Completed"]

    result_code, message = dishln_pointing_device.ChangePointingData(
        "trajectory"
    )
    assert result_code == [ResultCode.OK]
    assert message == ["offset change event set"]
