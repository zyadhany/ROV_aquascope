cmake_minimum_required(VERSION 3.8)
project(devices)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(gz-sim8 REQUIRED)
find_package(gz-plugin2 REQUIRED)
find_package(gz-transport13 REQUIRED)
find_package(gz-msgs10 REQUIRED)

add_library(HeadlightToggle SHARED
  src/HeadlightToggle.cpp
)

target_link_libraries(HeadlightToggle
  gz-sim8::gz-sim8
  gz-plugin2::gz-plugin2
  gz-transport13::gz-transport13
  gz-msgs10::gz-msgs10
)


install(TARGETS HeadlightToggle
  LIBRARY DESTINATION lib
)

install(DIRECTORY models
  DESTINATION share/${PROJECT_NAME}
)

ament_package()