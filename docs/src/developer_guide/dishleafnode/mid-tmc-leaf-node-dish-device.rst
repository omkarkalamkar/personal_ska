===============================
MidTmcLeafNodeDish Tango Device
===============================

    A Leaf control node for DishMaster.

    :Device Properties:
    :MidDishControl: FQDN of Dish Master Device
    :Device Attributes:
    :commandExecuted: Stores command executed on the device.
    :dishMasterDevName: Stores Dish Master Device name.
    

Properties
----------
.. index::
	single: AdapterTimeOut; MidTmcLeafNodeDish.AdapterTimeOut

.. py:attribute:: AdapterTimeOut
	:module: MidTmcLeafNodeDish

	:data type: DevFloat
	:default value: 2

.. index::
	single: CommandTimeOutDefault; MidTmcLeafNodeDish.CommandTimeOutDefault

.. py:attribute:: CommandTimeOutDefault
	:module: MidTmcLeafNodeDish

	:data type: DevFloat
	:default value: 30

.. index::
	single: DefaultArrayLayoutPath; MidTmcLeafNodeDish.DefaultArrayLayoutPath

.. py:attribute:: DefaultArrayLayoutPath
	:module: MidTmcLeafNodeDish

	Default path for the array layout definition.

	:data type: DevString
	:default value: instrument/ska1_mid/layout/mid-layout.json

.. index::
	single: DefaultArrayLayoutSourceUris; MidTmcLeafNodeDish.DefaultArrayLayoutSourceUris

.. py:attribute:: DefaultArrayLayoutSourceUris
	:module: MidTmcLeafNodeDish

	Default source URIs for the array layout definition.

	:data type: DevString
	:default value: gitlab://gitlab.com/ska-telescope/ska-telmodel-data?main#tmdata

.. index::
	single: DishAvailabilityCheckTimeout; MidTmcLeafNodeDish.DishAvailabilityCheckTimeout

.. py:attribute:: DishAvailabilityCheckTimeout
	:module: MidTmcLeafNodeDish

	:data type: DevUShort
	:default value: 3

.. index::
	single: EnableAutoStow; MidTmcLeafNodeDish.EnableAutoStow

.. py:attribute:: EnableAutoStow
	:module: MidTmcLeafNodeDish

	Flag to enable AutoStow feature

	:data type: DevBoolean
	:default value: True

.. index::
	single: EventSubscriptionCheckPeriod; MidTmcLeafNodeDish.EventSubscriptionCheckPeriod

.. py:attribute:: EventSubscriptionCheckPeriod
	:module: MidTmcLeafNodeDish

	:data type: DevFloat
	:default value: 1

.. index::
	single: GroupDefinitions; MidTmcLeafNodeDish.GroupDefinitions

.. py:attribute:: GroupDefinitions
	:module: MidTmcLeafNodeDish

	:data type: DevVarStringArray

.. index::
	single: GustWindspeedMeasurementTimeWindow; MidTmcLeafNodeDish.GustWindspeedMeasurementTimeWindow

.. py:attribute:: GustWindspeedMeasurementTimeWindow
	:module: MidTmcLeafNodeDish

	Gust wind speed tracking duration(unit seconds) for             auto stowing

	:data type: DevDouble
	:default value: 3.0

.. index::
	single: IsDishAbortEnabled; MidTmcLeafNodeDish.IsDishAbortEnabled

.. py:attribute:: IsDishAbortEnabled
	:module: MidTmcLeafNodeDish

	:data type: DevBoolean

.. index::
	single: LivelinessCheckPeriod; MidTmcLeafNodeDish.LivelinessCheckPeriod

.. py:attribute:: LivelinessCheckPeriod
	:module: MidTmcLeafNodeDish

	:data type: DevFloat
	:default value: 1

.. index::
	single: LoggingLevelDefault; MidTmcLeafNodeDish.LoggingLevelDefault

.. py:attribute:: LoggingLevelDefault
	:module: MidTmcLeafNodeDish

	:data type: DevUShort
	:default value: 4

.. index::
	single: LoggingTargetsDefault; MidTmcLeafNodeDish.LoggingTargetsDefault

.. py:attribute:: LoggingTargetsDefault
	:module: MidTmcLeafNodeDish

	:data type: DevVarStringArray
	:default value: ['tango::logger']

.. index::
	single: MaxAllowedGustWindspeed; MidTmcLeafNodeDish.MaxAllowedGustWindspeed

