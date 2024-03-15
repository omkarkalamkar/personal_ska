"""Class for programTrackTable calculator."""
import datetime
import time


class ProgramTrackTableCalculator:
    """Class for programTrackTableCalculator"""

    def __init__(self, component_manager, logger) -> None:
        """Init method"""
        self.component_manager = component_manager
        self.logger = logger

    def calculate_program_track_table(self, ra_value: str, dec_value: str, azel_converter) -> list:
        """This method calculates programTrackTable.
        Example of TrackTable:
        [TAI1, Az1, El1, TAI2, Az2, El2,,,,,,TAIn, Azn, Eln]
        Args:
            ra_value (str): RA value in hours:minutes:sec
            dec_value (str): Dec Value in degree:arc_minutes:arc_sec
        """
        program_track_table = []
        for _ in range(self.component_manager.track_table_entries):
            utc_timestamp = self.component_manager.extended_time.timestamp() * 1000
            timestamp = self.component_manager.convert_timestamp(utc_timestamp)
            #######################################################
            az_value, el_value = azel_converter.point(ra_value, dec_value, timestamp)
            #######################################################
            if not self._is_elevation_within_mechanical_limits(el_value):
                time.sleep(self.component_manager.pointing_calculation_period)
                continue
            if az_value < 0:
                az_value = 360 - abs(az_value)
            if self.component_manager.event_track_time.is_set():
                log_message = (
                    "Stop the Thread as event track time is set: "
                    f"{self.component_manager.event_track_time.is_set()}"
                )
                self.logger.debug(log_message)
                break

            program_track_table.append(utc_timestamp)
            program_track_table.append(round(az_value, 12))
            program_track_table.append(round(el_value, 12))

            self.component_manager.extended_time = (
                self.component_manager.extended_time
                + datetime.timedelta(
                    milliseconds=self.component_manager.pointing_calculation_period
                )
            )
            time.sleep(0.00005)
        return program_track_table

    def _is_elevation_within_mechanical_limits(
        self,
        el_value: float,
    ):
        """Check if elevation is within mechanical limit
        Args:
            el_value: string
        Return:
            bool
        """

        if (
            not self.component_manager.elevation_min_limit
            <= el_value
            <= self.component_manager.elevation_max_limit
        ):
            self.elevation_limit = True
            self.logger.info(
                "Minimum/maximum elevation limit has been reached."
                + " Source is not visible currently."
            )
            return False

        self.elevation_limit = False
        return True
