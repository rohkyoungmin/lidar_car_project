import math
from typing import Optional

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

try:
    import serial
    from serial import SerialException
except ImportError:  # pragma: no cover - exercised on systems without pyserial
    serial = None
    SerialException = Exception


class ArduinoBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__('arduino_bridge_node')

        self.declare_parameter('serial_port', '/dev/ttyACM0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('max_linear', 0.25)
        self.declare_parameter('max_angular', 1.0)
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('dry_run', False)

        self.serial_port = self.get_parameter('serial_port').value
        self.baudrate = int(self.get_parameter('baudrate').value)
        self.max_linear = abs(float(self.get_parameter('max_linear').value))
        self.max_angular = abs(float(self.get_parameter('max_angular').value))
        self.cmd_timeout = max(0.0, float(self.get_parameter('cmd_timeout').value))
        self.dry_run = bool(self.get_parameter('dry_run').value)

        self._serial: Optional['serial.Serial'] = None
        self._last_cmd_time = self.get_clock().now()
        self._last_sent_command = ''
        self._serial_error_reported = False

        if self.dry_run:
            self.get_logger().warn('dry_run is true: serial port will not be opened')
        else:
            self._open_serial()

        self.create_subscription(Twist, '/cmd_vel', self._cmd_vel_callback, 10)
        self.create_timer(0.05, self._watchdog_callback)
        self._send_velocity(0.0, 0.0)

    def _open_serial(self) -> None:
        if serial is None:
            self.get_logger().error(
                'pyserial is not available. Install python3-serial, or run with dry_run:=true.'
            )
            return

        try:
            self._serial = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=0.1,
                write_timeout=0.1,
            )
            self.get_logger().info(
                f'Opened Arduino serial port {self.serial_port} at {self.baudrate} baud'
            )
        except SerialException as exc:
            self._serial = None
            self.get_logger().error(
                f'Could not open serial port {self.serial_port}: {exc}. '
                'No motion commands will be sent.'
            )

    def _cmd_vel_callback(self, msg: Twist) -> None:
        self._last_cmd_time = self.get_clock().now()
        linear_x = self._clamp(msg.linear.x, -self.max_linear, self.max_linear)
        angular_z = self._clamp(msg.angular.z, -self.max_angular, self.max_angular)
        self._send_velocity(linear_x, angular_z)

    def _watchdog_callback(self) -> None:
        age = (self.get_clock().now() - self._last_cmd_time).nanoseconds / 1e9
        if age > self.cmd_timeout:
            self._send_velocity(0.0, 0.0)

    def _send_velocity(self, linear_x: float, angular_z: float) -> None:
        command = f'V {linear_x:.3f} {angular_z:.3f}\n'

        if self.dry_run:
            if command != self._last_sent_command:
                self.get_logger().info(f'dry_run serial command: {command.strip()}')
            self._last_sent_command = command
            return

        if self._serial is None or not self._serial.is_open:
            if not self._serial_error_reported:
                self.get_logger().error('Serial port is not open; command not sent')
                self._serial_error_reported = True
            return

        try:
            self._serial.write(command.encode('ascii'))
            self._serial.flush()
            self._serial_error_reported = False
            self._last_sent_command = command
        except SerialException as exc:
            self.get_logger().error(f'Serial write failed: {exc}')
            self._serial_error_reported = True

    def stop_and_close(self) -> None:
        self._send_velocity(0.0, 0.0)
        if self._serial is not None and self._serial.is_open:
            try:
                self._serial.close()
                self.get_logger().info('Closed Arduino serial port')
            except SerialException as exc:
                self.get_logger().error(f'Error while closing serial port: {exc}')

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        if not math.isfinite(value):
            return 0.0
        return min(max(value, lower), upper)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ArduinoBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_and_close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
