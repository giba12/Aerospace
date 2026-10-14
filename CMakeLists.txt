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
  src/recorder.cpp
  src/runner.cpp
  src/sensor.cpp)
target_include_directories(simcore PUBLIC include)
sim_enable_warnings(simcore)

# The executable is deliberately tiny: main() makes one call into simcore.
add_executable(sim src/main.cpp)
target_link_libraries(sim PRIVATE simcore)
sim_enable_warnings(sim)

if(SIM_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()
