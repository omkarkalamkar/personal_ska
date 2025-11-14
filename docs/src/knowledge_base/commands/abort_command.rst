.. _abort:

======
Abort
======

    1. Dish Leaf Node provides API for **Abort workflow**.
    2. The Dish Leaf Node **accepts the command** unconditionally :-

        A. No checks on **DishMode, PointingState**, or current operation.
        B. Designed to interrupt any ongoing activity and force the system into a safe **ABORTED** state.

    3. The following **state requirements** are applied for **command execution** :-

        A. Dish Master must be responsive (TANGO device proxy and adapter must initialize successfully).
        B. No dependency on current dish operating mode or pointing state.

    4. No input JSON **validation** is performed :-

        A. The Abort command requires no input arguments.
        B. No JSON parsing or schema **validation** is needed.

    5. The **command execution** involves the following **key operations** :-

        A. **Trigger global abort signal**

            - abort_event is set to notify all background tasks and observers.
            - TANGO clients are notified of state changes via attribute update.
            - abort_event is cleared immediately after.

        B. **Terminate all ongoing internal tasks**

            - All background operations (e.g., **tracking, configuration**) are aborted.
            - Progress is reported in two phases:

                i. 0-50%: Completion of internal task termination.
                ii. 50-100%: Completion of Abort on Dish Master and track table stop.

        C. Invoke Abort on Dish Master (conditional)

            - If `is_dish_abort_commands_enabled` == True:

                i. Abort() command is sent to Dish Master via adapter.
                ii. A unique command ID is recorded for tracking.

            - If Dish Master returns **REJECTED, NOT_ALLOWED, or ABORTED** → command fails immediately with same result.
            - Otherwise, execution continues (long-running command).

        D. Stop :term:`ProgramTrackTable` generation

            - StopProgramTrackTable() is invoked on the Dish LN Pointing Device.
            - On failure:

                i. Error is logged.
                ii. **Health state** is updated to **DEGRADED**.
                iii. Command **fails** with **ResultCode.FAILED**.

        E. Clear residual track table errors

            Any stored track table errors are reset.

    6. The TMC Dish Leaf Node **monitors progress** via **task callbacks** and **timeout tracking** :-

        A. Command reports **ResultCode.STARTED** immediately after:

            i. Adapter initialization.
            ii. Issuing Abort (if enabled) and StopProgramTrackTable.
            iii. Final success/failure is reported asynchronously.

        B. **Success** criteria (reported as **TaskStatus.COMPLETED**)

            i. All internal tasks are terminated.
            ii. StopProgramTrackTable completes without error.
            iii. Abort command (if sent) is accepted by Dish Master.
            iv. Progress reaches 100% via callback.

        C. **Failure** is reported in any of the following cases (**TaskStatus.FAILED**)

            i. Dish Master adapter fails to initialize.
            ii. StopProgramTrackTable() raises an **exception** → health **DEGRADED**.
            iii. Internal task abortion fails.
            iv. Timeout: Command **exceeds command_timeout** (configured via TimeKeeper) → automatic failure.

    7. No input JSON schema

        - The Abort command accepts no input.
        - No reference to external schema (unlike Configure command).
        - Schema URL: Not applicable