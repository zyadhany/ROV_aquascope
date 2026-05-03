cmake_minimum_required(VERSION 3.8)
project(my_gz_plugins)

find_package(ament_cmake REQUIRED)

find_package(gz-sim8 REQUIRED)
find_package(gz-plugin2 REQUIRED COMPONENTS register)
find_package(gz-transport13 REQUIRED)
find_package(gz-msgs10 REQUIRED)
find_package(gz-math7 REQUIRED)

add_library(BallastTankPlugin SHARED
  src/BallastTankPlugin.cc
)

add_library(PressureSensorPlugin SHARED
  src/PressureSensorPlugin.cc
)

add_library(SpotLightPlugin SHARED
  src/SpotLightPlugin.cc
)

add_library(ScanningSonarPlugin SHARED
  src/ScanningSonarPlugin.cc
)

add_library(RovGripperPlugin SHARED
  src/RovGripperPlugin.cc
)

set_property(TARGET BallastTankPlugin PROPERTY CXX_STANDARD 17)
set_property(TARGET PressureSensorPlugin PROPERTY CXX_STANDARD 17)
set_property(TARGET SpotLightPlugin PROPERTY CXX_STANDARD 17)
set_property(TARGET ScanningSonarPlugin PROPERTY CXX_STANDARD 17)
set_property(TARGET RovGripperPlugin PROPERTY CXX_STANDARD 17)

target_link_libraries(BallastTankPlugin
  gz-sim8::gz-sim8
  gz-plugin2::gz-plugin2
  gz-plugin2::register
  gz-transport13::gz-transport13
  gz-msgs10::gz-msgs10
  gz-math7::gz-math7
)

target_link_libraries(PressureSensorPlugin
  gz-sim8::gz-sim8
  gz-plugin2::gz-plugin2
  gz-plugin2::register
  gz-transport13::gz-transport13
  gz-msgs10::gz-msgs10
  gz-math7::gz-math7
)

target_link_libraries(SpotLightPlugin
  gz-sim8::gz-sim8
  gz-plugin2::gz-plugin2
  gz-plugin2::register
  gz-transport13::gz-transport13
  gz-msgs10::gz-msgs10
  gz-math7::gz-math7
)

target_link_libraries(ScanningSonarPlugin
  gz-sim8::gz-sim8
  gz-plugin2::gz-plugin2
  gz-plugin2::register
  gz-transport13::gz-transport13
  gz-msgs10::gz-msgs10
  gz-math7::gz-math7
)

target_link_libraries(RovGripperPlugin
  gz-sim8::gz-sim8
  gz-plugin2::gz-plugin2
  gz-plugin2::register
  gz-transport13::gz-transport13
  gz-msgs10::gz-msgs10
  gz-math7::gz-math7
)

install(TARGETS
  BallastTankPlugin
  PressureSensorPlugin
  SpotLightPlugin
  ScanningSonarPlugin
  RovGripperPlugin
  LIBRARY DESTINATION lib
)

ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/env-hooks/my_gz_plugins.sh.in")

ament_package()
