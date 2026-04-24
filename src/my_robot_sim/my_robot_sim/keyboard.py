#!/usr/bin/env python3

import sys
import threading
import termios
import tty
import select

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String


class KeyboardRosNode(Node):
    def __init__(self):
        super().__init__("rov_keyboard_controller")

        self.cmd_pub = self.create_publisher(String, "/rov/move_cmd", 10)

        self.get_logger().info("ROS keyboard controller started")
        self.get_logger().info(
            "Controls: "
            "w=forward, s=backward, a=left, d=right, g=stop, "
            "i=up, k=hold, o=down, q=quit"
        )

    def send_move_command(self, command: str) -> None:
        msg = String()
        msg.data = command
        self.cmd_pub.publish(msg)
        self.get_logger().info(f"Sent move command: {command}")


def spin_ros(node: Node):
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        executor.shutdown()


def get_key(timeout=0.1):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            return sys.stdin.read(1)
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def main():
    rclpy.init()
    ros_node = KeyboardRosNode()

    ros_thread = threading.Thread(target=spin_ros, args=(ros_node,), daemon=True)
    ros_thread.start()

    key_to_move_command = {
        "w": "forward",
        "s": "backward",
        "a": "left",
        "d": "right",
        "g": "stop",
        "i": "up",
        "k": "hold",
        "o": "down",
    }

    try:
        while True:
            key = get_key()

            if key is None:
                continue

            key = key.lower()

            if key == "q":
                ros_node.send_move_command("stop")
                print("\nQuit")
                break

            if key in key_to_move_command:
                command = key_to_move_command[key]
                print(f"\nMove command: {command}")
                ros_node.send_move_command(command)

    finally:
        ros_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()