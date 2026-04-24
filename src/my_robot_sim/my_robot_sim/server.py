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

        self.cmd_pub = self.create_publisher(String, "/rov/move_cmd", 10)

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


@app.route("/message", methods=["POST"])
def move():
    global ros_node

    data = request.get_json(silent=True) or {}
    direction = str(data.get("message", "")).strip().lower()

    allowed = {"forward", "backward", "left", "right", "stop"}
    if direction not in allowed:
        return jsonify(
            {
                "ok": False,
                "error": "direction must be one of: forward, backward, left, right, stop",
            }
        ), 400

    ros_node.send_command(direction)
    return jsonify({"ok": True, "sent": direction})


@app.route("/camera.jpg", methods=["GET"])
def camera_jpg():
    global ros_node

    with ros_node.frame_lock:
        frame = ros_node.latest_frame

    if frame is None:
        return jsonify({"ok": False, "error": "no camera frame yet"}), 503

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

    return jsonify({"ok": True, "camera": has_camera})


def spin_ros(node: Node):
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    executor.spin()


def main():
    global ros_node

    rclpy.init()
    ros_node = ApiRosNode()

    ros_thread = threading.Thread(target=spin_ros, args=(ros_node,), daemon=True)
    ros_thread.start()

    try:
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
    finally:
        ros_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()