from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, ExecuteProcess, TimerAction
from launch_ros.actions import Node
from ament_index_python.packages import get_package_prefix
from ament_index_python.packages import get_package_share_directory
import os

# UPDATED: Point to the new simulation package for models/worlds
pkg_share = get_package_share_directory('rov_sim')

# UPDATED: Point to the new simulation package for C++ plugins
plugin_prefix = get_package_prefix('rov_sim')

models_path = os.path.join(pkg_share, 'models')
plugins_path = os.path.join(plugin_prefix, 'lib')

def start_gazebo():
    world_path = os.path.join(pkg_share, 'worlds', 'empty.world')
    gazebo = ExecuteProcess(
        cmd=['gz', 'sim', world_path],
        output='screen'
    )

    start_simulation = TimerAction(
        period=1.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    'gz', 'service', '-s', '/world/pool_world/control',
                    '--reqtype', 'gz.msgs.WorldControl',
                    '--reptype', 'gz.msgs.Boolean',
                    '--timeout', '300',
                    '--req', 'pause: false'
                ],
                output='screen'
            )
        ]
    ) 

    return [gazebo, start_simulation]


def start_bridge():
    bridge = TimerAction(
    period=5.0,
    actions=[
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '/model/rov/joint/left_thruster_joint/cmd_thrust@std_msgs/msg/Float64]gz.msgs.Double',
                '/model/rov/joint/right_thruster_joint/cmd_thrust@std_msgs/msg/Float64]gz.msgs.Double',
                '/rov/ballast_cmd@std_msgs/msg/Float64]gz.msgs.Double',
                '/rov/depth/current@std_msgs/msg/Float64[gz.msgs.Double',
                '/rov/pressure@sensor_msgs/msg/FluidPressure[gz.msgs.FluidPressure',
                '/rov/light/cmd@std_msgs/msg/Bool]gz.msgs.Boolean',
                '/rov/gripper/open_cmd@std_msgs/msg/Bool]gz.msgs.Boolean',
                '/rov/imu@sensor_msgs/msg/Imu@gz.msgs.IMU',
                '/rov/scanning_sonar/reading@std_msgs/msg/String[gz.msgs.StringMsg',

                '--ros-args',
                '-r', '/model/rov/joint/left_thruster_joint/cmd_thrust:=/sim/left_thruster/cmd',
                '-r', '/model/rov/joint/right_thruster_joint/cmd_thrust:=/sim/right_thruster/cmd',
                '-r', '/rov/ballast_cmd:=/sim/ballast_cmd',
                '-r', '/rov/depth/current:=/sim/depth/current',
                '-r', '/rov/pressure:=/sim/pressure',
                '-r', '/rov/camera/image:=/sim/camera/image',
                '-r', '/rov/light/cmd:=/sim/light/cmd',
                '-r', '/rov/gripper/open_cmd:=/sim/gripper/open_cmd',
                '-r', '/rov/imu:=/sim/imu',
                '-r', '/rov/scanning_sonar/reading:=/sim/scanning_sonar/reading',
            ],
            output='screen'
        ),

        Node(
            package='ros_gz_image',
            executable='image_bridge',
            arguments=[
                '/sim/camera/image',
            ],
            parameters=[{'qos': 'sensor_data'}],
            output='screen'
        ),
        ]
    )
    return [bridge]

def ros_node():
    mcu_node = TimerAction(
        period=1.0,
        actions=[
            Node(
                package='rov_sim',
                executable='microcontroller_sim',
                output='screen'
            )
        ]
    )
    return [mcu_node]

def generate_launch_description():

    cmd_lunch = []
    cmd_lunch.append(
        AppendEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH',
            models_path,
            prepend=True,
        )
    )
    cmd_lunch.append(
        AppendEnvironmentVariable(
            'GZ_SIM_SYSTEM_PLUGIN_PATH',
            plugins_path,
            prepend=True,
        )
    )
    cmd_lunch.extend(start_gazebo())
    cmd_lunch.extend(start_bridge())
    cmd_lunch.extend(ros_node())

    return LaunchDescription(cmd_lunch)