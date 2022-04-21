@XTP-6028
Feature: DishLeafNode acceptance

	#Test the ability to generically run a a set of commands and that the execution is completed withing 5 seconds.
	@XTP-6029 @post_deployment @acceptance @SKA_mid
	Scenario: Ability to run commands on DishLeafNode
		Given a DishLeafNode device
		When I call the command <command_name>
		Then the command is queued and executed in less than 5 ss

		Examples:
		| command_name		  |
		| SetStandbyLPMode    |
        | SetStandbyFPMode    |
        | SetOperateMode      |
		| SetStowMode         |