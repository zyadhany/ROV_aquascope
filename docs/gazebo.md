# 🌊 Gazebo Simulation & Custom Plugins

## 📖 Introduction
Testing a robot underwater is difficult and risky. If a code error makes the robot crash into the bottom of a pool, the robot could be destroyed. To solve this, we created a **Digital Twin** (a virtual copy) of the ROV using a simulation software called **Gazebo**.

The Gazebo simulator creates a virtual pool with gravity, water resistance, and collision physics. We can test our Python code on this virtual robot before we ever put the real robot in the water.

---

## 🛠️ The ROV 3D Model
Inside the folder `src/my_robot_sim/models/rov/`, we have a file called `model.sdf`. "SDF" stands for Simulation Description Format. 

This file defines the physical shape of the robot. It tells Gazebo:
* How heavy the robot is (its mass).
* The size and shape of the hull (so it collides properly with walls).
* Where exactly the left and right thrusters are attached to the body.
* Where the camera is located on the front of the robot.

---

## 🔌 Custom Physics Plugins (C++)
Gazebo is very good at simulating cars and drones, but it needs help simulating water. To make our simulation realistic, we wrote several custom **C++ Plugins** located in the `src/my_gz_plugins/` folder. 

These plugins act as the "laws of physics" for our underwater world:

### 1. Ballast Tank Plugin (`BallastTankPlugin.cc`)
* **What it does:** In the real world, the robot sinks by sucking water into a tank, which makes the robot heavier. This plugin simulates that exactly.
* **How it works:** When the Python "Depth Controller" says "Turn on the pump", this C++ plugin slowly increases the mass (weight) of the 3D model in Gazebo. When the model gets heavier, gravity pulls it down. When the pump reverses, it decreases the mass, and the robot floats up.

### 2. Pressure Sensor Plugin (`PressureSensorPlugin.cc`)
* **What it does:** Simulates an underwater hydrostatic pressure sensor.
* **How it works:** It constantly looks at how deep the robot is (the Z-axis coordinate in the 3D world). As the robot goes deeper, the plugin calculates the water pressure at that depth and sends this data back to the ROS2 topics. It even adds a little bit of random "noise" to make it act like a real, imperfect sensor.

### 3. Scanning Sonar Plugin (`ScanningSonarPlugin.cc`)
* **What it does:** Simulates an acoustic sonar that can see in dark or muddy water.
* **How it works:** It shoots invisible "rays" out from the front of the robot. If a ray hits a virtual rock or wall, it calculates the distance and sends the measurement back to the robot, allowing it to dodge obstacles.

### 4. Spot Light Plugin (`SpotLightPlugin.cc`)
* **What it does:** Simulates the bright LED headlights on the front of the robot.
* **How it works:** It allows the operator to turn on a virtual light source in Gazebo to light up dark underwater areas for the camera.

### 5. ROV Gripper Plugin (`RovGripperPlugin.cc`)
* **What it does:** Simulates a robotic arm.
* **How it works:** Allows the robot to "grab" and hold onto other 3D objects in the simulation world.

---

## 🚀 How to Run the Simulation

Running the simulation is very simple.

**Step 1:** Open a terminal and source your workspace.
```bash
source ~/ros2_ws/install/setup.bash
```

**Step 2:** Run the simulation launch file.
```bash
ros2 launch my_robot_sim sim.launch.py
```

**What happens next?**
1. Gazebo will open a 3D window showing a virtual underwater environment (`empty.world`).
2. The ROV 3D model will be spawned in the center of the water.
3. All the C++ physics plugins will start calculating buoyancy and water pressure.
4. Your ROS2 Python nodes will automatically connect to this virtual robot instead of the real one. You can now use your keyboard or joystick to drive the virtual ROV!
