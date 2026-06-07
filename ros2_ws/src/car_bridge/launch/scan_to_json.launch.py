from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    output_path = LaunchConfiguration('output_path')
    max_points = LaunchConfiguration('max_points')
    front_angle_deg = LaunchConfiguration('front_angle_deg')
    stop_distance = LaunchConfiguration('stop_distance')

    return LaunchDescription([
        DeclareLaunchArgument(
            'output_path',
            default_value='/home/roh/lidar_car_project/web_control/static/scan_latest.json',
        ),
        DeclareLaunchArgument('max_points', default_value='720'),
        DeclareLaunchArgument('front_angle_deg', default_value='30.0'),
        DeclareLaunchArgument('stop_distance', default_value='0.35'),
        Node(
            package='car_bridge',
            executable='scan_to_json_node',
            name='scan_to_json_node',
            output='screen',
            parameters=[{
                'output_path': output_path,
                'max_points': ParameterValue(max_points, value_type=int),
                'front_angle_deg': ParameterValue(front_angle_deg, value_type=float),
                'stop_distance': ParameterValue(stop_distance, value_type=float),
            }],
        ),
    ])
