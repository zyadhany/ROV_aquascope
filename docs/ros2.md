# 🤖 ROS2 Core Control

## 📖 Introduction
The "Core Control" is the brain of the robot. It is written entirely in Python and uses the ROS2 framework. It consists of several independent programs (nodes) that run at the same time. These nodes read what the pilot wants to do, check the sensors, and figure out exactly how fast to spin the motors.

There are three main nodes responsible for making the robot move: the **MCU Gateway**, the **ROV Controller**, and the **Depth Controller**.

---

## 1. The MCU Gateway Node (`mcu_gateway.py`)
This node is the translator between the modern computer and the simple Microcontroller (Arduino/ESP32).

### How it reads data (From Robot to Computer)
1. The Microcontroller constantly sends raw text strings over the USB serial cable (e.g., `{"pressure": 110.5, "yaw": 45}`).
2. The Gateway Node reads this text string from the `/mcu/serial/out` topic.
3. It converts the text into proper ROS2 messages.
4. It publishes these messages to standard topics like `/rov/pressure/data` and `/rov/imu` so other nodes can easily read them.

### How it sends commands (From Computer to Robot)
1. The Gateway Node listens to command topics like `/rov/mcu/cmd/left_thruster` (which might have a value of `0.8` for 80% speed).
2. It takes that `0.8` value, packages it into a simple text string, and publishes it to the `/mcu/serial/in` topic.
3. The Microcontroller receives this string, understands it, and sends the correct electrical PWM signal to the physical motor.

---

## 2. The ROV Controller Node (`rov_controller.py`)
This node handles the pilot's steering commands. It acts as a "Mixer."

### How it works:
1. The pilot uses a joystick or a keyboard. Those tools send a single message like `"FORWARD 1.0"` or `"LEFT 0.5"` to the `/rov/controller/cmd` topic.
2. The **ROV Controller** receives `"FORWARD 1.0"`. It knows that to go forward, both the left and right thrusters must push forward.
3. It publishes `1.0` to the left thruster topic and `1.0` to the right thruster topic.
4. If it receives `"LEFT 0.5"`, it knows the robot needs to turn. It publishes `-0.5` (reverse) to the left thruster and `0.5` (forward) to the right thruster, causing the robot to spin in place.

It also handles simple on/off commands, like turning the headlights on or opening the robotic gripper.

---

## 3. The Depth Controller Node (`depth_controller.py`)
Keeping a robot at a perfectly stable depth underwater is very difficult. If you just leave the pump on, the robot will sink to the bottom. If you turn it off too late, it will bob up and down like a yo-yo.

To solve this, we built a **Pulse-Based Ballast Controller**. Instead of a standard PID controller, it uses a clever "State Machine" with three steps:

### The Three Steps (States):
1. **IDLE:** The robot is exactly at the "Target Depth". The pump is off. It does nothing until the robot drifts away from the target depth.
2. **PULSE:** If the robot drifts too high (above the "deadband" margin), the controller turns the pump ON for a very short burst of time (e.g., `0.5` seconds) to suck in water.
3. **OBSERVE:** The controller immediately turns the pump OFF and waits for a specific amount of time (e.g., `0.8` seconds). Because the robot is heavy and water is thick, it takes time for the robot to start sinking. The controller "observes" the depth sensor to see if that short `0.5` second pulse was enough to fix the depth. 
   * If the depth is fixing itself, it goes back to **IDLE**. 
   * If the robot is still too high, it goes back to **PULSE** and gives it another short burst.

This "Pulse and Wait" method prevents the robot from over-correcting and makes it incredibly stable underwater.

---

## 🎮 How to Control the Robot (Inputs)
We wrote two small nodes to let you send commands to the **ROV Controller**:
* **Keyboard (`keyboard.py`):** Opens a terminal window where you can press `W, A, S, D` to drive the robot. This is best for quick debugging on a laptop.
* **Joystick (`joystick_controller.py`):** Reads the analog sticks on a physical Xbox or PlayStation controller and sends precise speed and turning commands. This is best for real underwater missions.
