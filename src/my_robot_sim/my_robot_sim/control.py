#!/usr/bin/env python3

from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64, String


class ThrusterController(Node):
    def __init__(self):
        super().__init__("thruster_controller")

        self.left_pub = self.create_publisher(
            Float64,
            "/model/rov/joint/left_thruster_joint/cmd_thrust",
            10,
        )
        self.right_pub = self.create_publisher(
            Float64,
            "/model/rov/joint/right_thruster_joint/cmd_thrust",
            10,
        )

        self.depth_target_pub = self.create_publisher(
            Float64,
            "/rov/depth/target",
            10,
        )

        self.cmd_sub = self.create_subscription(
            String,
            "/rov/move_cmd",
            self.cmd_callback,
            10,
        )

        self.depth_sub = self.create_subscription(
            Float64,
            "/rov/depth/current",
            self.depth_callback,
            10,
        )

        self.default_thrust = 10.0
        self.current_left = 0.0
        self.current_right = 0.0

        self.depth_step = 0.10
        self.min_depth = 0.0
        self.max_depth = 2.0

        self.current_depth: Optional[float] = None
        self.target_depth: Optional[float] = None
        self.target_initialized = False

        self.get_logger().info("ThrusterController started")

    def depth_callback(self, msg: Float64) -> None:
        self.current_depth = float(msg.data)

        if not self.target_initialized:
            self.target_depth = self.current_depth
            self.target_initialized = True
            self.publish_depth_target()
            self.get_logger().info(
                f"Initialized target depth from current depth: {self.target_depth:.2f} m"
            )

    def publish_thrusters(self, left: float, right: float) -> None:
        left_msg = Float64()
        right_msg = Float64()
        left_msg.data = float(left)
        right_msg.data = float(right)

        self.left_pub.publish(left_msg)
        self.right_pub.publish(right_msg)

        self.current_left = float(left)
        self.current_right = float(right)

        self.get_logger().info(
            f"Published thrust | left={left:.2f} N, right={right:.2f} N"
        )

    def publish_depth_target(self) -> None:
        if self.target_depth is None:
            return

        msg = Float64()
        msg.data = float(self.target_depth)
        self.depth_target_pub.publish(msg)
        self.get_logger().info(
            f"Published depth target = {self.target_depth:.2f} m"
        )

    def cmd_callback(self, msg: String) -> None:
        cmd = msg.data.strip().lower()

        if cmd == "forward":
            self.publish_thrusters(self.default_thrust, self.default_thrust)

        elif cmd == "backward":
            self.publish_thrusters(-self.default_thrust, -self.default_thrust)

        elif cmd == "left":
            self.publish_thrusters(-self.default_thrust, self.default_thrust)

        elif cmd == "right":
            self.publish_thrusters(self.default_thrust, -self.default_thrust)

        elif cmd == "stop":
            self.publish_thrusters(0.0, 0.0)

        elif cmd == "hold":
            self.publish_thrusters(0.0, 0.0)
            if self.current_depth is not None:
                self.target_depth = self.current_depth
                self.publish_depth_target()
                self.get_logger().info(
                    f"HOLD at current depth = {self.target_depth:.2f} m"
                )

        elif cmd == "down":
            if self.target_depth is None:
                self.get_logger().warn("Target depth not initialized yet")
                return

            self.target_depth += self.depth_step
            if self.target_depth > self.max_depth:
                self.target_depth = self.max_depth
            self.publish_depth_target()

        elif cmd == "up":
            if self.target_depth is None:
                self.get_logger().warn("Target depth not initialized yet")
                return

            self.target_depth -= self.depth_step
            if self.target_depth < self.min_depth:
                self.target_depth = self.min_depth
            self.publish_depth_target()

        else:
            self.get_logger().warn(f"Unknown command: {cmd}")


def main(args=None):
    rclpy.init(args=args)
    node = ThrusterController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_thrusters(0.0, 0.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()