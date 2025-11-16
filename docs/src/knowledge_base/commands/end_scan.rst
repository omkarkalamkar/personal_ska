.. _endscan:

=======
EndScan
=======

    1. Dish Leaf Node provides API for end-scan workflow. The EndScan command is a long-running command that officially terminates an active scan observation.
    2. The Dish Leaf Node **accepts the command** if :—

        A. The dish is in one of the following **operating modes**:

            I. OPERATE
            II. STANDBY_FP
            III. STOW
            IV. MAINTENANCE

        B. The Dish Master is online and responsive.

    3. The following **state requirements** are applied for **command execution** :-

        A. The dish must be in **OPERATE, STANDBY_FP, STOW**, or **MAINTENANCE** mode.
        B. The Dish Master must remain reachable during execution.

    4. No input JSON is required

        A. The EndScan command takes no arguments.
        B. No JSON parsing or schema validation is performed.

    5. The **command execution** involves the following **key operations** :-

        A. **Connect to Dish Master** A connection to the Dish Master device is established.
        B. **Invoke EndScan on Dish Master** The command is sent directly to clear the scanID attribute on the Dish Master, marking the scan as complete.
        C. **Result Handling**

            - If accepted, Dish Master returns **ResultCode.QUEUED**.
            - A unique command ID is stored in ``command_unique_id_dict["EndScan"]``.
            - Final result is delivered asynchronously via the long-running command result attribute.

    6. The TMC Dish Leaf Node **monitors progress** via **long-running command results** :-

        A. Command is **successful** when:

            - The Dish Master reports **ResultCode.OK** on its longRunningCommandResult attribute.
            - The **scanID** is successfully cleared.
            - Final status: **ResultCode.OK** on the TMC Dish Leaf Node.

        B. Command **fails** if any of the following occur:
    
            - Dish Master reports **FAILED, REJECTED**, or **NOT_ALLOWED**.
            - The command times out (exceeds command_timeout from Helm configuration).
            - Final status: **ResultCode.FAILED** with error details.

    7. No input JSON schema

        A. The EndScan command requires no input.
        B. Schema URL: Not applicable