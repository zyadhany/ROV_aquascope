#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from std_msgs.msg import String, Float64, Int32, Bool


class RovController(Node):
    def __init__(self):
        super().__init__("rov_controller")

        self.cmd_sub = self.create_subscription(
            String,
            "/rov/controller/cmd",
            self.cmd_callback,
            10,
        )

        self.left_pub = self.create_publisher(
            Float64,
            "/rov/mcu/cmd/left_thruster",
            10,
        )

        self.right_pub = self.create_publisher(
            Float64,
            "/rov/mcu/cmd/right_thruster",
            10,
        )

        self.pump_pub = self.create_publisher(
            Int32,
            "/rov/mcu/cmd/pump",
            10,
        )

        self.light_pub = self.create_publisher(
            Bool,
            "/rov/mcu/cmd/light",
            10,
        )

        self.target_depth_pub = self.create_publisher(
            Float64,
            "/rov/depth/target",
            10,
        )

        self.light_on = False

        self.get_logger().info("ROV Controller started")

    def cmd_callback(self, msg: String):
        command = msg.data.strip()
        if not command:
            return

        parts = command.split()
        cmd = parts[0].upper()

        try:
            speed = float(parts[1]) if len(parts) > 1 else 1.0

            if cmd == "FORWARD":
                self.publish_thrusters(speed, speed)

            elif cmd == "BACKWARD":
                self.publish_thrusters(-speed, -speed)

            elif cmd == "LEFT":
                self.publish_thrusters(-speed, speed)

            elif cmd == "RIGHT":
                self.publish_thrusters(speed, -speed)

            elif cmd == "LEFT_THRUST":
                self.publish_left(speed)

            elif cmd == "RIGHT_THRUST":
                self.publish_right(speed)

            elif cmd == "THRUST":
                left = float(parts[1])
                right = float(parts[2])
                self.publish_thrusters(left, right)

            elif cmd == "PUMP":
                value = int(parts[1])
                self.publish_pump(value)

            elif cmd == "UP":
                self.publish_pump(2)

            elif cmd == "DOWN":
                self.publish_pump(1)

            elif cmd == "PUMP_STOP":
                self.publish_pump(0)

            elif cmd == "DEPTH":
                target = float(parts[1])
                self.publish_target_depth(target)

            elif cmd == "LIGHT":
                value = parts[1].upper()
                self.light_on = value in ["1", "ON", "TRUE"]
                self.publish_light(self.light_on)

            elif cmd == "LIGHT_TOGGLE":
                self.light_on = not self.light_on
                self.publish_light(self.light_on)

            elif cmd == "STOP":
                self.publish_thrusters(0.0, 0.0)

            else:
                self.get_logger().warn(f"Unknown command: {command}")

        except (IndexError, ValueError):
            self.get_logger().warn(f"Bad command: {command}")

    def publish_left(self, value: float):
        msg = Float64()
        msg.data = self.clamp(value)
        self.left_pub.publish(msg)

    def publish_right(self, value: float):
        msg = Float64()
        msg.data = self.clamp(value)
        self.right_pub.publish(msg)

    def publish_thrusters(self, left: float, right: float):
        self.publish_left(left)
        self.publish_right(right)

    def publish_pump(self, value: int):
        msg = Int32()
        msg.data = value
        self.pump_pub.publish(msg)

    def publish_light(self, value: bool):
        msg = Bool()
        msg.data = value
        self.light_pub.publish(msg)

    def publish_target_depth(self, value: float):
        msg = Float64()
        msg.data = value
        self.target_depth_pub.publish(msg)

    def clamp(self, value: float) -> float:
        return value
        # no clamping now
        return max(-1.0, min(1.0, value))


def main(args=None):
    rclpy.init(args=args)

    node = RovController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()