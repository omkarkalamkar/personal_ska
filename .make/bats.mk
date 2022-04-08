# include Makefile for Helm Chart related targets and variables

# do not declare targets if help had been invoked
ifneq (long-help,$(firstword $(MAKECMDGOALS)))
ifneq (help,$(firstword $(MAKECMDGOALS)))

SHELL=/usr/bin/env bash

BATS_TEST_DIR ?= tests/unit ## The directory for bats tests

.PHONY: bats-pre-install bats-do-install bats-post-install bats-install \
	bats-uninstall bats-pre-uninstall bats-do-uninstall

bats-reinstall: bats-uninstall bats-install ## reinstall bats-core dependencies

bats-pre-uninstall:

bats-post-uninstall:

bats-do-uninstall:
	@rm -rf $(CURDIR)/scripts/bats-*

## TARGET: bats-uninstall
## SYNOPSIS: make bats-uninstall
## HOOKS: bats-pre-uninstall, bats-post-uninstall
## VARS:
##       None.
##
##  Uninstall the bats test framework dependencies from /scripts/.

bats-uninstall: bats-pre-uninstall bats-do-uninstall bats-post-uninstall ## uninstall test dependencies for bats

bats-pre-install:

bats-post-install:

bats-do-install:
	@if [ -d $(CURDIR)/scripts/bats-core ]; then \
		echo "Skipping install as bats-core already exists"; \
	else \
		git clone --branch v1.4.1 https://github.com/bats-core/bats-core $(CURDIR)/scripts/bats-core; \
		git clone --branch v0.3.0 https://github.com/bats-core/bats-support $(CURDIR)/scripts/bats-support; \
		git clone --branch v2.0.0 https://github.com/bats-core/bats-assert $(CURDIR)/scripts/bats-assert; \
	fi

## TARGET: bats-install
## SYNOPSIS: make bats-install
## HOOKS: bats-pre-install, bats-post-install
## VARS:
##       None.
##
##  Install the bats test framework dependencies into /scripts/ from git.

bats-install: bats-pre-install bats-do-install bats-post-install ## install test dependencies for bats

## TARGET: bats-test
## SYNOPSIS: make bats-test
## HOOKS: bats-pre-test, bats-post-test
## VARS:
##       BATS_TEST_DIR=<directory containing the .bats test files - defaults to ./tests/unit>
##
##  Execute bats (Bash Automated Testing System - https://github.com/bats-core/bats-core) shell tests.

bats-pre-test:

bats-post-test:

bats-test: bats-pre-test bats-install bats-do-test bats-post-test ## Run unit tests using BATS

bats-do-test:
	@echo "bats-test: The CI_JOB_ID=$(CI_JOB_ID)"
	rm -rf $(CURDIR)/build
	mkdir -p $(CURDIR)/build
	@cd $(CURDIR)/build && \
	echo "bats-test: running tests in: $$(pwd) ..." && \
	export CI_JOB_ID=$(CI_JOB_ID) && \
	$(CURDIR)/scripts/bats-core/bin/bats \
		--jobs 1 \
		--report-formatter junit \
		-o $(CURDIR)/build $(CURDIR)/$(BATS_TEST_DIR)


# end of switch to suppress targets for help
endif
endif
