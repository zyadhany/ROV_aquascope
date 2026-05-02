#!/usr/bin/env python3

import pygame

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


# =========================
# JOYSTICK SETTINGS
# =========================

# Left analog axes
LEFT_STICK_X_AXIS = 0
LEFT_STICK_Y_AXIS = 1

# Buttons
BTN_UP = 0
BTN_DOWN = 2
BTN_LIGHT_TOGGLE = 1

# R2 can be button or axis depending on controller
BTN_R2 = 7
R2_AXIS = 5
R2_AXIS_THRESHOLD = 0.5

# Speeds
NORMAL_SPEED = 3.0
FAST_SPEED = 5.0

# Ignore small analog noise
DEADZONE = 0.25

# Publish rate
PUBLISH_HZ = 5.0


class JoystickController(Node):
    def __init__(self):
        super().__init__("joystick_controller")

        self.cmd_pub = self.create_publisher(
            String,
            "/rov/controller/cmd",
            10,
        )

        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            self.get_logger().error("No joystick connected")
            raise RuntimeError("No joystick connected")

        self.joy = pygame.joystick.Joystick(0)
        self.joy.init()

        self.x_axis = 0.0
        self.y_axis = 0.0

        self.up_pressed = False
        self.down_pressed = False
        self.r2_fast = False

        self.last_command = None

        self.timer = self.create_timer(1.0 / PUBLISH_HZ, self.timer_callback)

        self.get_logger().info("Joystick Controller started")
        self.get_logger().info(f"Joystick: {self.joy.get_name()}")
        self.get_logger().info(f"Buttons: {self.joy.get_numbuttons()}")
        self.get_logger().info(f"Axes: {self.joy.get_numaxes()}")
        self.get_logger().info("Left analog = movement")
        self.get_logger().info("Button 1 = UP")
        self.get_logger().info("Button 3 = DOWN")
        self.get_logger().info("Button 2 = LIGHT_TOGGLE")
        self.get_logger().info("R2 = fast speed")

    def send_command(self, command: str):
        msg = String()
        msg.data = command
        self.cmd_pub.publish(msg)
        self.get_logger().info(f"Sent command: {command}")

    def get_speed(self):
        if self.r2_fast:
            return FAST_SPEED
        return NORMAL_SPEED

    def handle_joystick_events(self):
        for event in pygame.event.get():

            if event.type == pygame.JOYAXISMOTION:
                axis = event.axis
                value = event.value

                if axis == LEFT_STICK_X_AXIS:
                    self.x_axis = value

                elif axis == LEFT_STICK_Y_AXIS:
                    self.y_axis = value

                elif axis == R2_AXIS:
                    self.r2_fast = value > R2_AXIS_THRESHOLD

            elif event.type == pygame.JOYBUTTONDOWN:
                button = event.button
                print(f"Button pressed: {button}")

                if button == BTN_UP:
                    self.up_pressed = True

                elif button == BTN_DOWN:
                    self.down_pressed = True

                elif button == BTN_LIGHT_TOGGLE:
                    self.send_command("LIGHT_TOGGLE")

                elif button == BTN_R2:
                    self.r2_fast = True

            elif event.type == pygame.JOYBUTTONUP:
                button = event.button
                print(f"Button released: {button}")

                if button == BTN_UP:
                    self.up_pressed = False

                elif button == BTN_DOWN:
                    self.down_pressed = False

                elif button == BTN_R2:
                    self.r2_fast = False

    def get_current_command(self):
        speed = self.get_speed()

        # Button movement has priority over analog movement
        if self.up_pressed:
            return "UP"

        if self.down_pressed:
            return "DOWN"

        # Left analog movement
        x = self.x_axis
        y = self.y_axis

        # If stick is in center
        if abs(x) < DEADZONE and abs(y) < DEADZONE:
            return "STOP"

        # Choose strongest direction
        if abs(y) > abs(x):
            if y < -DEADZONE:
                return f"FORWARD {speed}"
            elif y > DEADZONE:
                return f"BACKWARD {speed}"

        else:
            if x < -DEADZONE:
                return f"LEFT {speed}"
            elif x > DEADZONE:
                return f"RIGHT {speed}"

        return "STOP"

    def timer_callback(self):
        self.handle_joystick_events()

        command = self.get_current_command()

        # Keep sending movement while stick/button is active.
        # Send STOP once when released/centered.
        if command != self.last_command or command != "STOP":
            self.send_command(command)
            self.last_command = command


def main(args=None):
    rclpy.init(args=args)

    node = None

    try:
        node = JoystickController()
        rclpy.spin(node)

    except KeyboardInterrupt:
        if node is not None:
            node.send_command("STOP")

    finally:
        if node is not None:
            node.send_command("STOP")
            node.destroy_node()

        pygame.quit()
        rclpy.shutdown()


if __name__ == "__main__":
    main()