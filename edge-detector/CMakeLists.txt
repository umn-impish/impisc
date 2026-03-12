cmake_minimum_required(VERSION 3.20)
set(CMAKE_C_STANDARD 23)

project(edge-detector)
# main executable
add_executable(detect-edge edge_detector.c)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GPIOD REQUIRED IMPORTED_TARGET libgpiod)

target_link_libraries(
    detect-edge
    PUBLIC
        PkgConfig::GPIOD
)

install(TARGETS detect-edge DESTINATION /usr/local/bin)
