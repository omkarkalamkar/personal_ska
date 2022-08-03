@XTP-6028
Feature: DishLeafNode acceptance

	#Test the ability to generically run a a set of commands and that the execution is completed withing 5 seconds.
	@XTP-6029 @post_deployment @acceptance @SKA_mid
	Scenario: Ability to run commands on DishLeafNode
		Given a DishLeafNode device
		When I call the command <command_name>
		Then the <command_name> command is queued and executed in less than 5 secs

		Examples:
		| command_name		  |
        | SetStandbyFPMode    |
		| SetStandbyLPMode    |
		| SetOperateMode      |


	#This test is to verify the ping mechanism implemented on Dishleafnode.
	@XTP-10402 @post_deployment @acceptance @SKA_mid
	Scenario: Test ping functionality on Dishleafnode
		Given DishLeafNode and DishMaster devices are running
		When DishLeafNode pings the DishMaster device
		Then the ping information gets updated
