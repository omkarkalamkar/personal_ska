###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

Added
======

[0.17.0]
********
* Update Dish Leaf Node to use correction key from Config json to MAINTAIN, APPLY or RESET offsets on Dish Manager

[0.16.0]
********
* Dish Leaf Node supports **Non-sidereal tracking** for objects present in Katpoint

[0.15.0]
********
* Update Dish Leaf Node to use Base class v1.0.0 and pytango v9.5.0.

[0.14.3]
********
* Introduced IsDishAbortCommands property

[0.14.2]
********
* Enabled push event mechanism for kValue , kValueValidationResult

[0.14.1]
********
* ProgramTrackTable Enabled.
* LongRunningCommandResult used for TrackLoadStaticOff command result.


[0.14.0]
********
* Disabled programTrackTable updates

[0.13.3]
********
* Bug resolved: Dish ID not coming as expected from read dish fqdn.

[0.13.2]
*********
* Utilised ska-tmc-common 0.16.7 that resolves dish leaf node Configure command_inout CORBA exception

[0.13.1]
*********
* Updated Configure command to support multi-configure functionality.


[0.13.0]
*********
* Added improvements in dish leaf node as per modifications outlined in ADR-76.


[0.12.1]
*********
* Improved program track table calculation logic by using multiprocessing in separate class.


[0.12.0]
*********
* Updated Scan command interface to include scan_id as argument
* EndScan command has been added in in Dish Leaf Node to invoke EndScan command on Dish Master.

Fixed
======


[0.16.2]
********
* Improved logger statements on ska-tmc-dishleafnode

[0.16.1]
********
* Used latest version of KatPoint **v1.0a3** to fix the forward and reverse transform calculations.
* Fixed the issue related to IERS_A data download by keeping a local copy of the file under **data/** folder.

[0.16.0]
********
* Fixed integration test cases taking a long time to run by removing unnecessary assertions and unsubscribing to events.
* Fixed the **update_task_callback** method for both **Configure** and **TrackLoadStaticOff** commands

[0.13.3]
*********
Fixed the dish id not coming as expected from real dish master fqdn.

======
[0.13.4]
*********
Program Track Table Process disabled .