#!/usr/bin/env python3

import sys
import termios
import tty
import select

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class KeyboardController(Node):
    def __init__(self):
        super().__init__("keyboard_controller")

        self.cmd_pub = self.create_publisher(
            String,
            "/rov/controller/cmd",
            10,
        )

        self.get_logger().info("Keyboard Controller started")
        self.get_logger().info(
            "Controls: "
            "w=forward, s=backward, a=left, d=right, "
            "g=stop, i=up, k=pump stop, o=down, "
            "l=light toggle, q=quit"
        )

    def send_command(self, command: str):
        msg = String()
        msg.data = command
        self.cmd_pub.publish(msg)
        self.get_logger().info(f"Sent command: {command}")


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


def main(args=None):
    rclpy.init(args=args)

    node = KeyboardController()

    key_to_command = {
        "w": "FORWARD 1.0",
        "s": "BACKWARD 1.0",
        "a": "LEFT 1.0",
        "d": "RIGHT 1.0",
        "g": "STOP",
        "i": "UP",
        "k": "PUMP_STOP",
        "o": "DOWN",
        "l": "LIGHT_TOGGLE",
    }

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)

            key = get_key()

            if key is None:
                continue

            key = key.lower()

            if key == "q":
                node.send_command("STOP")
                print("\nQuit")
                break

            if key in key_to_command:
                command = key_to_command[key]
                print(f"\nCommand: {command}")
                node.send_command(command)

    except KeyboardInterrupt:
        node.send_command("STOP")

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()