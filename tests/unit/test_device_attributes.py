import pytest
from ska_tango_base.control_model import ControlMode, SimulationMode, TestMode
from tango import DevState

from ska_tmc_dishleafnode import release


@pytest.mark.dishln
def test_attributes(dishln_device):
    assert dishln_device.State() == DevState.ON
    dishln_device.loggingTargets = ["console::cout"]
    assert "console::cout" in dishln_device.loggingTargets
    dishln_device.testMode = TestMode.NONE
    assert dishln_device.testMode == TestMode.NONE
    dishln_device.simulationMode = SimulationMode.FALSE
    assert dishln_device.simulationMode == SimulationMode.FALSE
    dishln_device.controlMode = ControlMode.REMOTE
    assert dishln_device.controlMode == ControlMode.REMOTE
    dishln_device.dishMasterDevName = "dishmaster"
    assert dishln_device.dishMasterDevName == "dishmaster"
    assert dishln_device.versionId == release.version
    assert dishln_device.buildState == (
        "{},{},{}".format(release.name, release.version, release.description)
    )
