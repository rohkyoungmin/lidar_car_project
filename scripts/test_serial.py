#!/usr/bin/env python3
"""Simple Arduino serial smoke test.

WARNING: Lift the car wheels off the ground or disconnect motor power before
running this script. It sends motion commands directly to the Arduino.
"""

import time

import serial


SERIAL_PORT = '/dev/ttyACM0'
BAUDRATE = 115200
COMMANDS = [
    'V 0.000 0.000',
    'V 0.100 0.000',
    'V 0.000 0.000',
    'V 0.000 0.500',
    'V 0.000 0.000',
]


def main() -> None:
    with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1.0, write_timeout=1.0) as arduino:
        time.sleep(2.0)
        for command in COMMANDS:
            print(f'sending: {command}')
            arduino.write((command + '\n').encode('ascii'))
            arduino.flush()
            time.sleep(1.0)


if __name__ == '__main__':
    main()
