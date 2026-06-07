from glob import glob
from setuptools import find_packages, setup

package_name = 'car_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='roh',
    maintainer_email='roh@example.com',
    description='Safe ROS2 to Arduino serial bridge for a lidar car.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'arduino_bridge_node = car_bridge.arduino_bridge_node:main',
            'safety_stop_node = car_bridge.safety_stop_node:main',
            'scan_summary_node = car_bridge.scan_summary_node:main',
            'scan_to_json_node = car_bridge.scan_to_json_node:main',
        ],
    },
)
