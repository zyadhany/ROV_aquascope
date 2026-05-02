#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Imu
from std_msgs.msg import String, Float64, Int32, Bool


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

        self.imu_pub = self.create_publisher(
            Imu,
            "/rov/imu",
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
            Int32,
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

        self.get_logger().info("MCU Gateway started")

    # =========================
    # Commands -> serial input
    # =========================

    def left_thruster_callback(self, msg: Float64):
        self.send_serial(f"LEFT_THRUST {msg.data}")

    def right_thruster_callback(self, msg: Float64):
        self.send_serial(f"RIGHT_THRUST {msg.data}")

    def pump_callback(self, msg: Int32):
        self.send_serial(f"PUMP {msg.data}")

    def light_callback(self, msg: Bool):
        value = 1 if msg.data else 0
        self.send_serial(f"LIGHT {value}")

    def send_serial(self, command: str):
        msg = String()
        msg.data = command
        self.serial_in_pub.publish(msg)

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

            elif key == "IMU":
                self.publish_imu(parts[1:])

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
