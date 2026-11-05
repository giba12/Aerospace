# GoogleTest adapter (D1). Pinned by content hash, not just tag (NFR-009, OI-01).
include(FetchContent)
FetchContent_Declare(googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.17.0.tar.gz
  URL_HASH SHA256=65fab701d9829d38cb77c14acdc431d2108bfdbf8979e40eb8ae567edf10b27c
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

add_executable(sim_gtest_tests
  dynamics_tests.cpp
  estimator_tests.cpp
  kalman_tests.cpp
  mat2_tests.cpp
  output_util_tests.cpp
  interface_tests.cpp
  recorder_tests.cpp
  runner_tests.cpp
  sensor_tests.cpp
  sidecar_tests.cpp)
target_link_libraries(sim_gtest_tests PRIVATE sim_test_support GTest::gtest_main)
sim_enable_warnings(sim_gtest_tests)

include(GoogleTest)
# Register every TEST individually so `ctest -N` lists them all (TST-003).
gtest_discover_tests(sim_gtest_tests PROPERTIES LABELS "unit")

# JUnit XML with the requirement tags, for tools/req_trace.py (TST-004, TST-011). This runs the
# same suite once more in a single process. It costs well under a second and keeps the
# per-test listing above.
add_test(NAME junit.gtest
  COMMAND sim_gtest_tests --gtest_output=xml:${CMAKE_BINARY_DIR}/test-reports/gtest.xml)
set_tests_properties(junit.gtest PROPERTIES LABELS "report")
