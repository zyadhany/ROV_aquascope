# 🔌 Physical Hardware Setup

## 📖 Introduction
After you have successfully tested the code in the Gazebo Simulation, it is time to put the code on the real robot. This document explains the steps to connect the physical hardware and run the real-world launch profile.

---

## 🛠️ The Hardware Components

To run the physical robot, you need the following main components properly wired inside the waterproof hull:

1. **The Companion Computer:** This is usually a Raspberry Pi 4, Jetson Nano, or a small laptop running Linux (Ubuntu) and ROS2. This computer runs all the Python nodes and the Web Dashboard.
2. **The Microcontroller (MCU):** This is usually an Arduino Mega or ESP32. It is connected to the Companion Computer via a standard USB cable.
3. **The Thrusters:** Brushless underwater motors connected to Electronic Speed Controllers (ESCs). The ESCs are plugged into the PWM pins on the Microcontroller.
4. **The Sensors:** 
   * A USB Web Camera plugged directly into the Companion Computer.
   * A Pressure Sensor (e.g., MS5837) connected to the Microcontroller via I2C pins.
   * An IMU (e.g., MPU6050 or BNO055) connected to the Microcontroller via I2C pins.
5. **The Power Supply:** A large LiPo battery to provide power to the thrusters and the electronics.

---

## 🚀 Step-by-Step Setup Guide

Follow these exact steps to launch the software on the physical robot.

### Step 1: Connect the Hardware
1. Ensure the robot's main battery is fully charged and plugged in.
2. Plug the USB Camera into the Companion Computer.
3. Plug the Microcontroller into the Companion Computer using the USB cable.

### Step 2: Find the USB Port
The Companion Computer needs to know which USB port the Microcontroller is plugged into.
Open a terminal on the Companion Computer and run:
```bash
ls /dev/ttyUSB*
```
*Note: Sometimes it shows up as `/dev/ttyACM0`.*
Ensure your `mcu_gateway.py` code is configured to listen to this exact port.

### Step 3: Give USB Permissions
Linux computers block access to USB ports by default for security. You must give the system permission to read the Microcontroller.
Run this command (replace `ttyUSB0` with your actual port):
```bash
sudo chmod 666 /dev/ttyUSB0
```

### Step 4: Run the Real-World Launch File
Now that the hardware is connected and the computer has permission to talk to it, you can start the software.

Open a terminal, source your workspace, and run the real-world launch file:
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch my_robot_sim rov.launch.py
```

### Step 5: Start the Dashboard and Test
Once the launch file says "Started", open your web browser (or a tablet on the same Wi-Fi network).
1. Go to `http://<ROBOT_IP_ADDRESS>:8000`.
2. Check the live video feed. Can you see out of the camera?
3. Check the sensor data. Does the pressure and depth show correct numbers?
4. **Dry Test:** Use the joystick or keyboard to send a tiny forward command (like 10% speed) for one second. Listen to hear if the physical thrusters spin.

If everything works, seal the waterproof hull tightly. You are ready to dive!
