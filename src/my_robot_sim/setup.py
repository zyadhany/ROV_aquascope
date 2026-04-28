import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'my_robot_sim'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', 'my_robot_sim', 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', 'my_robot_sim', 'worlds'), glob('worlds/*')),
        (os.path.join('share', 'my_robot_sim', 'models', 'simple_bot'), glob('models/simple_bot/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='zyadhany',
    maintainer_email='zyadhany@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },

    
    entry_points={
        'console_scripts': [
            "rov_controller = my_robot_sim.rov_controller:main",
            "keyboard_controller = my_robot_sim.keyboard:main",
            'depth_hold_node = my_robot_sim.depth_hold_node:main',
            'server = my_robot_sim.server:main',
            "microcontroller_sim = my_robot_sim.sim.microcontroller_sim:main",
            "mcu_gateway = my_robot_sim.mcu_gateway:main",
            'camera_streamer = my_robot_sim.camera_streamer:main',
        ],
    },
)
