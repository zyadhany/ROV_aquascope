import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'rov_system'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Only hardware/core launch files remain here. 
        # (e.g. rov.launch.py)
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='zyadhany',
    maintainer_email='zyadhany@todo.todo',
    description='Core Python backend, thruster mixing, and hardware control nodes for the ROV.',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            "rov_controller = rov_system.rov_controller:main",
            "keyboard_controller = rov_system.keyboard:main",
            "depth_controller = rov_system.depth_controller:main",
            "gateway_server = rov_system.gateway_server:main",
            "gateway_api_server = rov_system.mcu_api_gateway:main",
            "mcu_gateway = rov_system.mcu_gateway:main",
            "camera_streamer = rov_system.camera_streamer:main",
            "joystick_controller = rov_system.joystick_controller:main",
        ],
    },
)