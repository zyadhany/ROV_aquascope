# 📊 Custom Web Dashboard

## 📖 Introduction
Most industrial robots use heavy software (like Rviz or QGroundControl) to monitor the robot's status. We wanted something lighter, faster, and easier to use.

We built a custom Web Dashboard. Because it is a website, you can open it on any laptop, tablet, or even a smartphone that is connected to the robot's Wi-Fi network. You do not need to install any special software—just open your web browser (like Chrome or Safari).

---

## 🛠️ How It Works (The Architecture)
The dashboard has two main parts: the **Backend** (the server) and the **Frontend** (what the user sees).

### 1. The Backend Server (Python & FastAPI)
The Backend is the bridge between the ROS2 robot and the Web Browser.
* **What it does:** It runs a fast web server using a Python library called `FastAPI`. 
* **Connecting to the Robot:** It constantly listens to the ROS2 topics (like the camera feed, current depth, and pressure data).
* **Serving the Website:** When you open your web browser and type in the robot's IP address, the Backend server sends the HTML, CSS, and Javascript files to your screen.
* **The APIs:** It creates "API Endpoints" (like `/api/nodes` or `/api/flowchart`). The Frontend can ask these endpoints for live data (like "What is the pressure right now?") and the Backend will reply instantly.

### 2. The Frontend UI (HTML, CSS, JavaScript)
The Frontend is the actual user interface you click on. We built it using standard "Vanilla" web technologies, meaning we didn't use complicated frameworks like React or Angular. This keeps the code simple and easy to edit.

* **HTML (`index.html`):** This is the skeleton of the page. It defines where the video player goes, where the buttons are, and where the text boxes for sensor data live.
* **CSS (`style.css`):** This makes the dashboard look beautiful. We used modern design techniques like dark mode colors, smooth rounded corners, and glowing hover effects on buttons.
* **JavaScript (`app.js`):** This is the engine of the page. It runs in your browser and constantly asks the Backend API for new data (every fraction of a second). When it gets new data, it automatically updates the numbers on your screen without having to refresh the page.

---

## 🗺️ The Live Flowchart Feature
One of the most unique features of our dashboard is the **Live Flowchart**.

Inside the codebase, there is a file called `flowchart.md`. This file defines how the entire robot is wired together. 
When the dashboard loads, it reads this file and draws a beautiful, interactive diagram on the screen. It shows the Microcontroller, the Thrusters, the Pump, and the Sensors.

Because it reads this file automatically, if we add a new sensor to the robot tomorrow, we just update the text file, and the dashboard will automatically draw the new sensor on the screen!

---

## 🚀 How to Run the Dashboard

If you used the standard `sim.launch.py` or `rov.launch.py` commands, the dashboard usually starts automatically! 

However, if you want to run it manually or test it, follow these steps:

**Step 1:** Open a new terminal and source your workspace.
```bash
source ~/ros2_ws/install/setup.bash
```

**Step 2:** Run the dashboard node.
```bash
ros2 run rov_dashboard dashboard_backend
```

**Step 3:** Open your web browser.
* Type `http://localhost:8000` (if you are on the same computer).
* Type `http://<ROBOT_IP_ADDRESS>:8000` (if you are on a different device).

You will immediately see the live camera feed and sensor data!
