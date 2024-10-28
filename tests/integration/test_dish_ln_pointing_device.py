import pytest
from ska_control_model import HealthState
from ska_tmc_common import DevFactory

from tests.settings import DISHLN_POINTING_DEVICE


@pytest.mark.post_deployment
@pytest.mark.test
def test_dishln_pointing_device(tango_context):
    """Test the dishln pointing device is up and pingable"""

    dishln_pointing_device = DevFactory().get_device(DISHLN_POINTING_DEVICE)
    assert dishln_pointing_device.ping() > 0
    assert dishln_pointing_device.HealthState == HealthState.OK
    assert (
        dishln_pointing_device.dishlnPointingDeviceFqdn
        == DISHLN_POINTING_DEVICE
    )
    assert (
        'Command Completed'
        in dishln_pointing_device.command_inout("generateprogramtracktable")[
            1
        ][0]
    )
