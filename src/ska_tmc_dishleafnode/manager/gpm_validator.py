"""
This module provides GPM (Global Pointing Model) validation functionality
for the Dish Leaf Node.
"""

import json
import re
from logging import Logger
from typing import Tuple

import numpy as np
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands import ApplyPointingModel
from ska_tmc_dishleafnode.constants import DISH_BANDPARAMS


class GPMValidator:
    """
    Handles Global Pointing Model (GPM) validation operations for the
    Dish Leaf Node.

    This class encapsulates GPM version management, validation, and
    application operations.
    """

    def __init__(self, component_manager, logger: Logger):
        """
        Initialize the GPM Validator.

        Args:
            component_manager: Reference to the DishLNComponentManager
            instance.
            logger (Logger): Logger instance for logging operations.
        """
        self.component_manager = component_manager
        self.logger = logger

    def gpm_validation_update(self, band: str, result_code: str):
        """Update the GPM validation result.

        Args:
            band(str): Band name.
            result_code(str): Validation result code.
        """
        callback = (
            self.component_manager.handle_update_gpm_validation_result_callback
        )
        if callback:
            callback(band, result_code)

    def get_band_info(self, band_name: str) -> Tuple[str | None, str | None]:
        """Get GPM version and band name for the given band.

        Args:
            band_name(str): The band name to look up.

        Returns:
            Tuple of (gpm_version, band_found). Both are None if band
            not found.
        """
        gpm_version_for_given_band = None
        band_found = None
        try:
            match = re.search(r'band(\d+[ab]?)', band_name.lower())
            band_found = f"Band_{match.group(1)}"
            gpm_version_for_given_band = self.component_manager.gpm_version[
                band_found
            ]
            self.logger.debug(
                "GPM version: %s, band: %s",
                gpm_version_for_given_band,
                band_found,
            )
        except Exception as e:
            self.logger.exception(
                "Exception for band %s occurred during GPM validation: %s",
                band_name,
                e,
            )
        return gpm_version_for_given_band, band_found

    def validate_gpm_version(
        self,
        dish_param: list,
        gpm_version_for_given_band: str,
        band_found: str,
    ) -> None:
        """Validate GPM version against dish parameters.

        Args:
            dish_param(ndarray): Dish pointing model parameters.
            gpm_version_for_given_band(str): GPM version for the band.
            band_found(str): The band name found.
        """
        try:
            ordered_keys = [
                'IA',
                'CA',
                'NPAE',
                'AN',
                'AN0',
                'AW',
                'AW0',
                'ACEC',
                'ACES',
                'ABA',
                'ABphi',
                'IE',
                'ECEC',
                'ECES',
                'HECE4',
                'HESE4',
                'HECE8',
                'HESE8',
            ]
            apm_cmd_obj = ApplyPointingModel(
                self.component_manager,
                self.component_manager.op_state_model,
                self.component_manager.adapter_factory,
                self.logger,
            )
            tm_source_path = (
                self.component_manager.gpm_source_path
                + '?'
                + gpm_version_for_given_band
                + '#tmdata'
            )
            tm_file_path = (
                self.component_manager.gpm_file_path + band_found + '.json'
            )
            self.logger.debug(
                "Stored TMDATA paths %s, %s", tm_source_path, tm_file_path
            )
            apm_json, message = apm_cmd_obj.get_global_pointing_data_json(
                [tm_source_path],
                tm_file_path,
            )
            self.logger.debug(
                "Downloaded GPM Json %s for %s", apm_json, band_found
            )
            if message:
                self.logger.error(
                    "GPM validation failed. GPM version '%s' for '%s' "
                    "of dish. Error: %s",
                    gpm_version_for_given_band,
                    DISH_BANDPARAMS[band_found],
                    message,
                )
                self.gpm_validation_update(band_found, ResultCode.FAILED.name)
                return
            band_params = [
                apm_json['coefficients'][key]['value'] for key in ordered_keys
            ]
            band_params = np.array(band_params, dtype=np.float32)
            if not np.allclose(band_params, dish_param):
                self.logger.error(
                    "GPM version '%s' band not matched with '%s' of dish.",
                    gpm_version_for_given_band,
                    DISH_BANDPARAMS[band_found],
                )
                self.logger.debug(
                    "Dish GPM: %s, DishLeafNode GPM: %s",
                    dish_param,
                    band_params,
                )
                self.gpm_validation_update(band_found, ResultCode.FAILED.name)
            else:
                self.gpm_validation_update(band_found, ResultCode.OK.name)
                self.logger.debug(
                    "GPM version '%s' band params matched with '%s' of dish.",
                    gpm_version_for_given_band,
                    DISH_BANDPARAMS[band_found],
                )
        except Exception as e:
            self.gpm_validation_update(band_found, ResultCode.FAILED.name)
            self.logger.exception(
                "Exception occurred while GPM validation: %s", e
            )

    def invoke_apm_on_dish(
        self,
        gpm_version_for_given_band: str,
        band_found: str,
    ) -> None:
        """Invoke ApplyPointingModel if GPM is set for the band
        on DLN but not on dish.

        Args:
            gpm_version_for_given_band(str): The GPM version for the band.
            band_found(str): The band name found.
        """
        try:
            if gpm_version_for_given_band != "UNKNOWN":
                gpm_previous_version = self.component_manager.gpm_version.get(
                    band_found
                )

                apm_cmd_obj = ApplyPointingModel(
                    self.component_manager,
                    self.component_manager.op_state_model,
                    self.component_manager.adapter_factory,
                    self.logger,
                )
                tm_source_path = (
                    self.component_manager.gpm_source_path
                    + '?'
                    + gpm_version_for_given_band
                    + '#tmdata'
                )
                tm_file_path = (
                    self.component_manager.gpm_file_path + band_found + '.json'
                )
                result_code, message = apm_cmd_obj.do(
                    json.dumps(
                        {
                            "tm_data_sources": [tm_source_path],
                            "tm_data_filepath": tm_file_path,
                        }
                    )
                )
                if result_code != int(ResultCode.OK):
                    self.gpm_validation_update(
                        band_found, ResultCode.FAILED.name
                    )
                    self.logger.error(
                        "ApplyPointingModel command failed during GPM "
                        "validation on %s and message: %s",
                        self.component_manager.dish_dev_name,
                        message,
                    )
                    self.logger.error(
                        "Band: '%s' and GPM version on DLN: '%s'",
                        DISH_BANDPARAMS[band_found],
                        gpm_version_for_given_band,
                    )
                    self.component_manager.gpm_version[
                        band_found
                    ] = gpm_previous_version
                else:
                    self.logger.debug(
                        "ApplyPointingModel command invoked successfully "
                        "during GPM validation"
                        " on %s for band: %s, version: %s and"
                        " message received is: %s",
                        self.component_manager.dish_dev_name,
                        band_found,
                        gpm_version_for_given_band,
                        message,
                    )
                    self.gpm_validation_update(band_found, ResultCode.OK.name)
            else:
                self.gpm_validation_update(band_found, ResultCode.UNKNOWN.name)
                self.logger.debug(
                    "Invalid GPM version '%s' found during GPM validation, "
                    "can't apply GPM to '%s'",
                    gpm_version_for_given_band,
                    DISH_BANDPARAMS[band_found],
                )
        except Exception as e:
            self.logger.exception(
                "GPM validation failed. Exception occurred while applying "
                "GPM on band: %s for version: %s and exception is %s",
                band_found,
                gpm_version_for_given_band,
                e,
            )
            self.gpm_validation_update(band_found, ResultCode.FAILED.name)

    def update_dish_params_and_validate_gpm(
        self,
        dish_param: list,
        band_name: str,
    ) -> None:
        """Update dish parameters and validate or apply GPM for the band.

        Args:
            dish_param(list): Pointing model parameters.
            band_name(str): Band name to update and validate.
        """
        gpm_version_for_given_band = None
        band_found = None
        band_name = band_name.lower()
        if band_name in self.component_manager.dish_pointing_model_param:
            (
                gpm_version_for_given_band,
                band_found,
            ) = self.get_band_info(band_name)
            self.logger.info(
                "GPM Version for %s %s",
                band_found,
                gpm_version_for_given_band,
            )
            if np.array(dish_param).size > 0 and np.any(dish_param > 0.0):
                if gpm_version_for_given_band == "UNKNOWN":
                    self.gpm_validation_update(
                        band_found, ResultCode.FAILED.name
                    )
                    self.logger.error(
                        "GPM Validation failed. GPM Dish param received: %s",
                        dish_param,
                    )
                    self.logger.error(
                        "GPM version found '%s' for band: '%s'",
                        gpm_version_for_given_band,
                        band_found,
                    )
                else:
                    self.validate_gpm_version(
                        dish_param, gpm_version_for_given_band, band_found
                    )
            elif np.all(dish_param == 0.0) or not np.array(dish_param).size:
                self.invoke_apm_on_dish(gpm_version_for_given_band, band_found)
            self.component_manager.dish_pointing_model_param[
                band_name
            ] = json.dumps(dish_param.tolist())
            self.logger.debug(
                f"Dish parameter: {band_name} updated to {dish_param}."
            )
        else:
            self.logger.error(
                f"Band name '{band_name}' not found in parameters."
            )
            return

        if self.component_manager._update_dish_pointing_model_param:
            self.component_manager._update_dish_pointing_model_param(
                self.component_manager.dish_pointing_model_param
            )
        self.component_manager.update_gpm_data_for_health_aggregation()
