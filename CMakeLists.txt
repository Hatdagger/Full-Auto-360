# fullauto - ReXGlue recompiled project for Full Auto (Xbox 360)
#
# The SDK package provides rexglue_project and the rexglue_setup_* functions.
# build.bat / scripts/build-windows.ps1 download the SDK into sdk/ and point CMake at it.

cmake_minimum_required(VERSION 3.25)
project(fullauto LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if (REXSDK_DIR)
  add_subdirectory("${REXSDK_DIR}" rexglue-sdk)
else ()
  find_package(rexglue 0.11.0 REQUIRED CONFIG)
endif ()
rexglue_project(fullauto OUTPUT_DIR generated/default)

# Host sources. src/main.cpp stays on the executable.
set(FULLAUTO_HOST_SOURCES src/fullauto_hooks.cpp)

# Test input for headless boot tests (docs/TESTING.md). Off in normal builds.
option(FULLAUTO_TEST_INPUT "Build the test input hooks (FULLAUTO_TEST_AUTOPRESS)" OFF)
if (FULLAUTO_TEST_INPUT)
  list(APPEND FULLAUTO_HOST_SOURCES tests/test_input.cpp)
endif ()

# OBJECT and never STATIC, an archive drops the REX_EXPORT symbols.
add_library(fullauto_common OBJECT ${FULLAUTO_HOST_SOURCES})
rexglue_setup_host_library(fullauto_common)

if (WIN32)
  add_executable(fullauto WIN32 src/main.cpp)
else ()
  add_executable(fullauto src/main.cpp)
endif ()

rexglue_setup_target(fullauto)
target_link_libraries(fullauto PRIVATE fullauto_common)
