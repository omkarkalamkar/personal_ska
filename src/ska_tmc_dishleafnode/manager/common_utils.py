"""This module provides common utilities for dish leaf node"""
import copy

from ska_tango_base.commands import ResultCode


def update_lrcr_result(self, event_command_id, event_command_result) -> None:
    """
    This function will update result of longrunningcommandresult attribute
    against a command Id
    """

    self.logger.info(
        f"Working on data event_command_id:{event_command_id}"
        f" event_command_result : {event_command_result}"
    )
    command_dict_ref = {}
    command_dict_ref = copy.deepcopy(self.command_mapping)
    for key, command_dict in command_dict_ref.items():
        # Iterate through the  dictionary for each command Id
        # And add ResultCode , if command has returned ResultCode.OK

        for inner_key, value in command_dict.items():
            if inner_key == "message_or_unique_id":
                if value == event_command_id:
                    self.logger.info(
                        f"The value {event_command_id} exists "
                        f"in the dictionary under key '{key}' "
                    )
                    if int(event_command_result) == ResultCode.OK:
                        self.command_mapping.setdefault(key, {})[
                            "ResultCode"
                        ] = ResultCode.OK

                    else:
                        self.logger.info(
                            "ResultCode value is %s", event_command_result
                        )

            else:
                self.logger.info(
                    "Message ID does not exists in command mapping"
                )

    self.logger.info("Current command mapping :: %s", self.command_mapping)


def process_long_running_command_result(
    self, device_name: str, value: str
) -> None:
    """
    Method to update task callback based on long running command result
    event data.

    :param lrc_status: longRunningCommandResult attribute event data
    :type: (Tuple[List[str], List[str]])
    """
    self.logger.info(
        "Received longRunningCommandResult event for device: %s, "
        "with value: %s",
        device_name,
        value,
    )

    if self.command_in_progress:
        try:
            if not value[1]:
                pass

            if value[0].endswith(self.supported_commands):
                if int(value[1]) == ResultCode.OK:
                    update_lrcr_result(self, value[0], value[1])

        except ValueError:
            self.logger.info(
                f"""Updating LRCRCallback with value: {value} for
                                      device: {device_name}"""
            )

            exception_message = (
                f"Exception occurred on the following devices:"
                f"for command - {self.command_in_progress} "
                f"{device_name}: {value[1]}\n"
            )

            self.logger.info(f"exception_message :: {exception_message}")

            self.long_running_result_callback(
                self.command_id,
                ResultCode.FAILED,
                exception_message=exception_message,
            )
