import logging
import math

import pytest
from astropy import units as u
from astropy.coordinates import Angle, SkyCoord
from ska_tmc_common.exceptions import ConversionError

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.manager import DishLNComponentManager

logger = logging.getLogger(__name__)


def degree_to_degree_minute_seconds(argin: float) -> str:
    """
    Converts a number in degree decimal to Deg:Min:Sec.

    :param argin: A number in decimal degrees.
        Example: 30.7129252
    :return: Number in deg:min:sec format.
        Example: 30:42:46.5307 is returned value for input 30.7129252.
    """
    dms_str = ""  # degree:minutes:seconds
    try:
        sign = 1
        if argin < 0:
            sign = -1
        fraction_min, degrees = math.modf(abs(argin))
        fraction_sec, minutes = math.modf(fraction_min * 60)
        seconds = fraction_sec * 60
        dms_str = f"{int(degrees * sign)}:{int(minutes)}:{round(seconds, 2)}"
    except Exception as error:
        logger.error(
            "Error while converting decimal degree to deg:min:sec -> %s",
            error,
        )
        raise ConversionError(
            f"Error while converting {argin} to Degree:Minutes:Seconds"
        ) from error
    return str(dms_str)


@pytest.mark.parametrize(
    "ra, dec, timestamp",
    [
        pytest.param("16:29:24.46", "-26:25:55.7", "2019-02-19 06:01:00"),
        pytest.param("18:36:56.49", "38:47:07.8", "2019-02-19 05:47:08"),
        pytest.param("22:50:52.23", "18:00:07.7", "2019-03-06 07:00:00"),
    ],
)
@pytest.mark.r1
def test_pointing_calculations(ra: str, dec: str, timestamp: str):
    """Function to test AzEl conversion"""

    dish_dev_name = "ska001/dish/master"
    logger = logging.getLogger(__name__)
    component_manager = DishLNComponentManager(logger=logger, dish_dev_name=dish_dev_name)

    # Below steps does forward transform
    pointing_calc = AzElConverter(component_manager)
    pointing_calc.create_antenna_obj()
    azel = pointing_calc.point(ra, dec, timestamp)

    # Below steps does forward transform
    refraction_angle = Angle(azel[1], u.deg)
    ra_dec = pointing_calc.backward_transform(azel[0], refraction_angle.rad, timestamp=timestamp)

    # Below steps will create an skycoord object in icrs frame for the provided Ra, Dec values
    Ra_angle = Angle(ra, u.hourangle)
    Dec_angle = Angle(dec, u.deg)
    given_ra_dec_in_icrs_frame = SkyCoord(Ra_angle, Dec_angle, frame="icrs")

    # Below steps does the validation
    converted_ra_angle = Angle(ra_dec[0], u.deg)
    converted_dec_angle = Angle(ra_dec[1], u.deg)
    converted_ra_dec = SkyCoord(converted_ra_angle, converted_dec_angle, frame="icrs")
    given_ra = given_ra_dec_in_icrs_frame.ra.to_string(u.rad, precision=5)
    given_dec = given_ra_dec_in_icrs_frame.dec.to_string(u.rad, precision=4)
    converted_ra = converted_ra_dec.ra.to_string(u.rad, precision=5)
    converted_dec = converted_ra_dec.dec.to_string(u.rad, precision=4)
    assert given_ra == converted_ra
    assert given_dec == converted_dec
