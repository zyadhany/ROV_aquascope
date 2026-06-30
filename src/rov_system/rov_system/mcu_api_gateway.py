#!/usr/bin/env python3

import json
import math
import requests
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import String, Float64, Bool

class McuGateway(Node):
    def __init__(self):
        super().__init__("mcu_gateway")
        
        self.esp_url = "http://10.42.0.42"
        self.max_pwm = 255
        self.req_timeout = 0.2

        self.depth_pub = self.create_publisher(Float64, "/rov/depth/current", 10)
        self.pressure_pub = self.create_publisher(Float64, "/rov/pressure/data", 10)
        self.imu_pub = self.create_publisher(Imu, "/rov/imu", 10)
        self.sonar_pub = self.create_publisher(String, "/rov/scanning_sonar/reading", 10)
        self.front_distance_pub = self.create_publisher(Float64, "/rov/front_distance", 10)
        self.temp_pub = self.create_publisher(Float64, "/rov/temperature", 10)

        self.left_thruster_sub = self.create_subscription(Float64, "/rov/mcu/cmd/left_thruster", self.left_thruster_callback, 10)
        self.right_thruster_sub = self.create_subscription(Float64, "/rov/mcu/cmd/right_thruster", self.right_thruster_callback, 10)
        self.pump_sub = self.create_subscription(Float64, "/rov/mcu/cmd/pump", self.pump_callback, 10)
        self.light_sub = self.create_subscription(Bool, "/rov/mcu/cmd/light", self.light_callback, 10)
        self.gripper_sub = self.create_subscription(Bool, "/rov/mcu/cmd/gripper", self.gripper_callback, 10)

        self.sensor_timer = self.create_timer(2, self.poll_sensors)
        self.get_logger().info("HTTP MCU Gateway started")

    def send_http_command(self, endpoint: str, params: dict = None):
        try:
            requests.get(f"{self.esp_url}{endpoint}", params=params, timeout=self.req_timeout)
        except requests.exceptions.RequestException:
            pass

    def clamp_normalized(self, value: float):
        if not math.isfinite(value):
            return None
        return max(-1.0, min(1.0, value))

    def left_thruster_callback(self, msg: Float64):
        value = self.clamp_normalized(msg.data)
        if value is not None:
            self.send_http_command("/motor/left", {"speed": float(value)})

    def right_thruster_callback(self, msg: Float64):
        value = self.clamp_normalized(msg.data)
        if value is not None:
            self.send_http_command("/motor/right", {"speed": float(value)})

    def pump_callback(self, msg: Float64):
        value = self.clamp_normalized(msg.data)
        if value is not None:
            self.send_http_command("/pump", {"speed": float(value)})

    def light_callback(self, msg: Bool):
        self.send_http_command("/light_on" if msg.data else "/light_off")

    def gripper_callback(self, msg: Bool):
        self.send_http_command("/gripper/open" if msg.data else "/gripper/close")

    def poll_sensors(self):
        try:
            response = requests.get(f"{self.esp_url}/sensors", timeout=self.req_timeout)
            if response.status_code == 200:
                data = response.json()
                
                if "depth" in data:
                    msg = Float64()
                    msg.data = float(data["depth"])
                    self.depth_pub.publish(msg)
                
                if "front_distance" in data:
                    msg = Float64()
                    msg.data = float(data["front_distance"])
                    self.front_distance_pub.publish(msg)

                if "pressure" in data:
                    try:
                        msg = Float64()
                        msg.data = float(data["pressure"])
                        self.pressure_pub.publish(msg)
                    except ValueError:
                        pass

                if "temp" in data:
                    try:
                        msg = Float64()
                        msg.data = float(data["temp"])
                        self.temp_pub.publish(msg)
                    except ValueError:
                        pass
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            pass

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