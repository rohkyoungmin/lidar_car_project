import math
from typing import Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class ScanSummaryNode(Node):
    def __init__(self) -> None:
        super().__init__('scan_summary_node')
        self._latest_scan: Optional[LaserScan] = None
        self.create_subscription(LaserScan, '/scan', self._scan_callback, 10)
        self.create_timer(1.0, self._timer_callback)

    def _scan_callback(self, msg: LaserScan) -> None:
        self._latest_scan = msg

    def _timer_callback(self) -> None:
        if self._latest_scan is None:
            self.get_logger().info('Waiting for /scan...')
            return

        msg = self._latest_scan
        summary = {
            'front_min': self._sector_min(msg, -30.0, 30.0),
            'left_min': self._sector_min(msg, 60.0, 120.0),
            'right_min': self._sector_min(msg, -120.0, -60.0),
            'rear_min': self._sector_min(msg, 150.0, -150.0),
        }
        text = ', '.join(f'{key}={self._format_distance(value)}' for key, value in summary.items())
        self.get_logger().info(text)

    def _sector_min(self, msg: LaserScan, start_deg: float, end_deg: float) -> Optional[float]:
        start = math.radians(start_deg)
        end = math.radians(end_deg)
        values = []

        angle = msg.angle_min
        for distance in msg.ranges:
            normalized = self._normalize_angle(angle)
            if self._angle_in_sector(normalized, start, end):
                if self._valid_distance(distance, msg.range_min, msg.range_max):
                    values.append(distance)
            angle += msg.angle_increment

        return min(values) if values else None

    @staticmethod
    def _angle_in_sector(angle: float, start: float, end: float) -> bool:
        start = ScanSummaryNode._normalize_angle(start)
        end = ScanSummaryNode._normalize_angle(end)
        if start <= end:
            return start <= angle <= end
        return angle >= start or angle <= end

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

    @staticmethod
    def _format_distance(distance: Optional[float]) -> str:
        if distance is None:
            return 'n/a'
        return f'{distance:.2f}m'


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ScanSummaryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