.. py:attribute:: MaxAllowedGustWindspeed
	:module: MidTmcLeafNodeDish

	Threshold on gust wind speed(unit m/s) for auto stowing

	:data type: DevDouble
	:default value: 20.0

.. index::
	single: MaxAllowedOpsMeanWindspeedMeasurementTimeWindow; MidTmcLeafNodeDish.MaxAllowedOpsMeanWindspeedMeasurementTimeWindow

.. py:attribute:: MaxAllowedOpsMeanWindspeedMeasurementTimeWindow
	:module: MidTmcLeafNodeDish

	Operational wind speed mean and percentile difference             duration(unit seconds) for auto stowing

	:data type: DevDouble
	:default value: 600.0

.. index::
	single: MaxAllowedOpsWindspeed; MidTmcLeafNodeDish.MaxAllowedOpsWindspeed

.. py:attribute:: MaxAllowedOpsWindspeed
	:module: MidTmcLeafNodeDish

	Threshold on operational wind speed(unit m/s) for auto stowing

	:data type: DevDouble
	:default value: 10.0

.. index::
	single: MaxAllowedWindspeed; MidTmcLeafNodeDish.MaxAllowedWindspeed

.. py:attribute:: MaxAllowedWindspeed
	:module: MidTmcLeafNodeDish

	Threshold on wind speed(unit m/s) for auto stowing

	:data type: DevDouble
	:default value: 13.5

.. index::
	single: MaxAllowedWindspeedDifference; MidTmcLeafNodeDish.MaxAllowedWindspeedDifference

.. py:attribute:: MaxAllowedWindspeedDifference
	:module: MidTmcLeafNodeDish

	Threshold on operational wind speed(unit m/s) for auto stowing

	:data type: DevDouble
	:default value: 4.5

.. index::
	single: MaxTemperatureThreshold; MidTmcLeafNodeDish.MaxTemperatureThreshold

.. py:attribute:: MaxTemperatureThreshold
	:module: MidTmcLeafNodeDish

	Maximum Temperature(unit °C) threshold for auto stowing

	:data type: DevDouble
	:default value: 40

.. index::
	single: MaxTrackTableRetry; MidTmcLeafNodeDish.MaxTrackTableRetry

.. py:attribute:: MaxTrackTableRetry
	:module: MidTmcLeafNodeDish

	Maximum retries for the programTrackTable write operations

	:data type: DevShort
	:default value: 3

.. index::
	single: MeanWindspeedMeasurementTimeWindow; MidTmcLeafNodeDish.MeanWindspeedMeasurementTimeWindow

.. py:attribute:: MeanWindspeedMeasurementTimeWindow
	:module: MidTmcLeafNodeDish

	Wind speed tracking duration(unit seconds) for auto stowing

	:data type: DevDouble
	:default value: 600.0

.. index::
	single: MidDishControl; MidTmcLeafNodeDish.MidDishControl

.. py:attribute:: MidDishControl
	:module: MidTmcLeafNodeDish

	FQDN of Dish Master Device

	:data type: DevString

.. index::
	single: MidPointingDevice; MidTmcLeafNodeDish.MidPointingDevice

.. py:attribute:: MidPointingDevice
	:module: MidTmcLeafNodeDish

	FQDN of DishLeaf Node Pointing Device

	:data type: DevString

.. index::
	single: MinTemperatureThreshold; MidTmcLeafNodeDish.MinTemperatureThreshold

.. py:attribute:: MinTemperatureThreshold
	:module: MidTmcLeafNodeDish

	Minimum Temperature(unit °C) threshold for auto stowing

	:data type: DevDouble
	:default value: -5

.. index::
	single: SkaLevel; MidTmcLeafNodeDish.SkaLevel

.. py:attribute:: SkaLevel
	:module: MidTmcLeafNodeDish

	:data type: DevShort
	:default value: 4

.. index::
	single: TemperatureDelta; MidTmcLeafNodeDish.TemperatureDelta

.. py:attribute:: TemperatureDelta
	:module: MidTmcLeafNodeDish

	Temperature delta(unit °C) to calculate

	the rate of change in temperature for auto stowing
	:data type: DevDouble
	:default value: 4.5

.. index::
	single: TimeDelta; MidTmcLeafNodeDish.TimeDelta

.. py:attribute:: TimeDelta
	:module: MidTmcLeafNodeDish

	Time delta(unit seconds) to calculate

	the rate of change in temperature for auto stowing
	:data type: DevDouble
	:default value: 1000.0

