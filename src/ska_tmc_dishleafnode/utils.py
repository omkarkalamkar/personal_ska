"""Utility module"""
import logging
import math

logger = logging.getLogger(__name__)


def dd_to_dms(argin):  # pylint: disable=inconsistent-return-statements
    """
    Converts a number in degree decimal to Deg:Min:Sec.

    :param argin: A number in decimal degrees.
        Example: 30.7129252
    :return: Number in deg:min:sec format.
        Example: 30:42:46.5307 is returned value for input 30.7129252.
    """
    try:
        sign = 1
        if argin < 0:
            sign = -1
        frac_min, degrees = math.modf(abs(argin))
        frac_sec, minutes = math.modf(frac_min * 60)
        seconds = frac_sec * 60
        return f"{int(degrees * sign)}:{int(minutes)}:{round(seconds, 4)}"
    except SyntaxError as error:
        log_msg = (
            f"Error while converting decimal degree to dig:min:sec.{error}"
        )
        logger.error(log_msg)
