import json
from enum import IntEnum, unique

from ska_tmc_common.device_info import DeviceInfo
from ska_tmc_common.enum import PointingState


@unique
class DishMode(IntEnum):
    UNKNOWN = 0
    OFF = 1
    STARTUP = 2
    SHUTDOWN = 3
    STANDBY_LP = 4
    STANDBY_FP = 5
    STOW = 6
    CONFIG = 7
    OPERATE = 8
    MAINTENANCE = 9
    FORBIDDEN = 10
    ERROR = 11


class DishDeviceInfo(DeviceInfo):
    def __init__(self, dev_name, _unresponsive=False):
        super().__init__(dev_name, _unresponsive)
        self.id = -1
        self.pointingState = PointingState.NONE
        self.dishMode = DishMode.UNKNOWN
        self.rxCapturingData = 0
        self.achievedPointing = []
        self.desiredPointing = []

    def from_dev_info(self, devInfo):
        super().from_dev_info(devInfo)
        if isinstance(devInfo, DishDeviceInfo):
            self.id = devInfo.id
            self.pointingState = devInfo.pointingState
            self.dishMode = devInfo.dishMode
            self.rxCapturingData = devInfo.rxCapturingData
            self.achievedPointing = devInfo.achievedPointing
            self.desiredPointing = devInfo.desiredPointing

    def __eq__(self, other):
        if isinstance(other, DishDeviceInfo) or isinstance(other, DeviceInfo):
            return self.dev_name == other.dev_name
        else:
            return False

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
        super_dict = super().to_dict()
        super_dict["id"] = self.id
        super_dict["pointingState"] = str(PointingState(self.pointingState))
        super_dict["dishMode"] = str(DishMode(self.dishMode))
        super_dict["rxCapturingData"] = self.rxCapturingData
        super_dict["achievedPointing"] = self.achievedPointing
        super_dict["desiredPointing"] = self.desiredPointing
        return super_dict