.. index::
	single: TrackTableRetryDuration; MidTmcLeafNodeDish.TrackTableRetryDuration

.. py:attribute:: TrackTableRetryDuration
	:module: MidTmcLeafNodeDish

	Retry duration for programTrackTable write operation in seconds

	:data type: DevFloat
	:default value: 0.2

.. index::
	single: WeatherStationDeviceNames; MidTmcLeafNodeDish.WeatherStationDeviceNames

.. py:attribute:: WeatherStationDeviceNames
	:module: MidTmcLeafNodeDish

	FQDN's of Weather Station devices

	:data type: DevVarStringArray

.. index::
	single: WindspeedMeasurementTimeWindow; MidTmcLeafNodeDish.WindspeedMeasurementTimeWindow

.. py:attribute:: WindspeedMeasurementTimeWindow
	:module: MidTmcLeafNodeDish

	Operational wind speed tracking duration(unit seconds) for             auto stowing

	:data type: DevDouble
	:default value: 1000.0

Attributes
----------
.. index::
	single: State; MidTmcLeafNodeDish.State

.. py:attribute:: State
	:module: MidTmcLeafNodeDish

	The operational state of the device as enumeration.

	:access: READ
	:data type: DevState
	:data format: SCALAR

.. index::
	single: Status; MidTmcLeafNodeDish.Status

.. py:attribute:: Status
	:module: MidTmcLeafNodeDish

	More detailed textual information about the device's status.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: actualPointing; MidTmcLeafNodeDish.actualPointing

.. py:attribute:: actualPointing
	:module: MidTmcLeafNodeDish

	No description

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: adminMode; MidTmcLeafNodeDish.adminMode

.. py:attribute:: adminMode
	:module: MidTmcLeafNodeDish

	The Admin Mode of the device. It may interpret the current device condition and condition of all managed devices to set this. Most possibly an aggregate attribute.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: arrayLayout; MidTmcLeafNodeDish.arrayLayout

.. py:attribute:: arrayLayout
	:module: MidTmcLeafNodeDish

	Returns the array-layout attribute value.

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: buildState; MidTmcLeafNodeDish.buildState

.. py:attribute:: buildState
	:module: MidTmcLeafNodeDish

	Read the Build State of the device.

	:return: the build state of the device

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: commandTimeOut; MidTmcLeafNodeDish.commandTimeOut

.. py:attribute:: commandTimeOut
	:module: MidTmcLeafNodeDish

	Command execution time limit.

	:access: READ_WRITE
	:data type: DevUShort
	:data format: SCALAR

.. index::
	single: commandedState; MidTmcLeafNodeDish.commandedState

.. py:attribute:: commandedState
	:module: MidTmcLeafNodeDish

	The last commanded Operating State of the device. Initial string is "None".  Only other strings it can change to is "OFF", "STANDBY" or "ON", following the Off(), Standby() or On() commands. If the state transition commands are long running commands the commanded state will only update when the long running command starts executing.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: controlMode; MidTmcLeafNodeDish.controlMode

.. py:attribute:: controlMode
	:module: MidTmcLeafNodeDish

	The control mode of the device are REMOTE, LOCAL Tango Device accepts only from a ‘local’ client and ignores commands and queries received from TM or any other ‘remote’ clients. The Local clients has to release LOCAL control before REMOTE clients can take control again.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: dishMasterDevName; MidTmcLeafNodeDish.dishMasterDevName

.. py:attribute:: dishMasterDevName
	:module: MidTmcLeafNodeDish

	No description

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: dishMode; MidTmcLeafNodeDish.dishMode

.. py:attribute:: dishMode
	:module: MidTmcLeafNodeDish

	current value of the dishMode attribute

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: dishlnPointingDevName; MidTmcLeafNodeDish.dishlnPointingDevName

.. py:attribute:: dishlnPointingDevName
	:module: MidTmcLeafNodeDish

	No description

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: globalPointingModelParams; MidTmcLeafNodeDish.globalPointingModelParams

.. py:attribute:: globalPointingModelParams
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: gpmFilePath; MidTmcLeafNodeDish.gpmFilePath

.. py:attribute:: gpmFilePath
	:module: MidTmcLeafNodeDish

	Returns the tm data file path

	:return: gpm data file path
		:rtype: str

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: gpmSourcePath; MidTmcLeafNodeDish.gpmSourcePath

