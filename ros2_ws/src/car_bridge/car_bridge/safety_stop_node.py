import math
from typing import Optional

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class SafetyStopNode(Node):
    def __init__(self) -> None:
        super().__init__('safety_stop_node')

        self.declare_parameter('stop_distance', 0.35)
        self.declare_parameter('front_angle_deg', 30.0)
        self.declare_parameter('allow_turning_when_blocked', True)

        self.stop_distance = float(self.get_parameter('stop_distance').value)
        self.front_angle = math.radians(abs(float(self.get_parameter('front_angle_deg').value)))
        self.allow_turning_when_blocked = bool(
            self.get_parameter('allow_turning_when_blocked').value
        )

        self._front_blocked = False
        self._last_blocked_log_time = self.get_clock().now()

        self.create_subscription(LaserScan, '/scan', self._scan_callback, 10)
        self.create_subscription(Twist, '/cmd_vel_raw', self._cmd_vel_raw_callback, 10)
        self._publisher = self.create_publisher(Twist, '/cmd_vel', 10)

    def _scan_callback(self, msg: LaserScan) -> None:
        blocked = self._scan_has_front_obstacle(msg)
        if blocked != self._front_blocked:
            self._front_blocked = blocked
            if blocked:
                self.get_logger().warn(
                    f'Front obstacle inside {self.stop_distance:.2f} m; blocking forward motion'
                )
            else:
                self.get_logger().info('Front path clear; forward motion allowed')

    def _cmd_vel_raw_callback(self, msg: Twist) -> None:
        safe = Twist()
        safe.linear.x = msg.linear.x
        safe.linear.y = msg.linear.y
        safe.linear.z = msg.linear.z
        safe.angular.x = msg.angular.x
        safe.angular.y = msg.angular.y
        safe.angular.z = msg.angular.z

        if self._front_blocked and safe.linear.x > 0.0:
            safe.linear.x = 0.0
            if not self.allow_turning_when_blocked:
                safe.angular.z = 0.0
            self._log_blocked_command()

        self._publisher.publish(safe)

    def _scan_has_front_obstacle(self, msg: LaserScan) -> bool:
        angle = msg.angle_min
        for distance in msg.ranges:
            if -self.front_angle <= self._normalize_angle(angle) <= self.front_angle:
                if self._valid_distance(distance, msg.range_min, msg.range_max):
                    if distance < self.stop_distance:
                        return True
            angle += msg.angle_increment
        return False

    @staticmethod
    def _valid_distance(distance: float, range_min: float, range_max: float) -> bool:
        return (
            math.isfinite(distance)
            and distance > 0.0
            and distance >= range_min
            and distance <= range_max
        )

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return math.atan2(math.sin(angle), math.cos(angle))

    def _log_blocked_command(self) -> None:
        now = self.get_clock().now()
        elapsed = (now - self._last_blocked_log_time).nanoseconds / 1e9
        if elapsed >= 1.0:
            self.get_logger().warn('Forward command suppressed by lidar safety stop')
            self._last_blocked_log_time = now


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SafetyStopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
