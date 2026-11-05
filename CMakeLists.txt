cmake_minimum_required(VERSION 3.20)
project(sensor_sim VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING "Build type" FORCE)
endif()

option(SIM_WARNINGS_AS_ERRORS "Treat compiler warnings as errors (NFR-001)" ON)
option(SIM_BUILD_TESTS "Build the test suites" ON)
option(SIM_SANITIZE "Build everything with AddressSanitizer and UndefinedBehaviorSanitizer (NFR-007)" OFF)
option(SIM_COVERAGE "Instrument for line coverage with gcov; see `cmake --build build --target coverage` (NFR-008)" OFF)

if(SIM_SANITIZE AND SIM_COVERAGE)
  message(FATAL_ERROR "SIM_SANITIZE and SIM_COVERAGE cannot be combined: build them in separate directories")
endif()

# Whole-build flags go on BEFORE any target exists so that the fetched test framework and every
# first-party target are instrumented the same way. Any sanitizer finding aborts the process
# (-fno-sanitize-recover) so a test cannot pass while hiding one.
if(SIM_SANITIZE)
  add_compile_options(-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address,undefined)
endif()

# Coverage needs unoptimised code or the line numbers do not match the source. GCC 13 can report
# line and branch coverage only (condition coverage needs GCC 14; risk R-08).
if(SIM_COVERAGE)
  add_compile_options(--coverage -O0 -g)
  add_link_options(--coverage)
endif()

# One place defines the warning policy; every first-party target calls it.
function(sim_enable_warnings target)
  target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  if(SIM_WARNINGS_AS_ERRORS)
    target_compile_options(${target} PRIVATE -Werror)
  endif()
endfunction()

# All logic lives in this library (TST-001, DD-001). It depends on the standard library only (NFR-002).
add_library(simcore STATIC
  src/cli.cpp
  src/dynamics.cpp
  src/estimator.cpp
  src/kalman.cpp
  src/output_util.cpp
  src/recorder.cpp
  src/runner.cpp
  src/sensor.cpp
  src/sidecar.cpp)
target_include_directories(simcore PUBLIC include)

# Source revision for the sidecar's build info (OUT-003). Read when CMake configures, so it can be
# stale after a later commit until you re-run cmake; the sidecar says `null` if git is unavailable.
execute_process(COMMAND git describe --always --dirty --abbrev=12
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
  OUTPUT_VARIABLE SIM_SOURCE_REVISION OUTPUT_STRIP_TRAILING_WHITESPACE
  RESULT_VARIABLE SIM_GIT_RESULT ERROR_QUIET)
if(SIM_GIT_RESULT EQUAL 0 AND SIM_SOURCE_REVISION)
  set_source_files_properties(src/sidecar.cpp PROPERTIES
    COMPILE_DEFINITIONS "SIM_SOURCE_REVISION=\"${SIM_SOURCE_REVISION}\"")
endif()
sim_enable_warnings(simcore)

# The executable is deliberately tiny: main() makes one call into simcore.
add_executable(sim src/main.cpp)
target_link_libraries(sim PRIVATE simcore)
sim_enable_warnings(sim)

if(SIM_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()

# `cmake --build build --target coverage` summarises line and branch coverage of simcore after the
# tests have run (NFR-008: a goal of 90 % reported in CI, never a gate). SIM_PYTHON is the pinned
# virtual environment, which carries gcovr. SIM_GCOV must match the compiler's gcov.
if(SIM_COVERAGE)
  set(SIM_GCOV "gcov" CACHE STRING "gcov executable matching the compiler (for example gcov-13)")
  set(SIM_COVERAGE_DIR "${CMAKE_BINARY_DIR}/coverage")
  add_custom_target(coverage
    COMMAND ${CMAKE_COMMAND} -E make_directory ${SIM_COVERAGE_DIR}
    COMMAND ${SIM_PYTHON} -m gcovr --root ${CMAKE_SOURCE_DIR} --object-directory ${CMAKE_BINARY_DIR}
            --gcov-executable ${SIM_GCOV} --exclude-throw-branches
            --filter ${CMAKE_SOURCE_DIR}/src/ --filter ${CMAKE_SOURCE_DIR}/include/
            --print-summary --txt ${SIM_COVERAGE_DIR}/summary.txt
            --xml ${SIM_COVERAGE_DIR}/coverage.xml --html-details ${SIM_COVERAGE_DIR}/index.html
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "Coverage of src/ and include/ (run ctest first); report in ${SIM_COVERAGE_DIR}"
    VERBATIM)
endif()
