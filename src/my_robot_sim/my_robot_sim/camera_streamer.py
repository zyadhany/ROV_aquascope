#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CompressedImage


class CameraStreamer(Node):
    def __init__(self):
        super().__init__("camera_streamer")

        # Subscribe to raw camera image
        self.raw_camera_sub = self.create_subscription(
            Image,
            "/sim/camera/image",
            self.raw_image_callback,
            qos_profile_sensor_data,
        )

        # Publish raw camera image
        self.raw_camera_pub = self.create_publisher(
            Image,
            "/rov/camera/image",
            1
        )

        # Subscribe to compressed camera image
        self.compressed_camera_sub = self.create_subscription(
            CompressedImage,
            "/sim/camera/image/compressed",
            self.compressed_image_callback,
            qos_profile_sensor_data,
        )

        # Publish compressed camera image
        self.compressed_camera_pub = self.create_publisher(
            CompressedImage,
            "/rov/camera/image/compressed",
            1
        )

        self.get_logger().info("Camera Streamer started")

        self.get_logger().info("Raw input:        /sim/camera/image")
        self.get_logger().info("Raw output:       /rov/camera/image")

        self.get_logger().info("Compressed input: /sim/camera/image/compressed")
        self.get_logger().info("Compressed output:/rov/camera/image/compressed")

    def raw_image_callback(self, msg: Image):
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "rov_camera"

        self.raw_camera_pub.publish(msg)

        self.get_logger().info(
            "Raw camera frame republished",
            throttle_duration_sec=2.0,
        )

    def compressed_image_callback(self, msg: CompressedImage):
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "rov_camera"

        self.compressed_camera_pub.publish(msg)

        self.get_logger().info(
            "Compressed camera frame republished",
            throttle_duration_sec=2.0,
        )


def main(args=None):
    rclpy.init(args=args)

    node = CameraStreamer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Camera Streamer stopped")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()