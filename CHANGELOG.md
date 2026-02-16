###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

[1.0.0]
*******
Updated
-------
* Base classes v1.4.0 and pytango v10.1.2.

[0.30.1]
********
Added
------
* Unknown Capability will be treated a negative indicator.
* DISH Capabilities transition to UNKNOWN will  be ignored when Dish is not in OPERATE mode.


[0.30.0]
********
Added
------
* Added Autostow functionality.

Updated
-------
* Updated SetStowMode functionality.
* Updated subscription mechanism with event manager.



[0.29.5]
********
Fixed
-----
* Release tag 0.29.5 as tag 0.29.4 has incorrect code base.

[0.29.4]
********
Fixed
-----
* Updated Abort command as per the dish-lmc chart 9.0.0
* Fixed issue with clearing of dictionary command_unique_id_dict

[0.29.3]
********
Added
-----
* Added Program Track Table errors on HealthInfo.

[0.29.2]
********
Added
-----
* Implemented  HealthInfo on Dish Leaf Node
* Improved visibility: failures (e.g. GPM/KValue validation, Dish Manager state, band capability) now surface in healthInfo .


[0.29.1]
********
Added
-----

* Added fix for GPM issue faced on mid integration.


[0.29.0]
********
Added
-----
* Added event subscription for Dish kValue updates
* Implemented validation rules using the rule engine
* Updated dish healthState based on kValue validation results
* Implemented GPM validation functionality on DLN.
* Implemented gpmValidationResult attribute to check the validation per band.
* Implemented gpmSourcePath and gpmFilePath memorized attributes(Developers purpose only.)

[0.28.0]
********
Updated
-------
* TMC Mid to align with the changes introduced in Dish 9.0.0 namely; Deprecated SetOperateMode() command which is orchestrated in the TMC Configure workflow.

[0.27.2]
********
Fixed
-----
* Fixed inproper process shutdown after restart server on DishLeafNode

[0.27.1]
************
Updated
-------
* Fixed the TMC mid ConfigureBand command to support SPFRx configuration.

[0.27.0]
************
Updated
-------
* Updated the TMC mid documentation to bring it on par with the updates made towards resolution of SKB-808
* Updated the TMC mid ConfigureBand command to support SPFRx configuration.
* Utilized ska-tmc-common v.1.1.0.
* Utilized ska-tmc-simulator v.1.4.1.

Added
-----
* Added glossary and command workflow in Knowledge base

[0.26.1]
********
Updated
-------
* Resolved issues for the reverse transform

[0.26.0]
********
Updated
-------
* Disabled the configuredBand check in Configure command to enable Band 5 observation with real dish
* This is a branch release.

[0.25.1]
********
Fixed
-----
* Fixed issue with unresponsive flag update to resolve SKB-1074

[0.25.0]
********
Updated
-------
* Updated ArrayLayout design so it can be changed from the configure command


[0.24.5]
********
Updated
-------
* Updated ApplyPointingModel command as ApplyPointingModel is fastcommand on real dish.

[0.24.4]
********
Added
-----
* Added gpmVersion attribute to display the Global Pointing Model (GPM) version configured for the associated Dish Manager.

[0.24.3]
********
Updated
-------
* Updated imports for the helper device to deploy from ska-tmc-simulators package v1.1.1.
* Updated ska-tmc-common to v0.31.0.

[0.24.2]
********
Fixed
-----
* Updated DishLeafNode band mapping to normalize Band 5A and Band 5B, fixing the band mapping error

[0.24.1]
********
Fixed
-----

* Fixed RTD inline with SKB-808.
* Fixed CHANGELOG format.


[0.24.0]
********
Added
-----

* CommandTimeout attribute is introduced which can help to update timeout without redeployment.
* CommandTimeOutDefault property is introduced which can be used to set default value at the time of deployment.
* Utilized the latest tag of ska-tmc-common (0.30.0).

[0.23.3]
********
Fixed
-----

* Improved resource utilization by program track table thread in dish pointing device.

[0.23.2]
********
Fixed
-----

* Converted GenerateProgramTrackTable command to Slow Command

[0.23.1]
********
Fixed
-----

* Updated Abort command completion check to include pointing state and dish mode.

[0.23.0]
********
Fixed
-----

* Partial Configure updated such that it can be provided with any one of the keys of main configure and dish leaf node update only that specific data in configuration.
* Wrap sector is handled in partial configure.
* Offsets provided in fixed trajectory is used to adjust target used in track table calculation.

[0.22.5]
********
Fixed
-----

* Updated internal pointing State if command is not in progress.

[0.22.4]
********
Fixed
-----

* Added changes in the logs as per Logging Guidelines
* Added Command ID in logs and fixed logging levels .
* Modifies the log messages to make them readable

[0.22.3]
********
* Improved Dish Event Handler Callbacks by removing processing.

[0.22.2]
********
Fixed
-----

* Fixed NaN azimuth values issue in programTrackTable generation.

[0.22.1]
********
Fixed
-----

* Resolved skb-517 by filtering Track event when command is not in progress

[0.22.0]
********
Added
-----

* Updated ska-tmc-dishleafnode repository to use ska-tango-base v1.2.
* Renamed AbortCommands to Abort.
* Implemented error propagation and timeout handling for Abort command.
* DishLeafNode will catch exceptions thrown by DishManager and report on its LRCR for Abort commands.

[0.21.1]
********
Fixed
-----

* Fixed NaN azimuth values issue in programTrackTable generation.

[0.21.0]
********
* Updated dish leaf node to handle wrap_sector key.

[0.20.0]
********

* Updated the FQDN's as per ADR-9.

[0.19.7]
********
Fixed
-----

* Applied fix for SKB-661 and SKB-728

[0.19.6]
********
Fixed
-----

* Resolved bug SKB-658

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

[0.19.3]
********
* AbortCommands is implemented as a Slow Command

[0.19.2]
********
Fixed
-----

* Fixed SKB-525

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

[0.17.9]
********
* Error Propagation changes incorporated with process to stop track table.

[0.17.8]
********
* Improved the timeout and error propagation for Configure command
* Implemented timeout and error propagation for commands TrackStop, Scan and EndScan

[0.17.7]
********
Added
-----

* Updated logic to stop program track table process.
* Added Try Catch mechanism to identify issues faced in writing program track table on dish master

[0.17.6]
********
Fixed
-----

* Fix bug SKB-467 - Track command will not be invoked if pointingState is TRACK/SLEW

[0.17.5]
********
* Updated common v0.20.2 with liveliness probe bug related to full trl fixed.

[0.17.4]
********
* Updated AbortCommands() command as slow command.
* Updated Configure() command to stop the execution when AbortCommands() command is invoked while configuring the dish.
* Made IsDishAbortCommands property configurable at deployment time.

[0.17.3]
********
* Fix bug SKB-502, to update the attributes at initialization, so that it can show states of attributes at initialization on dashboards

[0.17.2]
********
* Implemented error propagation and timeout for configure command

[0.17.1]
********
* Updated the correction key behaviour when correction key is empty.

[0.17.0]
********
* Accomodate changes for the correction key in dish Leaf Node.
* Added StaticPmSetup command to process global pointing json

[0.16.4]
********
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
Added
-----

* Dish Leaf Node supports **Non-sidereal tracking** for objects present in Katpoint

Fixed
-----

* Fixed integration test cases taking a long time to run by removing unnecessary assertions and unsubscribing to events.
* Fixed the **update_task_callback** method for both **Configure** and **TrackLoadStaticOff** commands

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

[0.13.4]
*********
Program Track Table Process disabled .

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
