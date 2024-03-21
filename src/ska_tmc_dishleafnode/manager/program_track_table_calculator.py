"""Class for programTrackTable calculator."""
import datetime
from concurrent.futures import ThreadPoolExecutor

from astropy.time import Time

from ska_tmc_dishleafnode.constants import SKA_EPOCH


class ProgramTrackTableCalculator:
    """Class for programTrackTableCalculator"""

    def __init__(self, component_manager, logger) -> None:
        """
        Init method for ProgramTrackTableCalculator class.

        param: component_manager: Dish Leaf Node component manager object
        param: logger: logger

        :return: None
        """
        self.component_manager = component_manager
        self.logger = logger
        self.right_ascension = None
        self.declination = None
        self.weather_data = None
        self.azel_converter = None

    def calculate_program_track_table(self, ra_value: str, dec_value: str, azel_converter) -> list:
        """This method calculates programTrackTable.
        Example of TrackTable:
        [TAI1, Az1, El1, TAI2, Az2, El2,,,,,,TAIn, Azn, Eln]
        Args:
            ra_value (str): RA value in hours:minutes:sec
            dec_value (str): Dec Value in degree:arc_minutes:arc_sec

        :return: list in the form of [TAI1, Az1, El1, TAI2, Az2, El2,,,,,,TAIn, Azn, Eln]
        """
        self.right_ascension = ra_value
        self.declination = dec_value
        self.azel_converter = azel_converter
        self.weather_data = self.azel_converter.weather_data
        program_track_table = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            time_stamp_list, tai_timestamp_list = self.calculate_time_stamp_array()
            results = executor.map(self.point, time_stamp_list)
            for result in results:
                if not self._is_elevation_within_mechanical_limits(result[1]):
                    tai_timestamp_list.pop(0)
                    continue
                if result[0] < 0:
                    result[0] = 360 - abs(result[0])

                program_track_table.append(tai_timestamp_list.pop(0))
                program_track_table.extend([round(result[0], 12), round(result[1], 12)])

                if self.component_manager.event_track_time.is_set():
                    log_message = (
                        "Stop the Thread as event track time is set: "
                        f"{self.component_manager.event_track_time.is_set()}"
                    )
                    self.logger.debug(log_message)
                    break
        return program_track_table

    def _is_elevation_within_mechanical_limits(
        self,
        el_value: float,
    ) -> bool:
        """Check if elevation is within mechanical limit
        Args:
            el_value: string
        :return:
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

    def calculate_time_stamp_array(self) -> list:
        """
        This methods calculates an array of number of requested timestamps
        (TrackTableEntries) with a requested time difference
        (PointingCalculationPeriod).

        :return: An array of timestamps (list)
        """
        ska_epoch_utc = Time(SKA_EPOCH, scale="utc")
        time_stamp_array = []
        tai_timestamp_array = []
        for _ in range(self.component_manager.track_table_entries):
            utc_timestamp = self.component_manager.extended_time.timestamp() * 1000
            timestamp = self.component_manager.convert_timestamp(utc_timestamp)

            # Calculate tai time, answer is in seconds
            TAI_time = (utc_timestamp / 1000) - ska_epoch_utc.unix_tai
            tai_timestamp_array.append(TAI_time)
            time_stamp_array.append(timestamp)
            self.component_manager.extended_time = (
                self.component_manager.extended_time
                + datetime.timedelta(
                    milliseconds=self.component_manager.pointing_calculation_period
                )
            )

        return time_stamp_array, tai_timestamp_array

    def point(self, timestamp: str) -> list:
        """This method converts Target RaDec coordinates
        to the AzEl coordinates.It is called continuously
        from Track command (in a thread) at interval
        of 50ms till the StopTrack command is invoked.
        Args:
            timestamp(str): utc timestamp in string format
        Return:
            az_el_coordinates (list)
        """
        return self.azel_converter.radec_to_azel(
            self.right_ascension, self.declination, timestamp, self.weather_data
        )
