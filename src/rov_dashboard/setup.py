from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'rov_dashboard'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.json')),
        (os.path.join('share', package_name, 'web'), glob('web/*')),
        (os.path.join('share', package_name, 'web'), glob('web/js/*')),
    ],
    install_requires=['setuptools', 'fastapi', 'uvicorn'],
    zip_safe=True,
    maintainer='zyadhany',
    maintainer_email='zeyad.hany2003@gmail.com',
    description='Flowchart dashboard MVP for an ROV',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'dashboard_backend = rov_dashboard.dashboard_backend:main',
        ],
    },
)
