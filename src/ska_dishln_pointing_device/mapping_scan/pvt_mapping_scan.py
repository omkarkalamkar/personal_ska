"""Module for generating program track table for position velocity
time mappiing scans"""

from __future__ import annotations

import operator
import sched
import threading
import time
from datetime import datetime, timedelta
from logging import Logger

from astropy.time import Time

# pylint: disable=unused-import
from ska_trajectory.cubic_hermite_trajectory import (  # noqa: F401
    CubicHermiteTrajectory,
)

# pylint: enable=unused-import
from ska_trajectory.trajectory import TrajectoryName

from ska_dishln_pointing_device.mapping_scan.mapping import BaseScanMapping
from ska_tmc_dishleafnode.az_el_converter import (
    AzElConverter_v2 as AzElConverter,
)
from ska_tmc_dishleafnode.constants import FIRST_PROGRAM_TRACK_TABLE_SIZE
from ska_tmc_dishleafnode.manager.program_track_table_calculator import (
    ProgramTrackTableCalculator,
)


class PositionVelocityTimeMappingScan(BaseScanMapping):
    """
    PositionVelocityTimeMappingScan class inherits from BaseScanMapping class.
    It is used to generate program track table for scans like Mattieu pattern.
    """

    def __init__(
        self,
        pattern_name: str,
        component_manager,
        logger: Logger,
    ):
        """
        Initialize the PositionVelocityTimeMappingScan object.
        :param pattern_name (str): The name of the pattern.
        :param component_manager: An object for managing components.
        :param logger (object, optional): An object for logging.
        """
        super().__init__(
            pattern_name=pattern_name,
            component_manager=component_manager,
            logger=logger,
        )
        self.time_offsets = []
        self.trajectory_attrs = {}
        self.cadence = 0.0
        self.trajectory_name = ""
        self.pvt_object = None
        self.track_table_thread = None
        self.track_thread_lock = self.component_manager.track_thread_lock
        self.mapping_scan_event = self.component_manager.mapping_scan_event
        self.converter = AzElConverter(self.component_manager)
        self.track_table_calculator = ProgramTrackTableCalculator(
            self.component_manager, self.logger
        )
        self.track_table_scheduler = sched.scheduler(time.time, time.sleep)
        self.extended_time = 0.0
        self.program_track_table_size = (
            self.component_manager.program_track_table_size * 3
        )

    def set_target_and_start_process(self):
        """
        Set the target and start process for the scan.
        """
        self.logger.info("Setting target and start process for the scan.")
        self.converter.create_antenna_obj()
        self.logger.debug(
            "Antenna object created for %s",
            self.component_manager.dishln_pointing_device_name,
        )
        self.build_data_for_observation()
        (
            self.component_manager.projection_name,
            self.component_manager.projection_alignment,
        ) = self.get_projection()
        self.set_trajectory_data()
        self.pvt_object = TrajectoryName[self.trajectory_name](
            **self.trajectory_attrs
        )
        self.cadence = self.time_offsets[1] - self.time_offsets[0]
        self.start_track_table_calculation()

    def set_trajectory_data(self):
        """
        Set the trajectory data for the scan.
        """
        self.logger.info("Setting trajectory data for the scan.")
        self.time_offsets = self.get_time_offsets()
        self.trajectory_attrs = self.get_trajectory_attrs()
        self.trajectory_name = self.component_manager.trajectory_name

    def get_time_offsets(self):
        """
        Get the time offsets for the scan.
        :return: A list of time offsets.
        """
        time_offsets = (
            self.component_manager.target_data.get("pointing", {})
            .get("trajectory", {})
            .get("attrs", {})
            .get("time_offsets", [])
        )
        if not time_offsets:
            self.logger.exception("Time offsets not found in target data")
            raise ValueError("Time offsets not found in target data")
        return time_offsets

    def get_trajectory_attrs(self):
        """
        Get the trajectory attributes for the scan.
        :return: A dictionary of trajectory attributes.
        """
        trajectory_attrs = (
            self.component_manager.target_data.get("pointing", {})
            .get("trajectory", {})
            .get("attrs", {})
        )
        if not trajectory_attrs:
            self.logger.exception(
                "Trajectory attributes not found in target data"
            )
            raise ValueError("Trajectory attributes not found in target data")
        return trajectory_attrs

    def start_track_table_calculation(self) -> None:
        """This method creates and starts a thread for the programTrackTable
        calculation."""

        try:
            # Stop existing thread if alive
            self.component_manager.stop_track_table_thread()
            with self.track_thread_lock:
                # added condition for edge case where tracktable start
                # and stop are running parallely.
                if not self.component_manager.stop_track_called.is_set():
                    # clear mapping scan event to start new thread
                    self.mapping_scan_event.clear()
                    self.create_track_table_thread()
                    self.track_table_thread.start()

        except Exception as exception:
            self.logger.exception(
                "Failed to start trackTable thread" + " due to exception: %s",
                str(exception),
            )

    def create_track_table_thread(self) -> None:
        """This creates thread for track table calculation."""
        try:
            self.track_table_thread = threading.Thread(
                target=self.track_thread
            )
        except Exception as exception:
            self.logger.exception(
                "Failed to create trackTable thread "
                + " due to exception: %s ",
                str(exception),
            )

    # pylint: disable=line-too-long
    def track_thread(self) -> None:
        """
        This method manages calculation and writing of programTrackTable
        attribute on DishMaster at the required frequency.

        :return: None
        :rtype: None
        """
        try:
            pre_entries_of_ptt_in_schedular = (
                self.component_manager.entries_tt_schedular_queue
            )
            ptt_buffer_set = False
            time_offsets = self.time_offsets.copy()
            RaDec_AzEl_conversion_time = 0.02
            time_to_add: float = (
                operator.mul(
                    FIRST_PROGRAM_TRACK_TABLE_SIZE, RaDec_AzEl_conversion_time
                )
                + self.component_manager.track_table_advance_sec
            )
            utc_now = datetime.utcnow()
            self.extended_time = utc_now + timedelta(seconds=time_to_add)
            event_priority: int = 1
            program_track_table: list = self.calculate_program_track_table(
                time_offsets=time_offsets,
                ptt_buffer_set=ptt_buffer_set,
                program_track_table_size=FIRST_PROGRAM_TRACK_TABLE_SIZE * 3,
            )
            if program_track_table:
                scheduled_time = (
                    self.track_table_calculator.build_scheduled_time(
                        program_track_table[0]
                    )
                )
                # pylint: disable=line-too-long
                self.track_table_calculator.add_program_track_table_in_schedular(  # noqa: E501
                    track_table_scheduler=self.track_table_scheduler,
                    event_priority=event_priority,
                    scheduled_time=scheduled_time,
                    program_track_table=program_track_table,
                    update_pointing_program_track_table=(
                        # pylint: disable=line-too-long
                        self.component_manager.update_pointing_program_track_table  # noqa: E501
                    ),
                )
                pre_entries_of_ptt_in_schedular -= 1
            else:
                self.logger.error(
                    "Initial program track table calculation failed."
                    " No entries to schedule."
                )
                raise ValueError(
                    "Initial program track table calculation failed."
                )
            while not self.mapping_scan_event.is_set():
                self.logger.info(
                    "Target used to calculate trackTable: %s "
                    "with thread id: %s",
                    self.component_manager.target,
                    threading.get_native_id(),
                )
                program_track_table: list = self.calculate_program_track_table(
                    time_offsets=time_offsets,
                    ptt_buffer_set=ptt_buffer_set,
                    program_track_table_size=(self.program_track_table_size),
                )
                if program_track_table:
                    scheduled_time = (
                        self.track_table_calculator.build_scheduled_time(
                            program_track_table[0]
                        )
                    )
                    with self.track_thread_lock:
                        if not self.mapping_scan_event.is_set():
                            if pre_entries_of_ptt_in_schedular > 0:
                                pre_entries_of_ptt_in_schedular -= 1
                            else:
                                ptt_buffer_set = True
                            # pylint: disable=line-too-long
                            self.track_table_calculator.add_program_track_table_in_schedular(  # noqa: E501
                                # pylint: disable=line-too-long
                                track_table_scheduler=self.track_table_scheduler,  # noqa: E501
                                event_priority=event_priority,
                                scheduled_time=scheduled_time,
                                program_track_table=program_track_table,
                                update_pointing_program_track_table=(
                                    # pylint: disable=line-too-long
                                    self.component_manager.update_pointing_program_track_table  # noqa: E501
                                ),
                            )
                else:
                    while self.track_table_scheduler.queue:
                        self.track_table_scheduler.run(blocking=False)
                        time.sleep(0.5)
                    self.logger.info(
                        "Waiting to finish the scheduled PTT entries."
                    )
                if not self.track_table_scheduler.queue:
                    self.logger.info(
                        "No entries in scheduler queue. Stopping the "
                        "trackTable calculation."
                    )
                    break
        except Exception as exception:
            self.logger.exception(
                "Track thread failed to run due to exception: %s ",
                str(exception),
            )

    def calculate_program_track_table(
        self, time_offsets, ptt_buffer_set, program_track_table_size
    ) -> list:
        """
        This method calculates the program track table using the
        ProgramTrackTableCalculator class.

        :param time_offsets: A list of time offsets.
        :param ptt_buffer_set: A boolean indicating whether the PTT buffer is
            set.
        :rtype: list
        """
        try:
            program_track_table = []
            while (
                len(program_track_table) < program_track_table_size
                and time_offsets
            ):
                time_offset = time_offsets.pop(0)
                timestamp = self.extended_time + timedelta(seconds=time_offset)
                timestamp_time_obj = Time(timestamp, scale="utc")
                tai_time = self.track_table_calculator.convert_utc_to_tai(
                    timestamp_time_obj
                )
                (
                    self.component_manager.fixed_x_offset,
                    self.component_manager.fixed_y_offset,
                    _,
                    _,
                    _,
                ) = self.pvt_object.posn(time_offset)
                # pylint: disable=unbalanced-tuple-unpacking
                az, el = self.converter.point(timestamp)
                # pylint: disable=line-too-long
                if not self.track_table_calculator._is_elevation_within_mechanical_limits(  # noqa: E501
                    el
                ):
                    self.logger.error(
                        "Elevation %s not within mechanical limits set to dish"
                        " leaf node. Program track table will not be "
                        " calculated further.",
                        el,
                    )
                    # pylint: disable=line-too-long
                    self.component_manager.update_program_track_table_error_callback(  # noqa: E501
                        f"Elevation {el} not within mechanical limits"
                        " set to dish."
                    )

                else:
                    program_track_table.append(tai_time)
                    az = az + 360 * self.component_manager.wrap_sector
                    program_track_table.extend([round(az, 12), round(el, 12)])
                self.track_table_scheduler.run(blocking=False)
                if (
                    ptt_buffer_set
                    and self.component_manager.mapping_scan_event.wait(
                        self.cadence
                    )
                ):
                    self.logger.debug(
                        "Stopping the ProgramTrackTable calculation."
                    )
                    break
        except Exception as exception:
            self.logger.exception(
                "Failed to calculate program track table due to exception: %s",
                str(exception),
            )
        return program_track_table
