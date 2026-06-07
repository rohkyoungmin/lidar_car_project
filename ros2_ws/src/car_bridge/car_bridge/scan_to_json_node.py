import json
import math
import os
import tempfile
from typing import List, Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class ScanToJsonNode(Node):
    """Write a compact LaserScan snapshot for the local web UI.

    Safety note: this node only writes scan data. It does not command motors.
    The web server treats stale scan data as unsafe for forward motion.
    """

    def __init__(self) -> None:
        super().__init__('scan_to_json_node')

        self.declare_parameter(
            'output_path',
            '/home/roh/lidar_car_project/web_control/static/scan_latest.json',
        )
        self.declare_parameter('max_points', 720)
        self.declare_parameter('front_angle_deg', 30.0)
        self.declare_parameter('stop_distance', 0.35)

        self.output_path = str(self.get_parameter('output_path').value)
        self.max_points = max(1, int(self.get_parameter('max_points').value))
        self.front_angle = math.radians(abs(float(self.get_parameter('front_angle_deg').value)))
        self.stop_distance = float(self.get_parameter('stop_distance').value)

        self._latest_scan: Optional[LaserScan] = None
        self.create_subscription(LaserScan, '/scan', self._scan_callback, 10)
        self.create_timer(0.2, self._write_latest_scan)

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        self.get_logger().info(f'Writing scan JSON to {self.output_path}')

    def _scan_callback(self, msg: LaserScan) -> None:
        self._latest_scan = msg

    def _write_latest_scan(self) -> None:
        if self._latest_scan is None:
            return

        msg = self._latest_scan
        points = self._scan_points(msg)
        front_min = self._front_min(msg)
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9
        if stamp == 0.0:
            stamp = self.get_clock().now().nanoseconds / 1e9

        payload = {
            'stamp': stamp,
            'points': points,
            'front_min': front_min,
            'stop_distance': self.stop_distance,
        }
        self._atomic_write_json(payload)

    def _scan_points(self, msg: LaserScan) -> List[dict]:
        total = len(msg.ranges)
        stride = max(1, math.ceil(total / self.max_points))
        points = []

        for index in range(0, total, stride):
            distance = msg.ranges[index]
            if not self._valid_distance(distance, msg.range_min, msg.range_max):
                continue

            angle = self._normalize_angle(msg.angle_min + index * msg.angle_increment)
            points.append({
                'x': round(distance * math.sin(angle), 4),
                'y': round(distance * math.cos(angle), 4),
                'r': round(distance, 4),
                'angle': round(angle, 4),
            })

        return points

    def _front_min(self, msg: LaserScan) -> Optional[float]:
        values = []
        for index, distance in enumerate(msg.ranges):
            angle = self._normalize_angle(msg.angle_min + index * msg.angle_increment)
            if abs(angle) > self.front_angle:
                continue
            if self._valid_distance(distance, msg.range_min, msg.range_max):
                values.append(distance)
        return round(min(values), 4) if values else None

    def _atomic_write_json(self, payload: dict) -> None:
        directory = os.path.dirname(self.output_path)
        fd, temp_path = tempfile.mkstemp(prefix='.scan_', suffix='.json', dir=directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as file:
                json.dump(payload, file, separators=(',', ':'))
                file.write('\n')
            os.replace(temp_path, self.output_path)
        except OSError as exc:
            self.get_logger().error(f'Failed to write scan JSON: {exc}')
            try:
                os.unlink(temp_path)
            except OSError:
                pass

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


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ScanToJsonNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
