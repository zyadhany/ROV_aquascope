# ROV Aquascope: Core Software Documentation

[![ROS2](https://img.shields.io/badge/ROS2-Humble%20%2F%20Jazzy-blue)](https://docs.ros.org/)
[![Gazebo](https://img.shields.io/badge/Simulation-Gazebo%20Classic-orange)](https://gazebosim.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com/)

Welcome to the official software documentation for **ROV Aquascope**, a modular, fully integrated Remotely Operated Vehicle designed for underwater exploration and precise depth tracking. 

The software acts as the brain of the ROV, interacting with both the hardware and the user. It handles all the complex tasks while making it easy to scale and integrate with other systems.

---
## 🏗️ System Architecture Overview

```

┌────────────────────────────────────────────────────────┐
│                   1. USER INTERFACE                    │
│   Mobile App / Web Dashboard (HTML5/JS) <──> FastAPI   │
└───────────────────────────┬────────────────────────────┘
                            │ (WebSockets / REST API)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   2. ROS2 MIDDLEWARE                   │ 
└───────────────────────────┬────────────────────────────┘
                            │ (Serial / ROS2 Topics)
                            ▼
┌───────────────────────────┴────────────────────────────┐
│                    3. HARDWARE / SIM                   │  
└────────────────────────────────────────────────────────┘
```

1. **The UI Layer:** Mainly through a Mobile application for easy integration, supported by a fully controlled web dashboard with live monitoring.
2. **The Control Layer (ROS2 Core):** It's responsible for the main logic, control, and processing of data.
3. **The Hardware / Simulation:** It's the physical side which has all the sensors and actuators, and it can be simulated for software testing.

---

## 🛠️ Technical Key Features

* **Hardware Abstraction Layer (HAL):** The core autonomous logic and thruster-mixing nodes run identically across physical and simulated environments. The software does not distinguish between Gazebo joint commands and physical serial frames.
* **Bespoke Hydrodynamics Simulation:** Custom C++ Gazebo physics plugins written from scratch to simulate unique underwater assets, including active variable buoyancy (Ballast Tanks), hydrostatic pressure tracking, and scanning sonar acoustic arrays.
* **Production-Grade Fault Tolerance:** All critical ROS2 execution nodes utilize automatic lifecycle respawning (`respawn=True`) with configured initialization delays to prevent race conditions and recover instantly from runtime errors.
* **Low-Latency Telemetry Loop:** Replaced heavy generic third-party visualization tools with a lightweight, optimized WebSocket stream configuration capable of handling high-frequency sensor updates and visual diagnostics concurrently.

---

## 💻 Tech Stack & Dependencies

* **Middleware Framework:** ROS2 (Humble / Jazzy)
* **Simulation Engine:** Gazebo Classic 
* **Backend Utilities:** Python 3, FastAPI, WebSockets, `pyserial`
* **Frontend UI:** HTML5, CSS3 (Modern Flexbox/Grid Layouts), Vanilla JavaScript
* **Build System:** `colcon` with `ament_cmake` and `ament_python`

---

## ⚙️ Installation & Workspace Setup

### Prerequisites
Ensure your machine runs a supported Ubuntu Linux distribution with a verified ROS2 desktop installation.

```bash
# Update package lists
sudo apt update

# Install Gazebo ROS capabilities and standard bridges
sudo apt install ros-humble-ros-gz ros-humble-ros-gz-bridge -y

```

### Build Instructions

Clone the repository into a clean workspace structure and compile using the `colcon` toolchain:

```bash
# Initialize workspace directories
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

# Clone the project repository
git clone [https://github.com/YourUsername/YourRepoName.git](https://github.com/YourUsername/YourRepoName.git) .

# Resolve and build all packages
cd ~/ros2_ws
colcon build --symlink-install

# Source the overlay environment
source install/setup.bash

```

> 💡 **Pro-Tip:** Append `source ~/ros2_ws/install/setup.bash` to your `~/.bashrc` file to automatically source the workspace in every new terminal instance.

---

## 🚦 Execution Profiles (Quick Start)

The software provides two main launch profiles depending on whether you are running a virtual test flight or deploying on the physical vessel.

### Profile A: Digital Twin Sandbox (Simulation Mode)

Launches the Gazebo physics environment, loads the underwater world parameters, initializes custom physics loops, sets up bidirectional topic bridging, and runs a virtual microcontroller node to simulate real-world hardware feedback loops.

```bash
ros2 launch my_robot_sim sim.launch.py

```

### Profile B: Real-World Deployment (Hardware Mode)

Executed directly on the ROV's onboard companion computer (e.g., Raspberry Pi/Nvidia Jetson). It spins up the high-level controllers, opens the serial connection channel (`/dev/ttyUSB*`) to the primary microcontroller, and initializes the native hardware video encoding pipelines.

```bash
ros2 launch my_robot_sim rov.launch.py

```

---

## 📂 Subsystem Deep-Dives

Click on the links below or use the sidebar navigation to read the granular technical breakdowns of each sub-layer:

* **[📐 System Architecture](architecture.md)** — Detailed asynchronous network pipelines, execution data-flows, and full ROS2 topic/message type definitions.
* **[🌊 Gazebo Simulation Substack](https://www.google.com/search?q=gazebo.md)** — Mechanical SDF structures, hydrodynamic constants, and custom C++ plugin code analysis (Ballast, Sonar, Pressure).
* **[🧠 ROS2 Core Control Logic](https://www.google.com/search?q=ros2.md)** — Mathematical thruster mixing matrices, discrete-time depth holding PID algorithms, and serial string packet protocol formats.
* **[📺 Custom Web Dashboard](dashboard.md)** — Evaluation of the FastAPI backend routes, high-frequency WebSocket data multiplexing, and UI rendering optimizations.
* **[🔌 Physical Hardware Mapping](hardware.md)** — Pinout schematics, power distribution layout, and structural microcontroller specifications.

---

## 👥 Academic Profile & Team

* **Development Engineers:** Zyad Hany, Ahmed Abas, Nouran Yousry, Rowida Elsayed
* **Academic Institution:** Port Said University, Faculty of Engineering
* **Project Type:** Senior Graduation Project (Capstone Engineering Thesis)
* **Development Timeline:** 2024 – 2026
