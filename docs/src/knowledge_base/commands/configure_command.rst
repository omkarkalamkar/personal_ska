.. _configure:

=========
Configure
=========

    1. Dish Leaf Node provides API for **Configure workflow**.
    2. The Dish Leaf Node **accepts the command** if :-

        A. Dish Mode reported on Dish Leaf Node is in **STANDBY_FP , STOW, OPERATE**.
        B. Dish Master is responsive.

    3. The following **state requirements** are applied for the **command execution** :-

        A. Dish Mode reported on Dish Leaf Node is in **STANDBY_FP , STOW, OPERATE**.
        B. Dish Master is responsive.

    4. The Input JSON is **validated** as below, and Command is **'Rejected'** with exception message **if they are not met** :-

        A. JSON should not be empty or malformed
        B. Presence of critical **keys** based on type of observation are **validated**.(**pointing, dish, receiver_band**, etc.)

    5. The **command execution** involves below **key operations** :-


        A. :term:`ProgramTrackTable` generation process is started .If this process **fails**, the command updates the health state to **DEGRADED** and returns a failure result.
        B. The command invokes several sub-commands based on the input JSON and the current state:

            - **ConfigureBand**: Invoked to configure the receiver band on the Dish Master.
            - **Track**: Invoked to start tracking after ensuring that PointingState is not **Track** or **SLEW** and :term:`ProgramTrackTable` has been sent to Dish Master.

        C. When each command is invoked on the Dish Master Subarray :-

            - If Dish Master **raises exception** , command failure is reported as **'RESULT_CODE - FAILED'** on Long Running Command Result attribute of the TMC Dish leaf node .
            - If Dish Master **accepts command** , the TMC DISH leaf node will wait for command completion.

    6. The TMC DISH leaf node **monitors the progress** of commands via the **DishMode** , **Pointing State transitions** and the **long running command results**.

        A. Command is **successful** all below criteria are achieved. This is reported as **'RESULT_CODE - OK'** on Long Running Command Result attribute of the TMC Dish leaf node.

            - DishMode is **OPERATE**
            - PointingState is any of the **TRACK** or **SLEW**
            - For each of the command **ConfigureBand,Track** , Dish Master reports **'RESULT_CODE - OK'** on long running command attribute.

        B. Command failure is reported in any of the below cases as **'RESULT_CODE - FAILED'** on Long Running Command Result attribute of the TMC Dish leaf node.

            - The Dish Master reports **'RESULT_CODE - FAILED'** on its Long Running Command Result attribute for any of the sub command.
            - The command **times out** if Dish master **fails** to achive any of the **above success criteria** within the **timeout period** specified by `CommandTimeOutDefault` property specified in helm chart of the TMC Dish Leaf Node .

    7. Input JSON to Dish Master is as per schema detailed at - https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/dish/ska-dish.html