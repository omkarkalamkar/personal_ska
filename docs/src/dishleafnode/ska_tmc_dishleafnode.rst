ska\_tmc\_dishleafnode.dish_leaf_node module
==============================================


.. automodule:: ska_tmc_dishleafnode.dish_leaf_node
   :members:
   :undoc-members:
   :show-inheritance:


###########################
Attributes in DishleafNode
###########################


+-----------------------+--------------- +----------------------+-------------------------------------------------------------------------------------+
| Attribute Name        | O/P Data Type  | access/AttrWriteType |             Description                                                             |
+=======================+================+======================+=====================================================================================+
| dishMode              | DishMode       |         READ         | This attribute reports the DISH dishMode                                            |
+-----------------------+----------------+----------------------+-------------------------------------------------------------------------------------+
| pointingState         | PointingState  |         READ         | This attribute reports the DISH pointingState                                       |
+-----------------------+----------------+----------------------+-------------------------------------------------------------------------------------+
| trackTableErrors      | DevStringArray |         READ         | This attribute provides errors that occurred in the program track table calculation.|
+-----------------------+----------------+----------------------+-------------------------------------------------------------------------------------+
| dishMasterDevName     | String         |       READ_WRITE     | Provides Dish Master device name with DishLeafNode communicates.                    |
+-----------------------+----------------+----------------------+-------------------------------------------------------------------------------------+
| dishlnPointingDevName | String         |       READ_WRITE     | Provides DishLeafNode pointing device name with DishLeafNode communicates.          |
+-----------------------+----------------+----------------------+-------------------------------------------------------------------------------------+
| isSubsystemAvailable  | Bool           |         READ         | Reports the availability of associated Dish Master                                  |
+-----------------------+----------------+----------------------+-------------------------------------------------------------------------------------+
| actualPointing        | String         |         READ         | This attribute reports where the dish is currently pointing in RA and Dec form.     |                                                              |
+-----------------------+----------------+----------------------+-------------------------------------------------------------------------------------+