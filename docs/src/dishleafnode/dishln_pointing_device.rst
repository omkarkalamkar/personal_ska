ska\_dishln\_pointing\_device.dishln\_pointing\_device module
===================================================================


.. automodule:: ska_dishln_pointing_device.dishln_pointing_device
   :members:
   :undoc-members:
   :show-inheritance:



################################
Attributes in DishPointingDevice
################################


+--------------------------+---------------+----------------------+----------------------------------------------------------+
| Attribute Name           | O/P Data Type | access/AttrWriteType | Description                                              |
+==========================+===============+======================+==========================================================+
| MidPointingDevice | String        | READ                 | This attribute gives dish pointing device fqdn                  |
+--------------------------+---------------+----------------------+----------------------------------------------------------+
| healthState              | HealthState   | READ                 | This attribute gives HealthState of dish pointing device |
+--------------------------+---------------+----------------------+----------------------------------------------------------+
| TargetData               | String        | READ_WRITE           | This attribute provides target data.                     |
+--------------------------+---------------+----------------------+----------------------------------------------------------+
| pointingProgramTrackTable | String       | READ                 | This attribute provides program track table.             |
+--------------------------+---------------+----------------------+----------------------------------------------------------+


##################################
Properties in Dish Pointing Device
##################################

+-------------------------------+---------------+--------------------------------------------------------------------------------+
| Property Name                 | Data Type     | Description                                                                    |
+===============================+===============+================================================================================+
| ElevationMaxLimit             | DevFloat      | Maximum elevation allowed for observation                                      |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| ElevationMinLimit             | DevFloat      | Minimum elevation allowed for observation                                      |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| TrackTableEntries             | DevShort      | Number of entries in programTrackTable                                         |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| PointingCalculationPeriod     | DevShort      | Time difference between two consecutive entries of programTrackTable in        |
|                               |               | milliseconds                                                                   |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| TrackTableInAdvance           | DevShort      | programTrackTable in advance in seconds                                        |
+-------------------------------+---------------+----------------------+---------------------------------------------------------+
| TrackTableUpdateRate          | DevFloat      | The rate at which a tracktable is provided. It is one tracktable per specified |
|                               |               | number of seconds.                                                             |
+-------------------------------+---------------+--------------------------------------------------------------------------------+
| AzimuthMinLimit               | DevFloat      | Minimum value of Azimuth to which dish can point                               |
+-------------------------------+---------------+--------------------------------------------------------------------------------+
| AzimuthMaxLimit               | DevFloat      | Maximum value of Azimuth to which dish can point                               |
+-------------------------------+---------------+--------------------------------------------------------------------------------+