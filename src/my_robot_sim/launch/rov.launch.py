#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="my_robot_sim",
            executable="rov_controller",
            name="rov_controller",
            output="screen",
            emulate_tty=True,
            respawn=True,
            respawn_delay=2.0,
        ),

        Node(
            package="my_robot_sim",
            executable="mcu_gateway",
            name="mcu_gateway",
            output="screen",
            emulate_tty=True,
            respawn=True,
            respawn_delay=2.0,
        ),

        Node(
            package="my_robot_sim",
            executable="depth_controller",
            name="depth_controller",
            output="screen",
            emulate_tty=True,
            respawn=True,
            respawn_delay=2.0,
        ),

        Node(
            package="my_robot_sim",
            executable="camera_streamer",
            name="camera_streamer",
            output="screen",
            emulate_tty=True,
            respawn=True,
            respawn_delay=2.0,
        ),
    ])