#!/usr/bin/env python3

import json
import math

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Imu
from std_msgs.msg import String, Float64, Bool


class McuGateway(Node):
    def __init__(self):
        super().__init__("mcu_gateway")

        # Publish serial commands to MCU
        self.serial_in_pub = self.create_publisher(
            String,
            "/mcu/serial/in",
            10,
        )

        # Publish parsed sensor data
        self.depth_pub = self.create_publisher(
            Float64,
            "/rov/depth/current",
            10,
        )

        self.pressure_pub = self.create_publisher(
            Float64,
            "/rov/pressure/data",
            10,
        )

        self.temp_pub = self.create_publisher(
            Float64,
            "/rov/temperature",
            10,
        )

        self.imu_pub = self.create_publisher(
            Imu,
            "/rov/imu",
            10,
        )

        self.sonar_pub = self.create_publisher(
            String,
            "/rov/scanning_sonar/reading",
            10,
        )

        self.front_distance_pub = self.create_publisher(
            Float64,
            "/rov/front_distance",
            10,
        )

        # Subscribe to MCU serial output
        self.serial_out_sub = self.create_subscription(
            String,
            "/mcu/serial/out",
            self.serial_out_callback,
            10,
        )

        # Subscribe to command topics
        self.left_thruster_sub = self.create_subscription(
            Float64,
            "/rov/mcu/cmd/left_thruster",
            self.left_thruster_callback,
            10,
        )

        self.right_thruster_sub = self.create_subscription(
            Float64,
            "/rov/mcu/cmd/right_thruster",
            self.right_thruster_callback,
            10,
        )

        self.pump_sub = self.create_subscription(
            Float64,
            "/rov/mcu/cmd/pump",
            self.pump_callback,
            10,
        )

        self.light_sub = self.create_subscription(
            Bool,
            "/rov/mcu/cmd/light",
            self.light_callback,
            10,
        )

        self.gripper_sub = self.create_subscription(
            Bool,
            "/rov/mcu/cmd/gripper",
            self.gripper_callback,
            10,
        )

        self.get_logger().info("MCU Gateway started")

    # =========================
    # Commands -> serial input
    # =========================

    def left_thruster_callback(self, msg: Float64):
        value = self.clamp_normalized(msg.data, "left thruster")
        if value is not None:
            self.send_serial(f"LEFT_THRUST {value}")

    def right_thruster_callback(self, msg: Float64):
        value = self.clamp_normalized(msg.data, "right thruster")
        if value is not None:
            self.send_serial(f"RIGHT_THRUST {value}")

    def pump_callback(self, msg: Float64):
        value = self.clamp_normalized(msg.data, "pump")
        if value is not None:
            self.send_serial(f"PUMP {value}")

    def light_callback(self, msg: Bool):
        value = 1 if msg.data else 0
        self.send_serial(f"LIGHT {value}")

    def gripper_callback(self, msg: Bool):
        value = 1 if msg.data else 0
        self.send_serial(f"GRIPPER {value}")

    def send_serial(self, command: str):
        msg = String()
        msg.data = command
        self.serial_in_pub.publish(msg)

    def clamp_normalized(self, value: float, name: str):
        if not math.isfinite(value):
            self.get_logger().warn(f"Ignoring non-finite {name} command: {value}")
            return None

        return max(-1.0, min(1.0, value))

    # =========================
    # Serial output -> ROS data
    # =========================

    def serial_out_callback(self, msg: String):
        text = msg.data.strip()

        if not text:
            return

        parts = text.split()

        if len(parts) < 2:
            self.get_logger().info(text)
            return

        key = parts[0].upper()
        value_text = parts[1]

        try:
            if key == "DEPTH":
                self.publish_depth(float(value_text))

            elif key == "PRESSURE":
                self.publish_pressure(float(value_text))

            elif key == "TEMP" or key == "TEMPERATURE":
                self.publish_temp(float(value_text))

            elif key == "IMU":
                self.publish_imu(parts[1:])

            elif key == "SONAR":
                self.publish_sonar(" ".join(parts[1:]))

            elif key == "OK":
                self.get_logger().info(text)

            elif key == "ERROR":
                self.get_logger().warn(text)

            else:
                self.get_logger().info(text)

        except ValueError:
            self.get_logger().warn(f"Bad MCU message: {text}")

    def publish_depth(self, value: float):
        msg = Float64()
        msg.data = value
        self.depth_pub.publish(msg)

    def publish_pressure(self, value: float):
        msg = Float64()
        msg.data = value
        self.pressure_pub.publish(msg)

    def publish_temp(self, value: float):
        msg = Float64()
        msg.data = value
        self.temp_pub.publish(msg)

    def publish_sonar(self, reading: str):
        msg = String()
        msg.data = reading
        self.sonar_pub.publish(msg)

        try:
            data = json.loads(reading)
            angle = float(data.get("angle_rad", 0.0))
            distance = float(data["distance_m"])
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            return

        if abs(angle) <= 0.05:
            distance_msg = Float64()
            distance_msg.data = distance
            self.front_distance_pub.publish(distance_msg)

    def publish_imu(self, values):
        if len(values) != 10:
            raise ValueError

        (
            orientation_x,
            orientation_y,
            orientation_z,
            orientation_w,
            angular_velocity_x,
            angular_velocity_y,
            angular_velocity_z,
            linear_acceleration_x,
            linear_acceleration_y,
            linear_acceleration_z,
        ) = [float(value) for value in values]

        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "imu_link"
        msg.orientation.x = orientation_x
        msg.orientation.y = orientation_y
        msg.orientation.z = orientation_z
        msg.orientation.w = orientation_w
        msg.angular_velocity.x = angular_velocity_x
        msg.angular_velocity.y = angular_velocity_y
        msg.angular_velocity.z = angular_velocity_z
        msg.linear_acceleration.x = linear_acceleration_x
        msg.linear_acceleration.y = linear_acceleration_y
        msg.linear_acceleration.z = linear_acceleration_z

        self.imu_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    node = McuGateway()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
