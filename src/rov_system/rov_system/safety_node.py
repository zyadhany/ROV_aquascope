#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import Float64, Int32, Bool

class SafetyNode(Node):
    def __init__(self):
        super().__init__('safety_node')

        qos_profile = QoSProfile(
            depth=10,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        self.front_distance = float('inf')
        self.battery = 100
        self.water_leak = False

        self.front_distance_sub = self.create_subscription(
            Float64,
            '/rov/front_distance',
            self.front_distance_callback,
            10
        )

        self.battery_sub = self.create_subscription(
            Int32,
            '/rov/battery',
            self.battery_callback,
            qos_profile
        )

        self.water_leak_sub = self.create_subscription(
            Bool,
            '/rov/water_leak',
            self.water_leak_callback,
            qos_profile
        )

        self.alert_pub = self.create_publisher(
            Bool,
            '/rov/alert',
            10
        )

        self.timer = self.create_timer(0.5, self.check_safety)
        self.get_logger().info("Safety Node started")

    def front_distance_callback(self, msg: Float64):
        self.front_distance = msg.data

    def battery_callback(self, msg: Int32):
        self.battery = msg.data

    def water_leak_callback(self, msg: Bool):
        self.water_leak = msg.data

    def check_safety(self):
        alert = False

        if self.front_distance < 0.05:
            self.get_logger().warn(f"Alert: Front distance too close ({self.front_distance}m)")
            alert = True
        
        if self.battery < 20:
            self.get_logger().warn(f"Alert: Battery low ({self.battery}%)")
            alert = True
            
        if self.water_leak:
            self.get_logger().warn("Alert: Water leak detected!")
            alert = True

        msg = Bool()
        msg.data = alert
        self.alert_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = SafetyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