.. py:attribute:: gpmSourcePath
	:module: MidTmcLeafNodeDish

	Returns the tm data source path

	:return: source path
		:rtype: str

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: gpmValidationResult; MidTmcLeafNodeDish.gpmValidationResult

.. py:attribute:: gpmValidationResult
	:module: MidTmcLeafNodeDish

	Returns the band-specific GPM validation result.

	(dictionary stored in component manager).
	Format: {"band": ResultCode(UNKNOWN/OK/FAILED)}.

	:return: JSON string of band-to-GPM validation result mapping
		:rtype: str

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: gpmVersion; MidTmcLeafNodeDish.gpmVersion

.. py:attribute:: gpmVersion
	:module: MidTmcLeafNodeDish

	Returns the band-specific GPM version

	(stored in component manager as a dictionary).
	Format: {"band": "version"}.

	:return: JSON string of band-to-GPM version mapping
		:rtype: str

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: gustWindspeedMeasurementTimeWindow; MidTmcLeafNodeDish.gustWindspeedMeasurementTimeWindow

.. py:attribute:: gustWindspeedMeasurementTimeWindow
	:module: MidTmcLeafNodeDish

	Reads the gustWindspeedMeasurementTimeWindow attribute value.

	Returns:
	float: gustWindspeedMeasurementTimeWindow attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: s

.. index::
	single: healthInfo; MidTmcLeafNodeDish.healthInfo

.. py:attribute:: healthInfo
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: healthState; MidTmcLeafNodeDish.healthState

.. py:attribute:: healthState
	:module: MidTmcLeafNodeDish

	Read the Health State of the device. It interprets the current device condition and condition of all managed devices to set this. Most possibly an aggregate attribute.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: isSubsystemAvailable; MidTmcLeafNodeDish.isSubsystemAvailable

.. py:attribute:: isSubsystemAvailable
	:module: MidTmcLeafNodeDish

	Boolean Flag for sub system available

	:access: READ
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: kValue; MidTmcLeafNodeDish.kValue

.. py:attribute:: kValue
	:module: MidTmcLeafNodeDish

	Returns the k-value attribute value.

	:access: READ_WRITE
	:data type: DevLong
	:data format: SCALAR

.. index::
	single: kValueValidationResult; MidTmcLeafNodeDish.kValueValidationResult

.. py:attribute:: kValueValidationResult
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: lastPointingData; MidTmcLeafNodeDish.lastPointingData

.. py:attribute:: lastPointingData
	:module: MidTmcLeafNodeDish

	This attribute is used to store the recent

	pointing data received in calibration scan

	:return: str

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: loggingLevel; MidTmcLeafNodeDish.loggingLevel

.. py:attribute:: loggingLevel
	:module: MidTmcLeafNodeDish

	Read the logging level of the device.

	Initialises to LoggingLevelDefault on startup.
	See :py:class:`~ska_control_model.LoggingLevel`

	:return:  Logging level of the device.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: loggingTargets; MidTmcLeafNodeDish.loggingTargets

.. py:attribute:: loggingTargets
	:module: MidTmcLeafNodeDish

	Read the additional logging targets of the device.

	Note that this excludes the handlers provided by the ska_ser_logging
	library defaults - initialises to LoggingTargetsDefault on startup.

	:return:  Logging level of the device.

	:access: READ_WRITE
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 4

.. index::
	single: longRunningCommandIDsInQueue; MidTmcLeafNodeDish.longRunningCommandIDsInQueue

.. py:attribute:: longRunningCommandIDsInQueue
	:module: MidTmcLeafNodeDish

	Read the IDs of the long running commands in the queue.

	Every client that executes a command will receive a command ID as response.
	Keep track of IDs currently allocated.
	Entries are removed `self._command_tracker._removal_time` seconds
	after they have finished.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 66

.. index::
	single: longRunningCommandInProgress; MidTmcLeafNodeDish.longRunningCommandInProgress

.. py:attribute:: longRunningCommandInProgress
	:module: MidTmcLeafNodeDish

	Read the name(s) of the currently executing long running command(s).

	Name(s) of command and possible abort in progress or empty string(s).

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: longRunningCommandProgress; MidTmcLeafNodeDish.longRunningCommandProgress

.. py:attribute:: longRunningCommandProgress
	:module: MidTmcLeafNodeDish

	Read the progress of the currently executing long running command(s).

	ID, progress of the currently executing command(s).
	Clients can subscribe to on_change event and wait
	for the ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 4

