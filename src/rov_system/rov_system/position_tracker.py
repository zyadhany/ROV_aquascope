#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Point
from rclpy.qos import QoSProfile, DurabilityPolicy, HistoryPolicy, qos_profile_sensor_data

class PositionTracker(Node):
    def __init__(self):
        super().__init__('position_tracker')

        # 1. Setup QoS for Publisher (Latched / Global Variable style)
        # This guarantees any new node joining later instantly gets the last X/Y position
        global_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        # 2. Publisher for X/Y position
        # We use standard geometry_msgs/Point for X, Y, Z coordinates
        self.pos_pub = self.create_publisher(Point, '/rov/position/current', global_qos)

        # 3. Subscriber for IMU (Sensor Data QoS is highly recommended for Gazebo sensors)
        self.imu_sub = self.create_subscription(
            Imu,
            '/rov/imu',
            self.imu_callback,
            qos_profile_sensor_data
        )

        # Physics State Variables for Dead Reckoning (Double Integration)
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.vel_x = 0.0
        self.vel_y = 0.0
        
        self.last_time = None
        
        self.get_logger().info("Position Tracker initialized. Broadcasting on /rov/position/current")

    def imu_callback(self, msg: Imu):
        current_time = self.get_clock().now()
        
        # Skip the first frame to establish a time baseline
        if self.last_time is None:
            self.last_time = current_time
            return
            
        # Calculate Delta Time (dt) in seconds
        dt = (current_time - self.last_time).nanoseconds / 1e9
        self.last_time = current_time

        if dt <= 0:
            return

        # Extract linear acceleration (m/s^2)
        accel_x = msg.linear_acceleration.x
        accel_y = msg.linear_acceleration.y

        # Step 1: Integrate Acceleration to get Velocity (v = u + a*t)
        self.vel_x += accel_x * dt
        self.vel_y += accel_y * dt

        # Step 2: Integrate Velocity to get Position (p = p_initial + v*t)
        self.pos_x += self.vel_x * dt
        self.pos_y += self.vel_y * dt

        # Prepare and publish the global variable message
        pos_msg = Point()
        pos_msg.x = self.pos_x
        pos_msg.y = self.pos_y
        pos_msg.z = 0.0  # Assuming purely 2D planar tracking for now

        self.pos_pub.publish(pos_msg)

def main(args=None):
    rclpy.init(args=args)
    node = PositionTracker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()