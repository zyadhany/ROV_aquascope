#!/usr/bin/env python3

from collections import deque

import rclpy
from rclpy.node import Node

from std_msgs.msg import String, Float64, Int32


class MicrocontrollerSim(Node):
    def __init__(self):
        super().__init__("microcontroller_sim")

        # Fake serial input/output
        self.serial_sub = self.create_subscription(
            String,
            "/mcu/serial/in",
            self.serial_callback,
            10,
        )

        self.serial_pub = self.create_publisher(
            String,
            "/mcu/serial/out",
            10,
        )

        # Actuator publishers
        self.left_thruster_pub = self.create_publisher(
            Float64,
            "/sim/left_thruster/cmd",
            10,
        )

        self.right_thruster_pub = self.create_publisher(
            Float64,
            "/sim/right_thruster/cmd",
            10,
        )

        self.pump_pub = self.create_publisher(
            Int32,
            "/sim/ballast_cmd",
            10,
        )

        # Sensor subscribers
        self.depth_sub = self.create_subscription(
            Float64,
            "/sim/depth/current",
            self.depth_callback,
            10,
        )

        # Internal state, like ESP variables
        self.latest_depth = 0.0

        self.left_thruster_value = 0.0
        self.right_thruster_value = 0.0
        self.pump_value = 0

        # Queue instead of one variable.
        # This prevents fast commands from overwriting each other.
        self.serial_command_queue = deque()

        # Main loop timer, like Arduino loop()
        self.loop_timer = self.create_timer(0.05, self.loop)  # 20 Hz

        # Sensor report timer
        self.sensor_timer = self.create_timer(0.2, self.send_sensor_data)  # 5 Hz

        self.get_logger().info("Microcontroller simulator started")
        self.get_logger().info(
            "Commands: FORWARD, BACKWARD, LEFT, RIGHT, STOP, "
            "LEFT_THRUST, RIGHT_THRUST, PUMP, UP, DOWN, HOLD, PING"
        )

    # ========== Fake serial receive ==========

    def serial_callback(self, msg: String):
        command = msg.data.strip()

        if not command:
            return

        self.serial_command_queue.append(command)

    # ========== Sensor callbacks ==========

    def depth_callback(self, msg: Float64):
        self.latest_depth = msg.data

    # ========== ESP-like main loop ==========

    def loop(self):
        while self.serial_command_queue:
            command = self.serial_command_queue.popleft()
            self.handle_serial_command(command)

    # ========== Command parser ==========

    def handle_serial_command(self, command: str):
        parts = command.split()

        if not parts:
            return

        cmd = parts[0].upper()

        try:
            # =========================
            # Direct actuator commands
            # =========================

            if cmd == "LEFT_THRUST":
                # Example:
                # LEFT_THRUST 1.0
                value = float(parts[1])

                self.left_thruster_value = value
                self.publish_left_thruster()

                self.send_serial(f"OK LEFT_THRUST {value}")

            elif cmd == "RIGHT_THRUST":
                # Example:
                # RIGHT_THRUST 1.0
                value = float(parts[1])

                self.right_thruster_value = value
                self.publish_right_thruster()

                self.send_serial(f"OK RIGHT_THRUST {value}")

            elif cmd == "PUMP":
                # Example:
                # PUMP 0  -> stop / hold
                # PUMP 1  -> fill
                # PUMP 2  -> empty
                value = int(parts[1])

                self.pump_value = value
                self.publish_pump()

                self.send_serial(f"OK PUMP {value}")

            # =========================
            # Movement commands
            # =========================

            elif cmd == "FORWARD":
                # Example:
                # FORWARD
                # FORWARD 1.0
                value = self.get_optional_float(parts, default=1.0)

                self.left_thruster_value = value
                self.right_thruster_value = value

                self.publish_left_thruster()
                self.publish_right_thruster()

                self.send_serial(f"OK FORWARD {value}")

            elif cmd == "BACKWARD":
                # Example:
                # BACKWARD
                # BACKWARD 1.0
                value = self.get_optional_float(parts, default=1.0)

                self.left_thruster_value = -value
                self.right_thruster_value = -value

                self.publish_left_thruster()
                self.publish_right_thruster()

                self.send_serial(f"OK BACKWARD {value}")

            elif cmd == "LEFT":
                # Turn left.
                # Left thruster backward, right thruster forward.
                value = self.get_optional_float(parts, default=1.0)

                self.left_thruster_value = -value
                self.right_thruster_value = value

                self.publish_left_thruster()
                self.publish_right_thruster()

                self.send_serial(f"OK LEFT {value}")

            elif cmd == "RIGHT":
                # Turn right.
                # Left thruster forward, right thruster backward.
                value = self.get_optional_float(parts, default=1.0)

                self.left_thruster_value = value
                self.right_thruster_value = -value

                self.publish_left_thruster()
                self.publish_right_thruster()

                self.send_serial(f"OK RIGHT {value}")

            elif cmd == "STOP":
                self.stop_all()
                self.send_serial("OK STOP")

            # =========================
            # Ballast / vertical commands
            # =========================

            elif cmd == "UP":
                # Empty ballast tank.
                # In your system: 2 = empty.
                self.pump_value = 2
                self.publish_pump()

                self.send_serial("OK UP")

            elif cmd == "DOWN":
                # Fill ballast tank.
                # In your system: 1 = fill.
                self.pump_value = 1
                self.publish_pump()

                self.send_serial("OK DOWN")

            elif cmd == "HOLD":
                # Stop pump, keep current movement motors as they are.
                self.pump_value = 0
                self.publish_pump()

                self.send_serial("OK HOLD")

            # =========================
            # Utility
            # =========================

            elif cmd == "PING":
                self.send_serial("PONG")

            else:
                self.send_serial(f"ERROR UNKNOWN_COMMAND {command}")

        except (IndexError, ValueError):
            self.send_serial(f"ERROR BAD_COMMAND {command}")

    # ========== Helpers ==========

    def get_optional_float(self, parts, default: float) -> float:
        if len(parts) < 2:
            return default

        return float(parts[1])

    def stop_all(self):
        self.left_thruster_value = 0.0
        self.right_thruster_value = 0.0
        self.pump_value = 0

        self.publish_left_thruster()
        self.publish_right_thruster()
        self.publish_pump()

    # ========== Actuator output ==========

    def publish_left_thruster(self):
        msg = Float64()
        msg.data = self.left_thruster_value
        self.left_thruster_pub.publish(msg)

    def publish_right_thruster(self):
        msg = Float64()
        msg.data = self.right_thruster_value
        self.right_thruster_pub.publish(msg)

    def publish_pump(self):
        msg = Int32()
        msg.data = self.pump_value
        self.pump_pub.publish(msg)

    # ========== Sensor output back to fake serial ==========

    def send_sensor_data(self):
        self.send_serial(f"DEPTH {self.latest_depth:.3f}")

    # ========== Fake serial write ==========

    def send_serial(self, text: str):
        msg = String()
        msg.data = text
        self.serial_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    node = MicrocontrollerSim()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()