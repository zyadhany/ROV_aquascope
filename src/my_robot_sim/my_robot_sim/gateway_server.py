#!/usr/bin/env python3

import threading
import time

import cv2
from cv_bridge import CvBridge
from flask import Flask, Response, jsonify, request

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from sensor_msgs.msg import Image
from std_msgs.msg import String, Float64, Int32


COMMAND_TOPIC = "/rov/controller/cmd"
CAMERA_TOPIC = "/rov/camera/image"

DEPTH_TOPIC = "/rov/depth/current"
FRONT_DISTANCE_TOPIC = "/rov/front_distance"
BATTERY_TOPIC = "/rov/battery"


class ApiRosNode(Node):
    def __init__(self):
        super().__init__("gateway_server")

        self.cmd_pub = self.create_publisher(
            String,
            COMMAND_TOPIC,
            10,
        )

        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.bridge = CvBridge()

        self.speed_percent = 30
        self.speed_lock = threading.Lock()

        self.depth = 0.0
        self.front_distance = 0.0
        self.battery = 0
        self.sensor_lock = threading.Lock()

        self.create_subscription(
            Image,
            CAMERA_TOPIC,
            self.camera_callback,
            10,
        )

        self.create_subscription(
            Float64,
            DEPTH_TOPIC,
            self.depth_callback,
            10,
        )

        self.create_subscription(
            Float64,
            FRONT_DISTANCE_TOPIC,
            self.front_distance_callback,
            10,
        )

        self.create_subscription(
            Int32,
            BATTERY_TOPIC,
            self.battery_callback,
            10,
        )

        self.get_logger().info("ROS side of Flask API started")
        self.get_logger().info(f"Publishing commands to {COMMAND_TOPIC}")

    def get_velocity(self) -> float:
        with self.speed_lock:
            return self.speed_percent / 100.0

    def set_speed_percent(self, speed: int) -> None:
        speed = max(0, min(100, speed))

        with self.speed_lock:
            self.speed_percent = speed

        self.get_logger().info(f"Speed set to {speed}%")

    def send_command(self, command: str) -> None:
        msg = String()
        msg.data = command
        self.cmd_pub.publish(msg)
        self.get_logger().info(f"API sent command: {command}")

    def send_movement_command(self, ros_command: str) -> str:
        velocity = self.get_velocity()
        command = f"{ros_command} {velocity}"
        self.send_command(command)
        return command

    def camera_callback(self, msg: Image) -> None:
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            ok, jpeg = cv2.imencode(".jpg", frame)

            if ok:
                with self.frame_lock:
                    self.latest_frame = jpeg.tobytes()

        except Exception as e:
            self.get_logger().error(f"Camera conversion failed: {e}")

    def depth_callback(self, msg: Float64) -> None:
        with self.sensor_lock:
            self.depth = float(msg.data)

    def front_distance_callback(self, msg: Float64) -> None:
        with self.sensor_lock:
            self.front_distance = float(msg.data)

    def battery_callback(self, msg: Int32) -> None:
        with self.sensor_lock:
            self.battery = int(msg.data)


app = Flask(__name__)
ros_node: ApiRosNode | None = None


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/sensors", methods=["GET"])
def sensors_data():
    with ros_node.sensor_lock:
        depth = ros_node.depth
        front_distance = ros_node.front_distance

    return jsonify(
        {
            "ok": True,
            "depth": depth,
            "front_distance": front_distance,
        }
    )


@app.route("/battery", methods=["GET"])
def battery_data():
    with ros_node.sensor_lock:
        battery = ros_node.battery

    return jsonify(
        {
            "ok": True,
            "battery": battery,
        }
    )


@app.route("/speed", methods=["POST"])
def set_speed():
    data = request.get_json(silent=True) or {}

    try:
        speed = int(data.get("speed", 30))
    except (TypeError, ValueError):
        return jsonify(
            {
                "ok": False,
                "error": "speed must be a number from 0 to 100",
            }
        ), 400

    if speed < 0 or speed > 100:
        return jsonify(
            {
                "ok": False,
                "error": "speed must be between 0 and 100",
            }
        ), 400

    ros_node.set_speed_percent(speed)

    return jsonify(
        {
            "ok": True,
            "speed": speed,
            "velocity": speed / 100.0,
        }
    )


def command_response(app_command: str, sent_command: str):
    return jsonify(
        {
            "ok": True,
            "command": app_command,
            "sent": sent_command,
            "topic": COMMAND_TOPIC,
            "message_type": "std_msgs/String",
        }
    )


@app.route("/forward", methods=["POST"])
def forward():
    sent = ros_node.send_movement_command("FORWARD")
    return command_response("forward", sent)


@app.route("/backward", methods=["POST"])
def backward():
    sent = ros_node.send_movement_command("BACKWARD")
    return command_response("backward", sent)


@app.route("/left", methods=["POST"])
def left():
    sent = ros_node.send_movement_command("LEFT")
    return command_response("left", sent)


