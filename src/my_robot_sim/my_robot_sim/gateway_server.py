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
from std_msgs.msg import String


class ApiRosNode(Node):
    def __init__(self):
        super().__init__("rov_api_server")

        self.cmd_pub = self.create_publisher(
            String,
            "/rov/controller/cmd",
            10,
        )

        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.bridge = CvBridge()

        self.create_subscription(
            Image,
            "/rov/camera/image",
            self.camera_callback,
            10,
        )

        self.get_logger().info("ROS side of Flask API started")
        self.get_logger().info("Publishing commands to /rov/controller/cmd")

    def send_command(self, command: str) -> None:
        msg = String()
        msg.data = command
        self.cmd_pub.publish(msg)
        self.get_logger().info(f"API sent command: {command}")

    def camera_callback(self, msg: Image) -> None:
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            ok, jpeg = cv2.imencode(".jpg", frame)

            if ok:
                with self.frame_lock:
                    self.latest_frame = jpeg.tobytes()

        except Exception as e:
            self.get_logger().error(f"Camera conversion failed: {e}")


app = Flask(__name__)
ros_node = None


MOVEMENT_COMMANDS = {
    "forward": "FORWARD",
    "backward": "BACKWARD",
    "left": "LEFT",
    "right": "RIGHT",
}

SIMPLE_COMMANDS = {
    "stop": "STOP",
    "up": "UP",
    "pump_stop": "PUMP_STOP",
    "down": "DOWN",
    "light_toggle": "LIGHT_TOGGLE",
}


def build_command(message: str, velocity: float = 1.0) -> str:
    if message in MOVEMENT_COMMANDS:
        return f"{MOVEMENT_COMMANDS[message]} {velocity}"

    if message in SIMPLE_COMMANDS:
        return SIMPLE_COMMANDS[message]

    raise ValueError("Invalid message")


@app.route("/message", methods=["POST"])
def move():
    global ros_node

    data = request.get_json(silent=True) or {}

    message = str(data.get("message", "")).strip().lower()

    try:
        velocity = float(data.get("velocity", 1.0))
    except (TypeError, ValueError):
        return jsonify(
            {
                "ok": False,
                "error": "velocity must be a number",
            }
        ), 400

    allowed_messages = set(MOVEMENT_COMMANDS.keys()) | set(SIMPLE_COMMANDS.keys())

    if message not in allowed_messages:
        return jsonify(
            {
                "ok": False,
                "error": (
                    "message must be one of: "
                    "forward, backward, left, right, stop, "
                    "up, pump_stop, down, light_toggle"
                ),
            }
        ), 400

    command = build_command(message, velocity)
    ros_node.send_command(command)

    return jsonify(
        {
            "ok": True,
            "received": message,
            "velocity": velocity,
            "sent": command,
            "topic": "/rov/controller/cmd",
            "message_type": "std_msgs/String",
        }
    )


@app.route("/camera.jpg", methods=["GET"])
def camera_jpg():
    global ros_node

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
    global ros_node

    while True:
        with ros_node.frame_lock:
            frame = ros_node.latest_frame

        if frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )

        time.sleep(0.05)


@app.route("/camera.mjpg", methods=["GET"])
def camera_mjpg():
    return Response(
        mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/health", methods=["GET"])
def health():
    global ros_node

    with ros_node.frame_lock:
        has_camera = ros_node.latest_frame is not None

    return jsonify(
        {
            "ok": True,
            "camera": has_camera,
            "command_topic": "/rov/controller/cmd",
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