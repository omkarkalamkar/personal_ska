###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

## [0.23.2]
***********
## Fixed
* Converted GenerateProgramTrackTable command to Slow Command

## [0.23.1]
***********
## Fixed
* Updated Abort command completion check to include pointing state and dish mode.

## [0.23.0]
***********
## Fixed
* Partial Configure updated such that it can be provided with any one of the keys of main configure and dish leaf node update only that specific data in configuration.
* Wrap sector is handled in partial configure.
* Offsets provided in fixed trajectory is used to adjust target used in track table calculation.

[0.22.3]
********
* Improved Dish Event Handler Callbacks by removing processing.

## [0.22.0]
***********
## Added
* Updated ska-tmc-dishleafnode repository to use ska-tango-base v1.2.
* Renamed AbortCommands to Abort.
* Implemented error propagation and timeout handling for Abort command.
* DishLeafNode will catch exceptions thrown by DishManager and report on its LRCR for Abort commands.

[0.21.0]
********
* Updated dish leaf node to handle wrap_sector key.

[0.19.5]
********
* Update lock placement with skb-525 changes.
* Applied fix for SKB-606.
* Applied fixes for multi-configure issues
* Provided TrackTableUpdateRate as a configurable parameter
* Removed PointingCalculationPeriod configurable parameter

[0.19.4]
********
* Update lock placement.
* Update scheduler blocking to false

[0.19.1]
********
* Fix errors observed while testing dish error propagation in tmc-mid integration repository
  
[0.19.0]
********
* Command static pointing model is renamed to ApplyPointingModel.

[0.18.1]
********
* Added DishLeafNode pointing tango device.

[0.18.0]
********
* Implemented error propagation for Track Table calculation.

[0.17.8]
********
* Improved the timeout and error propagation for Configure command
* Implemented timeout and error propagation for commands TrackStop, Scan and EndScan

[0.17.3]
********
* Fix bug SKB-502, to update the attributes at initialization, so that it can show states of attributes at initialization on dashboards

[0.17.2]
********
* Implemented error propagation and timeout for configure command

[0.17.0]
********
* Accomodate changes for the correction key in dish Leaf Node.
* Added StaticPmSetup command to process global pointing json


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

[0.22.5]
* Updated internal pointing State if command is not in progress. 

[0.22.4]
* Added changes in the logs as per Logging Guidelines 
* Added Command ID in logs and fixed logging levels .
* Modifies the log messages to make them readable

[0.22.2]
* Fixed NaN azimuth values issue in programTrackTable generation.

[0.22.1]
* Resolved skb-517 by filtering Track event when command is not in progress 

[0.21.1]
* Fixed NaN azimuth values issue in programTrackTable generation.

[0.20.0]
* Updated the FQDN's as per ADR-9.

[0.19.7]
* Applied fix for SKB-661 and SKB-728

[0.19.6]
********
* Resolved bug SKB-658

[0.19.3]
********
* AbortCommands is implemented as a Slow Command

[0.19.2]
********
* Fixed SKB-525

[0.17.9]
********
* Error Propagation changes incorporated with process to stop track table.

[0.17.7]
********
* Updated logic to stop program track table process.
* Added Try Catch mechanism to identify issues faced in writing program track table on dish master


[0.17.6]
********
* Fix bug SKB-467 - Track command will not be invoked if pointingState is TRACK/SLEW

[0.17.5]
* Updated common v0.20.2 with liveliness probe bug related to full trl fixed.

[0.17.4]
********
* Updated AbortCommands() command as slow command.
* Updated Configure() command to stop the execution when AbortCommands() command is invoked while configuring the dish.
* Made IsDishAbortCommands property configurable at deployment time.

[0.17.1]
* Updated the correction key behaviour when correction key is empty. 

[0.16.4]
* Fix for SKB-419 and SKB-469
* Set and push archive events for all the attributes

[0.16.3]
********
* Patch release from branch SAH-1566 with SKB-419 fix

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

[0.13.4]
*********
Program Track Table Process disabled .