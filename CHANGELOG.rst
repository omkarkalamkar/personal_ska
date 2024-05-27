###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

Added
======
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
