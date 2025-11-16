.. _applypointingmodel:

==================
ApplyPointingModel
==================

    1. Dish Leaf Node provides API for applying a :term:`GlobalPointingModel`. The ApplyPointingModel command downloads a pointing model from a specified TelModel URI and applies it to the Dish Master.
    2. The Dish Leaf Node **accepts the command** if :—

        A. The Dish Master is **online** and **responsive**.
        B. No restriction on **DishMode** or **PointingState** — command is always allowed if the device is reachable.

    3. The following **state requirements** are applied for **command execution** :-

        A. Dish Master must be reachable via TANGO.
        B. The TelModel URI must be accessible and contain valid JSON.

    4. The Input JSON is **validated** as below, and command is **rejected if not met** :-

        A. Must be valid JSON.
        B. Must contain:

            - **tm_data_sources**: List of TelModel repository URLs (at least one).
            - **tm_data_filepath**: Path to the pointing model file (e.g., /gpm/Band_1/pointing_model.json).

        C. If either field is **missing or empty** → immediate **ResultCode.FAILED**.

    5. The **command execution** involves the following **key operations** :-

        A. Download Pointing Model JSON

            1. Uses **ska_telmodel** to fetch the file from the TelModel repository.
            2. 10-second timeout — if unreachable → **ResultCode.FAILED**.

        B. Validate File Existence

            - Checks that the file exists at the specified path in the repository.
            - If not found → **ResultCode.FAILED**.

        C. Extract Band and Version

            - Band (e.g., Band_1, Band_5a) from **tm_data_filepath**.
            - Version from URL query string in tm_data_sources.
            - Updates :term:`GPM` version tracking in the component manager.

        D. Send to Dish Master

            - Full JSON is forwarded to Dish Master via ApplyPointingModel() command.
            - Returns immediately with **QUEUED** and a unique command ID.

    6. The TMC Dish Leaf Node **monitors progress** via **long-running command results**

        A. Command is **successful** when:

            - Dish Master reports **ResultCode.OK** via **longRunningCommandResult**.
            - :term:`GPM` version is updated in the system.
            - Final status: **ResultCode.OK**.

        B. Command **fails** if any of the following occur:

            - TelModel URI unreachable or file not found.
            - Invalid JSON or missing fields.
            - Dish Master returns **FAILED, REJECTED**, or **NOT_ALLOWED**.
            - Timeout exceeds command_timeout.
            - Final status: **ResultCode.FAILED** with error message.

    7. **Input Json Schema**

        {

          "tm_data_sources": ["https://ska-telmodel.skatelescope.org/gpm?interface=..."],

          "tm_data_filepath": "/gpm/Band_1/pointing_model.json"

        }

        Full schema: https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/dish/ska-dish.html