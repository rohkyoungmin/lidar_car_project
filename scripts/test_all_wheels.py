#!/usr/bin/env python3
"""Serial diagnostic for all four wheels.

SAFETY WARNING:
Run this only with all wheels lifted off the ground or motor power disconnected.
This sends direct motor diagnostic commands to the Arduino.
"""

import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

commands = [
    "STOP\n",
    "M LR 100 1000\n",
    "M LF 100 1000\n",
    "M RR 100 1000\n",
    "M RF 100 1000\n",
    "M LR -100 1000\n",
    "M LF -100 1000\n",
    "M RR -100 1000\n",
    "M RF -100 1000\n",
    "SIDE L 100 1000\n",
    "SIDE L -100 1000\n",
    "SIDE R 100 1000\n",
    "SIDE R -100 1000\n",
    "ALL 100 1000\n",
    "ALL -100 1000\n",
    "STOP\n",
]

def read_available(ser):
    time.sleep(0.2)
    while ser.in_waiting:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            print("<<<", line)

print(f"Opening {PORT}")
ser = serial.Serial(PORT, BAUD, timeout=1)

print("Waiting for Arduino reset...")
time.sleep(2.5)
read_available(ser)

try:
    for cmd in commands:
        print(">>>", cmd.strip())
        ser.write(cmd.encode())
        ser.flush()
        read_available(ser)
        time.sleep(1.5)
finally:
    ser.write(b"STOP\n")
    ser.close()
    print("Closed.")