@app.route("/right", methods=["POST"])
def right():
    sent = ros_node.send_movement_command("RIGHT")
    return command_response("right", sent)


@app.route("/up", methods=["POST"])
@app.route("/moveUp", methods=["POST"])
@app.route("/move_up", methods=["POST"])
@app.route("/move-up", methods=["POST"])
def move_up():
    ros_node.send_command("UP")
    return command_response("up", "UP")


@app.route("/down", methods=["POST"])
@app.route("/moveDown", methods=["POST"])
@app.route("/move_down", methods=["POST"])
@app.route("/move-down", methods=["POST"])
def move_down():
    ros_node.send_command("DOWN")
    return command_response("down", "DOWN")


@app.route("/stop", methods=["POST"])
def stop():
    ros_node.send_command("STOP")
    return command_response("stop", "STOP")


@app.route("/pump_stop", methods=["POST"])
@app.route("/pump-stop", methods=["POST"])
def pump_stop():
    ros_node.send_command("PUMP_STOP")
    return command_response("pump_stop", "PUMP_STOP")


@app.route("/light_on", methods=["POST"])
@app.route("/light-on", methods=["POST"])
@app.route("/light/on", methods=["POST"])
def light_on():
    ros_node.send_command("LIGHT_ON")
    return command_response("light_on", "LIGHT_ON")


@app.route("/light_off", methods=["POST"])
@app.route("/light-off", methods=["POST"])
@app.route("/light/off", methods=["POST"])
def light_off():
    ros_node.send_command("LIGHT_OFF")
    return command_response("light_off", "LIGHT_OFF")


@app.route("/light_toggle", methods=["POST"])
@app.route("/light-toggle", methods=["POST"])
def light_toggle():
    ros_node.send_command("LIGHT_TOGGLE")
    return command_response("light_toggle", "LIGHT_TOGGLE")


@app.route("/message", methods=["POST"])
def message_compatibility():
    """
    Old endpoint kept for testing/backward compatibility.

    Body example:
    {
        "message": "forward",
        "velocity": 0.5
    }
    """
    data = request.get_json(silent=True) or {}

    message = str(data.get("message", "")).strip().lower()

    movement_commands = {
        "forward": "FORWARD",
        "backward": "BACKWARD",
        "left": "LEFT",
        "right": "RIGHT",
    }

    simple_commands = {
        "stop": "STOP",
        "up": "UP",
        "down": "DOWN",
        "pump_stop": "PUMP_STOP",
        "light_on": "LIGHT_ON",
        "light_off": "LIGHT_OFF",
        "light_toggle": "LIGHT_TOGGLE",
    }

    if message in movement_commands:
        try:
            velocity = float(data.get("velocity", ros_node.get_velocity()))
        except (TypeError, ValueError):
            return jsonify(
                {
                    "ok": False,
                    "error": "velocity must be a number",
                }
            ), 400

        sent = f"{movement_commands[message]} {velocity}"
        ros_node.send_command(sent)
        return command_response(message, sent)

    if message in simple_commands:
        sent = simple_commands[message]
        ros_node.send_command(sent)
        return command_response(message, sent)

    return jsonify(
        {
            "ok": False,
            "error": (
                "message must be one of: forward, backward, left, right, "
                "stop, up, down, pump_stop, light_on, light_off, light_toggle"
            ),
        }
    ), 400


@app.route("/camera.jpg", methods=["GET"])
def camera_jpg():
    with ros_node.frame_lock:
        frame = ros_node.latest_frame

    if frame is None:
        return jsonify(
            {
                "ok": False,
                "error": "no camera frame yet",
            }
        ), 503

    return Response(frame, mimetype="image/jpeg")


def mjpeg_generator():
    while True:
        with ros_node.frame_lock:
            frame = ros_node.latest_frame

        if frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )

        time.sleep(0.05)


@app.route("/video_feed", methods=["GET"])
def video_feed():
    return Response(
        mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/health", methods=["GET"])
def health():
    with ros_node.frame_lock:
        has_camera = ros_node.latest_frame is not None

    with ros_node.speed_lock:
        speed = ros_node.speed_percent

    return jsonify(
        {
            "ok": True,
            "camera": has_camera,
            "speed": speed,
            "velocity": speed / 100.0,
            "command_topic": COMMAND_TOPIC,
            "camera_topic": CAMERA_TOPIC,
            "depth_topic": DEPTH_TOPIC,
            "front_distance_topic": FRONT_DISTANCE_TOPIC,
            "battery_topic": BATTERY_TOPIC,
            "message_type": "std_msgs/String",
        }
    )


def spin_ros(node: Node):
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    executor.spin()


def main():
    global ros_node

    rclpy.init()
    ros_node = ApiRosNode()

    ros_thread = threading.Thread(
        target=spin_ros,
        args=(ros_node,),
        daemon=True,
    )
    ros_thread.start()

    try:
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            threaded=True,
        )

    finally:
        ros_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()