from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

pkg_share = get_package_share_directory('my_robot_sim')

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

    return [gazebo]




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
                    '/rov/ballast_cmd@std_msgs/msg/Int32]gz.msgs.Int32',
                     '/rov/depth/current@std_msgs/msg/Float64[gz.msgs.Double',
                     '/rov/camera/image@sensor_msgs/msg/Image@gz.msgs.Image'
                ],
                output='screen'
            ),

            Node(
                package='ros_gz_image',
                executable='image_bridge',
                arguments=['/rov/camera/image'],
                parameters=[{'qos': 'sensor_data'}],
                output='screen'
            ),
        ]
    )

    return [bridge]

def ros_node():
    thrusters_node = TimerAction(
        period=1.0,
        actions=[
            Node(
                package='my_robot_sim',
                executable='robot_controller',
                output='screen'
            )
        ]
    )

    pumb_node = TimerAction(
        period=1.0,
        actions=[
            Node(
                package='my_robot_sim',
                executable='depth_hold_node',
                output='screen'
            )
        ]
    )
    return [thrusters_node, pumb_node]

def generate_launch_description():

    cmd_lunch = []
    cmd_lunch.extend(start_gazebo())
    cmd_lunch.extend(start_bridge())
    cmd_lunch.extend(ros_node())

    return LaunchDescription(cmd_lunch)