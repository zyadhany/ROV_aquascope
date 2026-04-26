#!/usr/bin/env python3

from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64, Int32


class DepthHoldNode(Node):
    def __init__(self) -> None:
        super().__init__("depth_hold_node")

        self.declare_parameter("deadband", 0.01)
        self.declare_parameter("max_depth", 2.0)
        self.declare_parameter("sensor_timeout_sec", 0.2)
        self.declare_parameter("control_rate_hz", 10.0)

        self.declare_parameter("fill_cmd", 1)
        self.declare_parameter("empty_cmd", 2)
        self.declare_parameter("stop_cmd", 0)

        # Pulse-based ballast control
        self.declare_parameter("pulse_time_sec", 0.5)
        self.declare_parameter("min_observe_time_sec", 0.8)
        self.declare_parameter("stall_time_sec", 0.8)
        self.declare_parameter("movement_threshold_m", 0.005)

        self.deadband = float(self.get_parameter("deadband").value)
        self.max_depth = float(self.get_parameter("max_depth").value)
        self.sensor_timeout_sec = float(self.get_parameter("sensor_timeout_sec").value)
        control_rate_hz = float(self.get_parameter("control_rate_hz").value)

        self.fill_cmd = int(self.get_parameter("fill_cmd").value)
        self.empty_cmd = int(self.get_parameter("empty_cmd").value)
        self.stop_cmd = int(self.get_parameter("stop_cmd").value)

        self.pulse_time_sec = float(self.get_parameter("pulse_time_sec").value)
        self.min_observe_time_sec = float(self.get_parameter("min_observe_time_sec").value)
        self.stall_time_sec = float(self.get_parameter("stall_time_sec").value)
        self.movement_threshold_m = float(self.get_parameter("movement_threshold_m").value)

        self.current_depth: Optional[float] = None
        self.target_depth: Optional[float] = None
        self.last_depth_time = None
        self.last_cmd: Optional[int] = None

        self.prev_depth: Optional[float] = None

        # State machine
        self.state = "IDLE"   # IDLE, PULSE, OBSERVE
        self.state_start_time = 0.0
        self.state_end_time = 0.0
        self.active_cmd = self.stop_cmd

        # Observation tracking
        self.observe_start_depth: Optional[float] = None
        self.last_improvement_time = 0.0
        self.desired_direction = 0   # +1 deeper, -1 shallower

        self.create_subscription(Float64, "/rov/depth/current", self.depth_callback, 10)
        self.create_subscription(Float64, "/rov/depth/target", self.target_callback, 10)

        self.cmd_pub = self.create_publisher(Int32, "/rov/mcu/cmd/pump", 10)
        self.error_pub = self.create_publisher(Float64, "/rov/depth/error", 10)

        self.timer = self.create_timer(1.0 / control_rate_hz, self.control_loop)

        self.get_logger().info("depth_hold_node started")
        self.get_logger().info(
            f"Pulse controller | pulse={self.pulse_time_sec:.2f}s "
            f"observe_min={self.min_observe_time_sec:.2f}s "
            f"stall={self.stall_time_sec:.2f}s"
        )

    def now_sec(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def depth_callback(self, msg: Float64) -> None:
        self.prev_depth = self.current_depth
        self.current_depth = msg.data
        self.last_depth_time = self.get_clock().now()

    def target_callback(self, msg: Float64) -> None:
        target = msg.data
        if target < 0.0:
            target = 0.0
        if target > self.max_depth:
            target = self.max_depth

        self.target_depth = target
        self.get_logger().info(f"Target depth: {self.target_depth:.2f} m")

    def publish_cmd(self, value: int) -> None:
        if self.last_cmd == value:
            return

        msg = Int32()
        msg.data = value
        self.cmd_pub.publish(msg)
        self.last_cmd = value

        if value == self.fill_cmd:
            self.get_logger().info("CMD = FILL")
        elif value == self.empty_cmd:
            self.get_logger().info("CMD = EMPTY")
        else:
            self.get_logger().info("CMD = STOP")

    def reset_idle(self) -> None:
        self.state = "IDLE"
        self.state_start_time = 0.0
        self.state_end_time = 0.0
        self.active_cmd = self.stop_cmd
        self.observe_start_depth = None
        self.last_improvement_time = 0.0
        self.desired_direction = 0
        self.publish_cmd(self.stop_cmd)

    def start_pulse(self, cmd: int, desired_direction: int) -> None:
        now = self.now_sec()
        self.state = "PULSE"
        self.state_start_time = now
        self.state_end_time = now + self.pulse_time_sec
        self.active_cmd = cmd
        self.desired_direction = desired_direction
        self.publish_cmd(cmd)

        if cmd == self.fill_cmd:
            self.get_logger().info(f"Start FILL pulse for {self.pulse_time_sec:.2f} s")
        else:
            self.get_logger().info(f"Start EMPTY pulse for {self.pulse_time_sec:.2f} s")

    def start_observe(self) -> None:
        now = self.now_sec()
        self.state = "OBSERVE"
        self.state_start_time = now
        self.state_end_time = 0.0
        self.active_cmd = self.stop_cmd
        self.observe_start_depth = self.current_depth
        self.last_improvement_time = now
        self.publish_cmd(self.stop_cmd)
        self.get_logger().info("Observe depth after pulse")

    def control_loop(self) -> None:
        if self.current_depth is None or self.target_depth is None:
            self.reset_idle()
            return

        if self.last_depth_time is None:
            self.reset_idle()
            return

        age_sec = (self.get_clock().now() - self.last_depth_time).nanoseconds / 1e9
        if age_sec > self.sensor_timeout_sec:
            self.get_logger().warn("Depth timeout -> STOP")
            self.reset_idle()
            return

        error = self.target_depth - self.current_depth

        err_msg = Float64()
        err_msg.data = error
        self.error_pub.publish(err_msg)

        # close enough
        if abs(error) <= self.deadband:
            self.reset_idle()
            return

        now = self.now_sec()

        # Keep pulse active until timer ends
        if self.state == "PULSE":
            if now >= self.state_end_time:
                self.start_observe()
            return

        # Observe motion after pulse
        if self.state == "OBSERVE":
            if self.observe_start_depth is None:
                self.reset_idle()
                return

            depth_change = self.current_depth - self.observe_start_depth

            moving_correctly = False
            if self.desired_direction > 0:
                # Wanted deeper, so depth should increase
                moving_correctly = depth_change >= self.movement_threshold_m
            elif self.desired_direction < 0:
                # Wanted shallower, so depth should decrease
                moving_correctly = depth_change <= -self.movement_threshold_m

            if moving_correctly:
                self.last_improvement_time = now

            # Always wait at least a small observe time
            observe_age = now - self.state_start_time
            if observe_age < self.min_observe_time_sec:
                return

            # If still moving the right way, keep waiting
            if (now - self.last_improvement_time) < self.stall_time_sec:
                return

            # Motion has stalled and we're still outside deadband -> pulse again
            self.state = "IDLE"

        # IDLE -> decide next action
        if error > 0.0:
            # Too shallow -> go deeper -> fill
            self.start_pulse(self.fill_cmd, desired_direction=1)
        else:
            # Too deep -> go upward -> empty
            self.start_pulse(self.empty_cmd, desired_direction=-1)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DepthHoldNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        stop_msg = Int32()
        stop_msg.data = 0
        node.cmd_pub.publish(stop_msg)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()