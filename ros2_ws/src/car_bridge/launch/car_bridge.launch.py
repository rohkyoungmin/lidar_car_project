from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    serial_port = LaunchConfiguration('serial_port')
    baudrate = LaunchConfiguration('baudrate')
    max_linear = LaunchConfiguration('max_linear')
    max_angular = LaunchConfiguration('max_angular')
    stop_distance = LaunchConfiguration('stop_distance')
    front_angle_deg = LaunchConfiguration('front_angle_deg')
    dry_run = LaunchConfiguration('dry_run')

    return LaunchDescription([
        DeclareLaunchArgument('serial_port', default_value='/dev/ttyACM0'),
        DeclareLaunchArgument('baudrate', default_value='115200'),
        DeclareLaunchArgument('max_linear', default_value='0.25'),
        DeclareLaunchArgument('max_angular', default_value='1.0'),
        DeclareLaunchArgument('stop_distance', default_value='0.35'),
        DeclareLaunchArgument('front_angle_deg', default_value='30.0'),
        DeclareLaunchArgument('dry_run', default_value='false'),
        Node(
            package='car_bridge',
            executable='safety_stop_node',
            name='safety_stop_node',
            output='screen',
            parameters=[{
                'stop_distance': ParameterValue(stop_distance, value_type=float),
                'front_angle_deg': ParameterValue(front_angle_deg, value_type=float),
            }],
        ),
        Node(
            package='car_bridge',
            executable='arduino_bridge_node',
            name='arduino_bridge_node',
            output='screen',
            parameters=[{
                'serial_port': serial_port,
                'baudrate': ParameterValue(baudrate, value_type=int),
                'max_linear': ParameterValue(max_linear, value_type=float),
                'max_angular': ParameterValue(max_angular, value_type=float),
                'dry_run': ParameterValue(dry_run, value_type=bool),
            }],
        ),
    ])