.. index::
	single: longRunningCommandResult; MidTmcLeafNodeDish.longRunningCommandResult

.. py:attribute:: longRunningCommandResult
	:module: MidTmcLeafNodeDish

	Read the result of the completed long running command.

	Reports unique_id, json-encoded result.
	Clients can subscribe to on_change event and wait for
	the ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: longRunningCommandStatus; MidTmcLeafNodeDish.longRunningCommandStatus

.. py:attribute:: longRunningCommandStatus
	:module: MidTmcLeafNodeDish

	Read the status of the currently executing long running commands.

	ID, status pairs of the currently executing commands.
	Clients can subscribe to on_change event and wait for the
	ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 132

.. index::
	single: longRunningCommandsInQueue; MidTmcLeafNodeDish.longRunningCommandsInQueue

.. py:attribute:: longRunningCommandsInQueue
	:module: MidTmcLeafNodeDish

	Read the long running commands in the queue.

	Keep track of which commands are that are currently known about.
	Entries are removed `self._command_tracker._removal_time` seconds
	after they have finished.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 66

.. index::
	single: lrcExecuting; MidTmcLeafNodeDish.lrcExecuting

.. py:attribute:: lrcExecuting
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: lrcFinished; MidTmcLeafNodeDish.lrcFinished

.. py:attribute:: lrcFinished
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 100

.. index::
	single: lrcProtocolVersions; MidTmcLeafNodeDish.lrcProtocolVersions

.. py:attribute:: lrcProtocolVersions
	:module: MidTmcLeafNodeDish

	Return supported protocol versions.

	:return: A tuple containing the lower and upper bounds of supported long running
		command protocol versions.

	:access: READ
	:data type: DevLong64
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: lrcQueue; MidTmcLeafNodeDish.lrcQueue

.. py:attribute:: lrcQueue
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 32

.. index::
	single: maxAllowedGustWindspeed; MidTmcLeafNodeDish.maxAllowedGustWindspeed

.. py:attribute:: maxAllowedGustWindspeed
	:module: MidTmcLeafNodeDish

	Reads the maxAllowedGustWindspeed attribute value.

	Returns:
	float: maxAllowedGustWindspeed attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: m/s

.. index::
	single: maxAllowedOpsMeanWindspeedMeasurementTimeWindow; MidTmcLeafNodeDish.maxAllowedOpsMeanWindspeedMeasurementTimeWindow

.. py:attribute:: maxAllowedOpsMeanWindspeedMeasurementTimeWindow
	:module: MidTmcLeafNodeDish

	Reads the maxAllowedOpsMeanWindspeedMeasurementTimeWindow

	attribute value.
	Returns:
	float: maxAllowedOpsMeanWindspeedMeasurementTimeWindow
	attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: s

.. index::
	single: maxAllowedOpsWindspeed; MidTmcLeafNodeDish.maxAllowedOpsWindspeed

.. py:attribute:: maxAllowedOpsWindspeed
	:module: MidTmcLeafNodeDish

	Reads the maxAllowedOpsWindspeed attribute value.

	Returns:
	float: maxAllowedOpsWindspeed attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: m/s

.. index::
	single: maxAllowedWindspeed; MidTmcLeafNodeDish.maxAllowedWindspeed

.. py:attribute:: maxAllowedWindspeed
	:module: MidTmcLeafNodeDish

	Reads the maxAllowedWindspeed attribute value.

	Returns:
	float: maxAllowedWindspeed attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: m/s

.. index::
	single: maxAllowedWindspeedDifference; MidTmcLeafNodeDish.maxAllowedWindspeedDifference

.. py:attribute:: maxAllowedWindspeedDifference
	:module: MidTmcLeafNodeDish

	Reads the maxAllowedWindspeedDifference attribute value.

	Returns:
	float: maxAllowedWindspeedDifference attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: m/s

.. index::
	single: maxTemperatureThreshold; MidTmcLeafNodeDish.maxTemperatureThreshold

.. py:attribute:: maxTemperatureThreshold
	:module: MidTmcLeafNodeDish

	Reads the maxTemperatureThreshold attribute value.

	Returns:
	float: maxTemperatureThreshold attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: °C

.. index::
	single: meanGustSpeed; MidTmcLeafNodeDish.meanGustSpeed

