@XTP-6028
Feature: DishLeafNode acceptance

	#Test the ability to generically run a set of commands and that the execution is completed withing 5 seconds.
	@XTP-6029 @post_deployment @acceptance @SKA_mid
	Scenario: Ability to run commands on DishLeafNode
		Given a DishLeafNode device
		When I call the command <command_name> when DishMaster is in <dish_mode>
		Then the <command_name> command is executed successfully and DishMaster transitions to <resultant_state>

		Examples:
		| command_name      | resultant_state    | dish_mode  |
		| SetStandbyFPMode  | STANDBY            | STANDBY_LP |
		| SetOperateMode    | ON                 | STANDBY_FP |
		| SetStandbyLPMode  | STANDBY            | STANDBY_FP |
		| SetStowMode       | DISABLE            | STANDBY_LP |

	#This test is to verify the ping mechanism implemented on Dishleafnode.
	@XTP-10402 @post_deployment @acceptance @SKA_mid
	Scenario: Test ping functionality on Dishleafnode
		Given DishLeafNode and DishMaster devices are running
		When DishLeafNode pings the DishMaster device
		Then the ping information gets updated
