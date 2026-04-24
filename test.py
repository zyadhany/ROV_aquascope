#!/usr/bin/env python3

import sys
import termios
import tty
import select

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64, Bool, String


class MyController(Node):
    def __init__(self):
        super().__init__('my_controller')

        # =========================
        # Publishers
        # Edit these topics later
        # =========================
        self.rotate_pub = self.create_publisher(Float64, '/rotate_velocity', 10)
        self.move_pub = self.create_publisher(Float64, '/move_velocity', 10)
        self.light_pub = self.create_publisher(Bool, '/light_toggle', 10)
        self.mode_pub = self.create_publisher(String, '/controller_mode', 10)

        # =========================
        # Internal state
        # Edit these later
        # =========================
        self.rotate_velocity = 0.0
        self.move_velocity = 0.0
        self.light_on = False
        self.mode = 'idle'

        self.velocity_step = 0.5
        self.max_velocity = 10.0

        # Timer for continuous publishing
        self.timer = self.create_timer(0.1, self.publish_commands)

        self.get_logger().info('My controller started')
        print(self.help_text())

    def help_text(self):
        return (
            "\nController keys:\n"
            "  w : move forward\n"
            "  s : move backward\n"
            "  a : rotate left\n"
            "  d : rotate right\n"
            "  x : stop all motion\n"
            "  l : toggle light\n"
            "  m : change mode\n"
            "  q : quit\n\n"
            "Edit handle_key() to change behavior.\n"
        )

    def publish_commands(self):
        rotate_msg = Float64()
        rotate_msg.data = self.rotate_velocity
        self.rotate_pub.publish(rotate_msg)

        move_msg = Float64()
        move_msg.data = self.move_velocity
        self.move_pub.publish(move_msg)

        light_msg = Bool()
        light_msg.data = self.light_on
        self.light_pub.publish(light_msg)

        mode_msg = String()
        mode_msg.data = self.mode
        self.mode_pub.publish(mode_msg)

    def get_key(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setraw(fd)
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
            if readable:
                key = sys.stdin.read(1)
            else:
                key = ''
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        return key

    def clamp(self, value, min_value, max_value):
        return max(min(value, max_value), min_value)

    def stop_motion(self):
        self.rotate_velocity = 0.0
        self.move_velocity = 0.0
        print('Stopped all motion')

    def toggle_light(self):
        self.light_on = not self.light_on
        print(f'Light: {"ON" if self.light_on else "OFF"}')

    def change_mode(self):
        # Edit this logic later
        if self.mode == 'idle':
            self.mode = 'manual'
        elif self.mode == 'manual':
            self.mode = 'auto'
        else:
            self.mode = 'idle'

        print(f'Mode changed to: {self.mode}')

    def handle_key(self, key):
        # ============================================
        # THIS IS THE MAIN PLACE YOU EDIT LATER
        # Add any command behavior you want here
        # ============================================

        if key == 'w':
            self.move_velocity = self.clamp(
                self.move_velocity + self.velocity_step,
                -self.max_velocity,
                self.max_velocity
            )
            print(f'Move velocity: {self.move_velocity:.2f}')

        elif key == 's':
            self.move_velocity = self.clamp(
                self.move_velocity - self.velocity_step,
                -self.max_velocity,
                self.max_velocity
            )
            print(f'Move velocity: {self.move_velocity:.2f}')

        elif key == 'a':
            self.rotate_velocity = self.clamp(
                self.rotate_velocity + self.velocity_step,
                -self.max_velocity,
                self.max_velocity
            )
            print(f'Rotate velocity: {self.rotate_velocity:.2f}')

        elif key == 'd':
            self.rotate_velocity = self.clamp(
                self.rotate_velocity - self.velocity_step,
                -self.max_velocity,
                self.max_velocity
            )
            print(f'Rotate velocity: {self.rotate_velocity:.2f}')

        elif key == 'x':
            self.stop_motion()

        elif key == 'l':
            self.toggle_light()

        elif key == 'm':
            self.change_mode()

        elif key == 'q':
            print('Quit')
            return False
        else:
            print(f'Unknown key: {key}')
            return True
        
        self.publish_commands()
        return True

    def run(self):
        running = True
        while rclpy.ok() and running:
            key = self.get_key()

            if key:
                running = self.handle_key(key)


def main(args=None):
    rclpy.init(args=args)
    node = MyController()

    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()