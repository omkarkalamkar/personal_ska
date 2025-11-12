.. _scan:

====
Scan
====

    1. Dish Leaf Node provides API for **Scan workflow**.
    2. The Dish Leaf Node **accepts the command** if :-

        A. **DishMode** reported on Dish Leaf Node is in **OPERATE, STANDBY_FP, STOW, MAINTENANCE**.
        B. Dish Master is responsive.

    3. The following **state requirements** are applied for the **command execution** :-

        A. DishMode must be in **OPERATE, STANDBY_FP, STOW, MAINTENANCE**.
        B. Dish Master must be responsive.

    4. The Input JSON is **validated** as below, and Command is **'Rejected'** with exception message **if not met** :-

        A. JSON must not be empty or malformed.
        B. **Presence** of scan-specific keys (e.g., **scan_duration, ca_offset_arcsec, ie_offset_arcsec**) is expected — validation occurs upstream (e.g., in configure or track) and not directly in Scan.
        C. No explicit schema validation in Scan command class.

    5. The **command execution** involves below **key operations** :-

        A. **Adapter Initialization**

            - init_adapter() is called to create a proxy to Dish Master.
            - If adapter creation fails → command returns **ResultCode.FAILED**.

        B. **Invoke Scan on Dish Master**

            - Scan(argin) is invoked directly on Dish Master via adapter.
            - Input argin is passed unchanged as a JSON string.

        C. **Result Handling**

            - If Dish Master returns **ResultCode.QUEUED**:

                i. A unique command ID is stored
                ii. Long Running Command Result (LRCR) will be monitored via longRunningCommandResult attribute.

            - If Dish Master **raises exception** → command failure reported as **ResultCode.FAILED**.
            - If Dish Master **accepts command** → TMC Dish Leaf Node waits for completion via LRCR callback.

    6. The TMC Dish Leaf Node **monitors the progress** of commands via the **long running command results**.

        A. Command is **successful** if below criteria are achieved. This is reported as **ResultCode.OK** on Long Running Command Result attribute of the TMC Dish Leaf Node.

            - scan_result["result_code"] == **ResultCode.OK**
            - Dish Master reports **ResultCode.OK** on its longRunningCommandResult attribute for the Scan command.

        B. Command **failure** is reported in any of the below cases as **ResultCode.FAILED** on Long Running Command Result attribute of the TMC Dish Leaf Node.

            - Dish Master reports **ResultCode.FAILED, REJECTED**, or **NOT_ALLOWED** on its longRunningCommandResult.
            - The command **times out** if Dish Master **fails** to achieve success within the **timeout period** specified by **command_timeout** property in the Helm chart of the TMC Dish Leaf Node.

    7. Input JSON to Dish Master is expected to follow the observation schema

        A. Example keys: **scan_duration, ca_offset_arcsec, ie_offset_arcsec**, etc.
        B. Full schema detailed at: https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/dish/ska-dish.html