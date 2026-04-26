name: Microcontroller
id: hardware/microcontroller
type: hardware

name: Left Thruster
id: hardware/actuators/left_thruster
type: hardware

name: Right Thruster
id: hardware/actuators/right_thruster
type: hardware

name: Pump
id: hardware/actuators/pump
type: hardware

name: Light
id: hardware/actuators/light
type: hardware

name: Camera
id: hardware/sensors/camera
type: hardware

name: IMU
id: hardware/sensors/imu
type: hardware

name: Pressure Sensor
id: hardware/sensors/pressure_sensor
type: hardware

name: MCU Gateway
id: nodes/mcu_gateway
type: node

name: Camera Streamer
id: nodes/camera_streamer
type: node

name: Camera Image
id: topics/camera/image
type: topic
ros2_topic: /rov/camera/image

name: Pressure Data
id: topics/pressure/data
type: topic
ros2_topic: /rov/pressure/data

name: Current Depth
id: topics/depth/current
type: topic
ros2_topic: /rov/depth/current

name: Target Depth
id: topics/depth/target
type: topic
ros2_topic: /rov/depth/target

name: Depth Error
id: topics/depth/error
type: topic
ros2_topic: /rov/depth/error

name: Left Thruster Command
id: topics/cmd/left_thruster
type: topic
ros2_topic: /rov/mcu/cmd/left_thruster

name: Right Thruster Command
id: topics/cmd/right_thruster
type: topic
ros2_topic: /rov/mcu/cmd/right_thruster

name: Pump Command
id: topics/cmd/pump
type: topic
ros2_topic: /rov/mcu/cmd/pump

name: Light Command
id: topics/cmd/light
type: topic
ros2_topic: /rov/mcu/cmd/light

name: Depth Controller
id: nodes/depth_controller
type: node

name: ROV Controller
id: nodes/rov_controller
type: node

name: Keyboard Controller
id: nodes/keyboard_controller
type: node

name: Control Command
id: topics/control/command
type: topic
ros2_topic: /rov/controller/cmd

name: Mobile App Controller
id: nodes/mobile_app_controller
type: node


connections:

microcontroller -- control signal --> right_thruster
microcontroller -- control signal --> left_thruster
microcontroller -- control signal --> light
microcontroller -- control signal --> pump

pressure_sensor -- pressure data --> microcontroller
imu -- imu data --> microcontroller

microcontroller <-- serial connection --> mcu_gateway

camera -- raw video/image data --> camera_streamer
camera_streamer -- published video/image data --> camera_image

mcu_gateway -- pressure data --> pressure_data
mcu_gateway -- current depth --> current_depth
cmd_left_thruster -- command value --> mcu_gateway
cmd_right_thruster -- command value --> mcu_gateway
cmd_pump -- command value --> mcu_gateway
cmd_light -- control signal --> mcu_gateway

depth_controller << -- subscribed -- current_depth
depth_controller << -- subscribed -- target_depth
depth_controller -- publishes --> depth_error
depth_controller -- publishes --> cmd_pump

rov_controller << -- subscribed -- cmd_control_signal
rov_controller -- publishes --> cmd_left_thruster
rov_controller -- publishes --> cmd_right_thruster
rov_controller -- publishes --> cmd_light
rov_controller -- publishes --> target_depth

keyboard_controller -- publishes --> cmd_control_signal
mobile_app_controller -- publishes --> cmd_control_signal