.. py:attribute:: meanGustSpeed
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: meanOpsWindSpeed; MidTmcLeafNodeDish.meanOpsWindSpeed

.. py:attribute:: meanOpsWindSpeed
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: meanWindSpeed; MidTmcLeafNodeDish.meanWindSpeed

.. py:attribute:: meanWindSpeed
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: meanWindspeedMeasurementTimeWindow; MidTmcLeafNodeDish.meanWindspeedMeasurementTimeWindow

.. py:attribute:: meanWindspeedMeasurementTimeWindow
	:module: MidTmcLeafNodeDish

	Reads the meanWindspeedMeasurementTimeWindow attribute value.

	Returns:
	float: meanWindSpeedDuration attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: s

.. index::
	single: minTemperatureThreshold; MidTmcLeafNodeDish.minTemperatureThreshold

.. py:attribute:: minTemperatureThreshold
	:module: MidTmcLeafNodeDish

	Reads the minTemperatureThreshold attribute value.

	Returns:
	float: minTemperatureThreshold attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: °C

.. index::
	single: opsMeanWindSpeedDifference; MidTmcLeafNodeDish.opsMeanWindSpeedDifference

.. py:attribute:: opsMeanWindSpeedDifference
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: percentileForDiff; MidTmcLeafNodeDish.percentileForDiff

.. py:attribute:: percentileForDiff
	:module: MidTmcLeafNodeDish

	Reads the percentileForDiff attribute value.

	Returns:
	float: percentileForDiff attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: pointingState; MidTmcLeafNodeDish.pointingState

.. py:attribute:: pointingState
	:module: MidTmcLeafNodeDish

	current value of the dishMode attribute

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: rateOfChangeTemperature; MidTmcLeafNodeDish.rateOfChangeTemperature

.. py:attribute:: rateOfChangeTemperature
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: sdpQueueConnectorFqdn; MidTmcLeafNodeDish.sdpQueueConnectorFqdn

.. py:attribute:: sdpQueueConnectorFqdn
	:module: MidTmcLeafNodeDish

	This attribute is used for storing the FQDN of pointing_cal

	attribute from SDP queue connector device, which is required in
	calibration scan.

	:return: str

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: simulationMode; MidTmcLeafNodeDish.simulationMode

.. py:attribute:: simulationMode
	:module: MidTmcLeafNodeDish

	When TRUE the device is using a simulator

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: sourceOffset; MidTmcLeafNodeDish.sourceOffset

.. py:attribute:: sourceOffset
	:module: MidTmcLeafNodeDish

	Stores offsets from delta/partial configuration

	:access: READ
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: stowStatus; MidTmcLeafNodeDish.stowStatus

.. py:attribute:: stowStatus
	:module: MidTmcLeafNodeDish

	Expose a signal as a Tango attribute.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: temperatureDelta; MidTmcLeafNodeDish.temperatureDelta

.. py:attribute:: temperatureDelta
	:module: MidTmcLeafNodeDish

	Reads the temperatureDelta attribute value.

	Returns:
	float: temperatureDelta attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: °C

.. index::
	single: testMode; MidTmcLeafNodeDish.testMode

.. py:attribute:: testMode
	:module: MidTmcLeafNodeDish

	If TEST the device is using testing logic

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: timeDelta; MidTmcLeafNodeDish.timeDelta

.. py:attribute:: timeDelta
	:module: MidTmcLeafNodeDish

	Reads the timeDelta attribute value.

	Returns:
	float: timeDelta attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: s

.. index::
	single: trackTableErrors; MidTmcLeafNodeDish.trackTableErrors

.. py:attribute:: trackTableErrors
	:module: MidTmcLeafNodeDish

	TrackTable errors to be reported

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: versionId; MidTmcLeafNodeDish.versionId

.. py:attribute:: versionId
	:module: MidTmcLeafNodeDish

	Read the Version Id of the device.

	:return: the version id of the device

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: windSpeedMeasurementTimeWindow; MidTmcLeafNodeDish.windSpeedMeasurementTimeWindow

.. py:attribute:: windSpeedMeasurementTimeWindow
	:module: MidTmcLeafNodeDish

	Reads the windSpeedMeasurementTimeWindow attribute value.

	Returns:
	float: windSpeedMeasurementTimeWindow attribute value.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR
	:unit: s

Commands
--------
.. index::
	single: Abort; MidTmcLeafNodeDish.Abort

.. py:method:: Abort() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: AbortCommands; MidTmcLeafNodeDish.AbortCommands

