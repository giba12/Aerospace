# The test framework is chosen here by one option (TST-002, IF-11). Nothing outside tests/
# changes when the framework changes: each adapter directory owns its own dependency.
set(SIM_TEST_FRAMEWORK "gtest" CACHE STRING "C++ test framework adapter (directory under tests/)")
set_property(CACHE SIM_TEST_FRAMEWORK PROPERTY STRINGS gtest)

if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${SIM_TEST_FRAMEWORK}/CMakeLists.txt")
  message(FATAL_ERROR "SIM_TEST_FRAMEWORK='${SIM_TEST_FRAMEWORK}' has no adapter in tests/${SIM_TEST_FRAMEWORK}/")
endif()

file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/test-reports")  # JUnit XML lands here (TST-004)

# Framework-neutral helpers and fakes (TST-006). Header-only; no framework headers allowed.
add_library(sim_test_support INTERFACE)
target_include_directories(sim_test_support INTERFACE support)
target_link_libraries(sim_test_support INTERFACE simcore)

add_subdirectory(${SIM_TEST_FRAMEWORK})

# System and Python tests (TST-008). They run through CTest like everything else, so `ctest`
# stays the single documented command. SIM_PYTHON must be the pinned virtual environment;
# if it is missing this test FAILS rather than being skipped silently.
set(SIM_PYTHON "${CMAKE_SOURCE_DIR}/.venv/bin/python" CACHE FILEPATH "Python from the pinned venv (README step 1)")
add_test(NAME system.pytest
  COMMAND ${SIM_PYTHON} -m pytest -q
          --junitxml=${CMAKE_BINARY_DIR}/test-reports/pytest.xml
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
set_tests_properties(system.pytest PROPERTIES
  ENVIRONMENT "SIM_BIN=$<TARGET_FILE:sim>"
  LABELS "system")
