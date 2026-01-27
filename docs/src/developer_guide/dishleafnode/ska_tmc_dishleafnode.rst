ska\_tmc\_dishleafnode.dish_leaf_node module
==============================================

Link to the TMC User documentation is here <https://confluence.skatelescope.org/display/UD/TMC+User+Documentation>_.

.. automodule:: ska_tmc_dishleafnode.dish_leaf_node
   :members:
   :undoc-members:
   :show-inheritance:


###########################
Attributes in DishleafNode
###########################


+--------------------------+--------------------+------------------------------+-----------------------------------------------------------------------------+
| Attribute Name           | O/P Data Type      |    access/AttrWriteType      |               Description                                                   |
+==========================+====================+==============================+=============================================================================+
| dishMode                 |     DishMode       |         READ                 |   This attribute gives the DISH dishMode                                    |
+--------------------------+--------------------+------------------------------+-----------------------------------------------------------------------------+
| pointingState            |     PointingState  |         READ                 |   This attribute gives the DISH pointingState                               |
+--------------------------+-------------------+-------------------------------+-----------------------------------------------------------------------------+
| trackTableErrors         |     DevStringArray |         READ                 |   This attribute gives errors occurred in program track table calculation   |
+--------------------------+--------------------+------------------------------+-----------------------------------------------------------------------------+
| gpmVersion               |     DevStringArray |         Memorized            |   This attribute gives GPM version set for the bands on Dish.               |
+--------------------------+--------------------+------------------------------+-----------------------------------------------------------------------------+
| gpmValidationResult      |     DevStringArray |         READ                 |   This attribute gives GPM validation result for the bands on Dish.         |
+--------------------------+--------------------+------------------------------+-----------------------------------------------------------------------------+
| gpmSourcePath            |     DevStringArray |         Memorized            |   This attribute gives telmodel source path, used for GPM validation        |
+--------------------------+--------------------+------------------------------+-----------------------------------------------------------------------------+
| gpmFilePath              |     DevStringArray |         Memorized            |   This attribute gives telmodel file path, which is used for GPM validation |
+--------------------------+--------------------+------------------------------+-----------------------------------------------------------------------------+
| kValue                   |     DevLong        |         Memorized            |   This attribute gives kValue set on Dish leaf node                         |
+--------------------------+--------------------+------------------------------+-----------------------------------------------------------------------------+
| healthInfo               |     DevString      |         READ                 |   This attribute gives health information about the Dish Leaf Node          |
+--------------------------+--------------------+------------------------------+-----------------------------------------------------------------------------+

############################
Properties in Dish Leaf Node
############################


+-------------------------------+---------------+--------------------------------------------------------------------------------+
| Property Name                 | Data Type     | Description                                                                    |
+===============================+===============+================================================================================+
| DishMasterFQDN                | DevString     | FQDN of the Dish Master Tango Device Server                                    |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| DishlnPointingDeviceFQDN      | DevString     | FQDN of the Dish Pointing device                                               |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| LivelinessCheckPeriod         | DevFloat      | Period for the liveliness probe to monitor each device in a loop               |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| EventSubscriptionCheckPeriod  | DevFloat      | Period for the event subscriber to check the device subscriptions in a loop    |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| AdapterTimeOut                | DevFloat      | Timeout for the adapter creation. This property is for internal use.           |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| CommandTimeOutDefault         | DevFloat      | Default Timeout for the command execution                                      |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| DishAvailabilityCheckTimeout  | DevFloat      | Timeout for the dish availability check during intialisation. This property is |
|                               |               | for internal use.                                                              |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| MaxTrackTableRetry            | DevShort      | Maximum retries for the programTrackTable write operations                     |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| TrackTableRetryDuration       | DevFloat      | Retry duration for programTrackTable write operation in seconds                |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+