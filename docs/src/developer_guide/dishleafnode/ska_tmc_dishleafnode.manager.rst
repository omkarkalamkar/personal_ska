ska\_tmc\_dishleafnode.manager
===========================================

Link to the TMC User documentation is here <https://confluence.skatelescope.org/display/UD/TMC+User+Documentation>_.

component\_manager
-------------------------------------------------------------

.. automodule:: ska_tmc_dishleafnode.manager.component_manager
   :members:
   :undoc-members:
   :show-inheritance:

ska\_tmc\_dishleafnode.manager.program\_track\_table\_calculator module
------------------------------------------------------------------------

.. automodule:: ska_tmc_dishleafnode.manager.program_track_table_calculator
   :members:
   :undoc-members:
   :show-inheritance:

ska\_tmc\_dishleafnode.manager.event\_manager module
-------------------------------------------------------------

.. automodule:: ska_tmc_dishleafnode.manager.event_manager
   :members:
   :undoc-members:
   :show-inheritance:

ska\_tmc\_dishleafnode.manager.dish\_kvalue\_validation\_manager module
------------------------------------------------------------------------

.. automodule:: ska_tmc_dishleafnode.manager.dish_kvalue_validation_manager
   :members:
   :undoc-members:
   :show-inheritance:

Command Timeout
===============

The ``CommandTimeout`` attribute is introduced to allow updating the timeout value
for commands without requiring a redeployment. This provides flexibility in tuning
the timeout dynamically at runtime based on operational needs.

The ``CommandTimeOutDefault`` property is also introduced, which can be used to set
a default timeout value during the deployment phase. This ensures that an initial
timeout value is preconfigured when the component starts for the first time.

Usage
-----

* **CommandTimeout attribute**
  - Can be updated at runtime without redeployment.
  - Helps in adapting to varying command execution times.

* **CommandTimeOutDefault property**
  - Configurable in the deployment configuration (e.g., ``values.yaml``).
  - Sets the initial timeout value at startup.