.. py:method:: AbortCommands() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: returns (None): A tuple containing a return code and a string
		message indicating status. The message is for
		information purpose only.

.. index::
	single: ApplyPointingModel; MidTmcLeafNodeDish.ApplyPointingModel

.. py:method:: ApplyPointingModel(DevString) -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	:param argin: (not documented)

	:type argin: DevString

	:returns: returns (tuple): None

.. index::
	single: CheckLongRunningCommandStatus; MidTmcLeafNodeDish.CheckLongRunningCommandStatus

.. py:method:: CheckLongRunningCommandStatus(DevString) -> DevString
	:module: MidTmcLeafNodeDish

	command id

	:returns: TaskStatus

.. index::
	single: Configure; MidTmcLeafNodeDish.Configure

.. py:method:: Configure(DevString) -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	:param argin: (not documented)

	:type argin: DevString

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ConfigureBand; MidTmcLeafNodeDish.ConfigureBand

.. py:method:: ConfigureBand(DevString) -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	:param argin: (not documented)

	:type argin: DevString

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: DebugDevice; MidTmcLeafNodeDish.DebugDevice

.. py:method:: DebugDevice() -> DevUShort
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: The TCP port the debugger is listening on.

.. index::
	single: EndScan; MidTmcLeafNodeDish.EndScan

.. py:method:: EndScan() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: returns (Tuple[List[ResultCode], List[str]]): None

.. index::
	single: GetVersionInfo; MidTmcLeafNodeDish.GetVersionInfo

.. py:method:: GetVersionInfo() -> DevVarStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: returns (None): The result code and the command unique ID

.. index::
	single: Init; MidTmcLeafNodeDish.Init

.. py:method:: Init() -> DevVoid
	:module: MidTmcLeafNodeDish

	Init

.. index::
	single: ObsReset; MidTmcLeafNodeDish.ObsReset

.. py:method:: ObsReset() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: Off; MidTmcLeafNodeDish.Off

.. py:method:: Off() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: On; MidTmcLeafNodeDish.On

.. py:method:: On() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: [ResultCode][message or command id]

.. index::
	single: Reset; MidTmcLeafNodeDish.Reset

.. py:method:: Reset() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: [ResultCode][message or command id]

.. index::
	single: Restart; MidTmcLeafNodeDish.Restart

.. py:method:: Restart() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: Scan; MidTmcLeafNodeDish.Scan

.. py:method:: Scan(DevString) -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	:param argin: (not documented)

	:type argin: DevString

	:returns: returns (Tuple[List[ResultCode], List[str]]): None

.. index::
	single: SetKValue; MidTmcLeafNodeDish.SetKValue

.. py:method:: SetKValue(DevLong64) -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	:param k_value: (not documented)

	:type k_value: DevLong64

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: SetStandbyFPMode; MidTmcLeafNodeDish.SetStandbyFPMode

.. py:method:: SetStandbyFPMode() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: SetStandbyLPMode; MidTmcLeafNodeDish.SetStandbyLPMode

.. py:method:: SetStandbyLPMode() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: SetStowMode; MidTmcLeafNodeDish.SetStowMode

.. py:method:: SetStowMode() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: returns (Tuple): None

.. index::
	single: Standby; MidTmcLeafNodeDish.Standby

.. py:method:: Standby() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: [ResultCode][message or command id]

.. index::
	single: StartCapture; MidTmcLeafNodeDish.StartCapture

.. py:method:: StartCapture(DevString) -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	The timestamp indicates the time, in UTC, at which command

	execution should start.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: StopCapture; MidTmcLeafNodeDish.StopCapture

.. py:method:: StopCapture(DevString) -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	The timestamp indicates the time, in UTC, at which command

	execution should start.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: Track; MidTmcLeafNodeDish.Track

.. py:method:: Track(DevString) -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	:param argin: (not documented)

	:type argin: DevString

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: TrackLoadStaticOff; MidTmcLeafNodeDish.TrackLoadStaticOff

.. py:method:: TrackLoadStaticOff(DevString) -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	:param argin: (not documented)

	:type argin: DevString

	:returns: returns (tuple): None

.. index::
	single: TrackStop; MidTmcLeafNodeDish.TrackStop

.. py:method:: TrackStop() -> DevVarLongStringArray
	:module: MidTmcLeafNodeDish

	No input parameter (DevVoid)

	:returns: returns (tuple): None
