#!/usr/bin/env python3
"""Direct serial drive test.

SAFETY WARNING: Run this only with the wheels lifted off the ground or motor
power disconnected. This script sends motion commands directly to the Arduino.
"""

import time

import serial


SERIAL_PORT = '/dev/ttyACM0'
BAUDRATE = 115200
COMMANDS = [
    'V 0.000 0.000',
    'V 0.080 0.000',
    'V 0.000 0.000',
    'V -0.080 0.000',
    'V 0.000 0.000',
    'V 0.000 0.400',
    'V 0.000 0.000',
    'V 0.000 -0.400',
    'V 0.000 0.000',
]


def send_command(port: serial.Serial, command: str) -> None:
    print(f'sending: {command}')
    port.write((command + '\n').encode('ascii'))
    port.flush()


def main() -> None:
    arduino = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1.0, write_timeout=1.0)
    try:
        print(f'opened {SERIAL_PORT} at {BAUDRATE}; waiting for Arduino reset')
        time.sleep(2.5)
        for command in COMMANDS:
            send_command(arduino, command)
            time.sleep(1.5)
    finally:
        try:
            send_command(arduino, 'V 0.000 0.000')
        finally:
            arduino.close()
            print('serial closed')


if __name__ == '__main__':
    main()
