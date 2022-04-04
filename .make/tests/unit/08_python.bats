#!/usr/bin/env bats

# Load a library from the `${BATS_TEST_DIRNAME}/test_helper' directory.
#
# Globals:
#   none
# Arguments:
#   $1 - name of library to load
# Returns:
#   0 - on success
#   1 - otherwise
load_lib() {
  local name="$1"
  load "../../scripts/${name}/load"
}

load_lib bats-support
load_lib bats-assert

@test 'PYTHON: package with metadata for tag_setup' {
    run make -f ../tests/Makefile python-build PYTHON_BUILD_TYPE=tag_setup
    echo "$output"
    assert_success
}

@test 'PYTHON: package with metadata for non_tag_setup' {
    run make -f ../tests/Makefile python-build PYTHON_BUILD_TYPE=non_tag_setup
    echo "$output"
    assert_success
}

@test 'PYTHON: package with metadata for tag_pyproject' {
    run make -f ../tests/Makefile python-build PYTHON_BUILD_TYPE=tag_pyproject
    echo "$output"
    assert_success
}

@test 'PYTHON: package with metadata for non_tag_pyproject' {
    run make -f ../tests/Makefile python-build PYTHON_BUILD_TYPE=non_tag_pyproject
    echo "$output"
    assert_success
}
