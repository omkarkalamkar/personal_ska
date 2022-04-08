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

@test 'Conan: correct package' {
    run make -f ../tests/Makefile conan-package CONAN_PKG=ska-conan-correct
    assert_success
}

@test 'Conan: package missing metadata ' {
    run make -f ../tests/Makefile conan-package CONAN_PKG=ska-conan-missing-metadata
    assert_output -p 'buildConan: Missing self.copy("MANIFEST.skao.int", src="src") line in the conanfile.py'
}

@test 'Conan: package missing name ' {
    run make -f ../tests/Makefile conan-package CONAN_PKG=ska-conan-missing-name
    assert_output -p "buildConan: Missing Name or Version in conanfile.py"
}