"""Class for programTrackTable calculator."""
import datetime
from concurrent.futures import ThreadPoolExecutor
from logging import Logger

from astropy.time import Time

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.constants import SKA_EPOCH


class ProgramTrackTableCalculator:
    """Class for programTrackTableCalculator"""

    def __init__(self, component_manager, logger: Logger) -> None:
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
        self.track_table_time_stamp = None
        self.track_table_start_time = None

    def calculate_program_track_table(
        self, ra_value: str, dec_value: str, azel_converter: AzElConverter
    ) -> list:
        """This method calculates programTrackTable.

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
            time_stamp_list, tai_timestamp_list = self.calculate_time_stamp_list()
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
        """Check if elevation is within mechanical limit.

        Args:
            el_value (string): Elevation of the target.
        :return (bool): False if elevation is within the limit.
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

    def calculate_time_stamp_list(self) -> tuple:
        """
        This methods calculates an list of requested timestamps
        (TrackTableEntries) with a requested time difference
        (PointingCalculationPeriod) and corresponding list of time
        in TAI format.

        :return (tuple): Tuple with list of timestamps (UTC) in string format and
            timestamp in TAI format
        """
        self.track_table_start_time = self.track_table_time_stamp.timestamp()
        time_stamp_list = []
        tai_timestamp_list = []
        for _ in range(self.component_manager.track_table_entries):
            timestamp_sec = self.track_table_time_stamp.timestamp()
            timestamp_str = self.convert_timestamp(timestamp_sec)
            time_stamp_list.append(timestamp_str)

            tai_time = self.convert_utc_to_tai(timestamp_sec)
            tai_timestamp_list.append(tai_time)

            self.track_table_time_stamp = self.track_table_time_stamp + datetime.timedelta(
                milliseconds=self.component_manager.pointing_calculation_period
            )
        return time_stamp_list, tai_timestamp_list

    def point(self, timestamp: str) -> list:
        """This method converts Target RaDec coordinates to the AzEl
        coordinates. It is called continuously from Configure command (in a thread)
        at interval of 50ms till the StopTrack command is invoked.

        Args:
            timestamp(str): utc timestamp in string format
        Return:
            az_el_coordinates (list)
        """
        return self.azel_converter.radec_to_azel(
            self.right_ascension, self.declination, timestamp, self.weather_data
        )

    def convert_utc_to_tai(self, utc_time: float) -> float:
        """
        This method converts utc time to tai format time.
        :param: utc_time: time in utc (seconds)
        :returns: time in TAI format (seconds)
        """
        ska_epoch_utc = Time(SKA_EPOCH, scale="utc")
        return utc_time - ska_epoch_utc.unix_tai

    def convert_timestamp(self, timestamp_seconds: float) -> str:
        """Converts the floating point timestamp in seconds to a utc
        timestamp with format -> %Y-%m-%d %H:%M:%S

        :param timestamp_seconds: Input timestamp with time in seconds
        :type timestamp_seconds: float

        :returns: Timestamp in string with format "%Y-%m-%d %H:%M:%S".
        """
        timestamp = datetime.datetime.utcfromtimestamp(timestamp_seconds).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return timestamp
