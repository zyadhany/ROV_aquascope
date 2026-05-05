#!/usr/bin/env python3

from collections import deque
import threading
import sys
import termios
import tty
import select

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

try:
    from pynput import keyboard as pynput_keyboard
except ImportError:
    pynput_keyboard = None


NORMAL_SPEED = 0.6
FAST_SPEED = 1.0

MOVEMENT_KEYS = {
    "w": "FORWARD",
    "s": "BACKWARD",
    "a": "LEFT",
    "d": "RIGHT",
}

VERTICAL_KEYS = {
    "i": "UP",
    "o": "DOWN",
}

ACTION_KEYS = {
    "g": "STOP",
    "k": "PUMP_STOP",
    "l": "LIGHT_TOGGLE",
    "h": "GRIPPER_TOGGLE",
}


class KeyboardController(Node):
    def __init__(self):
        super().__init__("keyboard_controller")

        self.cmd_pub = self.create_publisher(
            String,
            "/rov/controller/cmd",
            10,
        )

        self.command_queue = deque()
        self.queue_lock = threading.Lock()

        self.pressed_keys = set()
        self.movement_order = []
        self.shift_pressed = False
        self.quit_requested = False
        self.listener = None

        self.queue_timer = self.create_timer(0.02, self.process_command_queue)

        self.get_logger().info("Keyboard Controller started")
        self.get_logger().info(
            "Controls: "
            "w=forward, s=backward, a=left, d=right, "
            "g=stop, i=up, k=pump stop, o=down, "
            "l=light toggle, h=gripper toggle, "
            "hold shift=fast, q=quit"
        )

    def send_command(self, command: str):
        msg = String()
        msg.data = command
        self.cmd_pub.publish(msg)
        self.get_logger().info(f"Sent command: {command}")

    def queue_command(self, command: str):
        with self.queue_lock:
            self.command_queue.append(command)

    def process_command_queue(self):
        while True:
            with self.queue_lock:
                if not self.command_queue:
                    break

                command = self.command_queue.popleft()

            self.send_command(command)

        if self.quit_requested:
            self.send_command("STOP")
            rclpy.shutdown()

    def start_global_listener(self) -> bool:
        if pynput_keyboard is None:
            self.get_logger().warn(
                "python3-pynput is not installed; falling back to terminal-only "
                "keyboard input."
            )
            return False

        try:
            self.listener = pynput_keyboard.Listener(
                on_press=self.on_global_key_press,
                on_release=self.on_global_key_release,
            )
            self.listener.start()

        except Exception as exc:
            self.get_logger().warn(
                f"Global keyboard listener failed: {exc}. "
                "Falling back to terminal-only keyboard input."
            )
            self.listener = None
            return False

        self.get_logger().info("Global keyboard listener active")
        return True

    def stop_global_listener(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None

    def on_global_key_press(self, key):
        key_name = self.normalize_global_key(key)

        if key_name is None:
            return

        with self.queue_lock:
            already_pressed = key_name in self.pressed_keys
            self.pressed_keys.add(key_name)

        if key_name == "shift":
            self.shift_pressed = True
            if self.movement_order:
                self.queue_current_movement()
            return

        if already_pressed:
            return

        if key_name in MOVEMENT_KEYS:
            if key_name in self.movement_order:
                self.movement_order.remove(key_name)

            self.movement_order.append(key_name)
            self.queue_current_movement()
            return

        if key_name in VERTICAL_KEYS:
            self.queue_command(VERTICAL_KEYS[key_name])
            return

        if key_name in ACTION_KEYS:
            self.queue_command(ACTION_KEYS[key_name])
            return

        if key_name == "q":
            self.quit_requested = True

    def on_global_key_release(self, key):
        key_name = self.normalize_global_key(key)

        if key_name is None:
            return

        with self.queue_lock:
            self.pressed_keys.discard(key_name)

        if key_name == "shift":
            self.shift_pressed = False
            if self.movement_order:
                self.queue_current_movement()
            return

        if key_name in MOVEMENT_KEYS:
            if key_name in self.movement_order:
                self.movement_order.remove(key_name)

            self.queue_current_movement()
            return

        if key_name in VERTICAL_KEYS:
            self.queue_command("PUMP_STOP")

    def normalize_global_key(self, key):
        if pynput_keyboard is None:
            return None

        if key in (
            pynput_keyboard.Key.shift,
            pynput_keyboard.Key.shift_l,
            pynput_keyboard.Key.shift_r,
        ):
            return "shift"

        try:
            if key.char is not None:
                return key.char.lower()

        except AttributeError:
            return None

        return None

    def queue_current_movement(self):
        if not self.movement_order:
            self.queue_command("STOP")
            return

        key_name = self.movement_order[-1]
        speed = FAST_SPEED if self.shift_pressed else NORMAL_SPEED
        self.queue_command(f"{MOVEMENT_KEYS[key_name]} {speed}")

    def command_for_terminal_key(self, key: str):
        fast = key.isupper()
        key = key.lower()

        if key in MOVEMENT_KEYS:
            speed = FAST_SPEED if fast else NORMAL_SPEED
            return f"{MOVEMENT_KEYS[key]} {speed}"

        if key in VERTICAL_KEYS:
            return VERTICAL_KEYS[key]

        if key in ACTION_KEYS:
            return ACTION_KEYS[key]

        return None


def get_key(timeout=0.1):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        ready, _, _ = select.select([sys.stdin], [], [], timeout)

        if ready:
            return sys.stdin.read(1)

        return None

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def main(args=None):
    rclpy.init(args=args)

    node = KeyboardController()

    try:
        if node.start_global_listener():
            rclpy.spin(node)

        else:
            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=0.01)

                key = get_key()

                if key is None:
                    continue

                if key.lower() == "q":
                    node.send_command("STOP")
                    print("\nQuit")
                    break

                command = node.command_for_terminal_key(key)

                if command is not None:
                    print(f"\nCommand: {command}")
                    node.send_command(command)

    except (KeyboardInterrupt, ExternalShutdownException):
        node.send_command("STOP")

    finally:
        node.stop_global_listener()
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
