@XTP-6028
Feature: DishLeafNode acceptance

	#Test the ability to generically run a set of commands and that the execution is completed withing 5 seconds.
	@XTP-6029 @acceptance @SKA_mid
	Scenario: Ability to run commands on DishLeafNode
		Given a DishLeafNode device
		When I call the command <command_name> when DishMaster is in <dish_mode>
		Then the <command_name> command is executed successfully and DishMaster transitions to <resultant_state>

		Examples:
		| command_name      | resultant_state    | dish_mode           |
		| SetStandbyFPMode  | STANDBY            | DishMode.STANDBY_LP |
		| Configure         | STANDBY            | DishMode.STANDBY_FP |
		| SetStandbyLPMode  | STANDBY            | DishMode.STANDBY_FP |
		| SetStowMode       | STANDBY            | DishMode.STANDBY_LP |
