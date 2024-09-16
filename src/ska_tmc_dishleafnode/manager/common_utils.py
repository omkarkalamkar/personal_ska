"""This module provides common utilities for dish leaf node"""
import copy
import json
from typing import Tuple

from ska_tango_base.commands import ResultCode


def update_lrcr_result(
    component_manager,
    event_command_id,
    event_command_result,
    event_command_message,
) -> None:
    """
    This function will update result of longrunningcommandresult attribute
    against a command Id
    """
    component_manager.logger.info(
        f"Working on data event_command_id:{event_command_id}"
        f" event_command_result : {event_command_result}"
    )
    component_manager.logger.debug(
        "command mapping is %s", component_manager.command_mapping
    )
    with component_manager.tango_operation_execution_lock:
        command_dict_ref = {}
        command_dict_ref = copy.deepcopy(component_manager.command_mapping)
        for key, command_dict in command_dict_ref.items():
            # Iterate through the  dictionary for each command Id
            # And add ResultCode , if command has returned ResultCode.OK

            for inner_key, value in command_dict.items():
                if inner_key == "message_or_unique_id":
                    component_manager.logger.info(
                        f"Working on data event_command_id:{event_command_id}"
                    )
                    if value == event_command_id:
                        component_manager.logger.info(
                            f"The value {event_command_id} exists "
                            f"in the dictionary under key '{key}' "
                        )
                        if int(event_command_result) == ResultCode.OK:
                            component_manager.command_mapping.setdefault(
                                key, {}
                            )["ResultCode"] = ResultCode.OK

                        else:
                            component_manager.command_mapping.setdefault(
                                key, {}
                            )["ResultCode"] = event_command_result

                            component_manager.logger.debug(
                                "command mapping is %s",
                                component_manager.command_mapping,
                            )
                            component_manager.logger.info(
                                "setting LRCR callback %s, %s, %s",
                                component_manager.command_id,
                                event_command_result,
                                event_command_message,
                            )
                            component_manager.long_running_result_callback(
                                component_manager.command_id,
                                event_command_result,
                                exception_message=event_command_message,
                            )

                else:
                    component_manager.logger.info(
                        "Message ID does not exists in command mapping"
                    )


def process_long_running_command_result(
    component_manager, lrc_result: Tuple[str, str]
) -> None:
    """
    Method to update task callback based on long running command result
    event data.

    :param lrc_result: longRunningCommandResult attribute event data
    :type: (Tuple[List[str], List[str]])
    """
    component_manager.logger.info(
        "Received longRunningCommandResult event for device: %s, ",
        lrc_result,
    )

    try:
        if not lrc_result:
            return
        with component_manager.lock:
            if lrc_result == ("", ""):
                return

        if lrc_result[0].endswith(component_manager.supported_commands) and (
            component_manager.command_in_progress
            in component_manager.supported_commands
        ):
            component_manager.logger.debug(
                "The command in progress is: %s for processing of "
                + "LRCR event",
                component_manager.command_in_progress,
            )
            command_result, message = json.loads(lrc_result[1])

            component_manager.logger.debug(
                "The command results: %s and message: %s ",
                command_result,
                message,
            )

            update_lrcr_result(
                component_manager, lrc_result[0], command_result, message
            )

    except ValueError:
        component_manager.logger.info(
            f"""Updating LRCRCallback with value: {lrc_result[1]} for
                                    command: {lrc_result[0]}"""
        )

        exception_message = (
            f"Exception occurred for command: {lrc_result[0]}"
            f"{lrc_result[1]}\n"
        )
        component_manager.long_running_result_callback(
            component_manager.command_id,
            ResultCode.FAILED,
            exception_message=exception_message,
        )
