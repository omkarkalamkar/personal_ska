from time import sleep

from ska_tango_base.control_model import ControlMode, SimulationMode, TestMode
from ska_tmc_common import DishMode, PointingState
from tango import DevState

from ska_tmc_dishleafnode import release
from tests.settings import SLEEP_TIME


def test_attributes(dishln_device):
    sleep(SLEEP_TIME)
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
    assert (
        dishln_device.buildState
        == f"""{release.name},{release.version},
            {release.description}"""
    )
    assert dishln_device.dishMode == DishMode.UNKNOWN
    assert dishln_device.pointingState == PointingState.NONE
