"""Generic trajectory factory and imports for mapping scans processing."""

from enum import Enum

from ska_trajectory.cubic_hermite_trajectory import CubicHermiteTrajectory
from ska_trajectory.trajectory import Trajectory  # noqa: F401


class TrajectoryNotImplementedError(Exception):
    """Exception raised when a trajectory is not implemented."""


class TrajectoryName(str, Enum):
    """Enum for trajectory names."""

    FIXED = "fixed"
    POS_VEL_TIME = "pos_vel_time"


# Mapping between name → class
TRAJECTORY_MAP = {
    TrajectoryName.FIXED: Trajectory,
    TrajectoryName.POS_VEL_TIME: CubicHermiteTrajectory,
}


def create_trajectory(name: str, **attrs):
    """
    Factory method to create trajectory instance
    """
    traj_name = TrajectoryName(name)

    if traj_name in TRAJECTORY_MAP:
        traj_cls = TRAJECTORY_MAP[traj_name]
    else:
        raise TrajectoryNotImplementedError(
            f"Unsupported trajectory name: {name}"
        )
    return traj_cls(**attrs)
