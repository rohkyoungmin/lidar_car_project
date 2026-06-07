import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

def send(ser, cmd, delay=1.5):
    print(f">>> {cmd.strip()}")
    ser.write(cmd.encode("utf-8"))
    ser.flush()
    time.sleep(delay)

    while ser.in_waiting:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            print("<<<", line)

print(f"Opening {PORT}...")
ser = serial.Serial(PORT, BAUD, timeout=1)

# Arduino Uno resets when serial port opens.
print("Waiting for Arduino reset...")
time.sleep(2.5)

while ser.in_waiting:
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print("<<<", line)

try:
    send(ser, "STOP\n", 1.0)

    send(ser, "M LR 100 1000\n", 1.5)
    send(ser, "STOP\n", 1.0)

    send(ser, "M LF 100 1000\n", 1.5)
    send(ser, "STOP\n", 1.0)

    send(ser, "M LR -100 1000\n", 1.5)
    send(ser, "STOP\n", 1.0)

    send(ser, "M LF -100 1000\n", 1.5)
    send(ser, "STOP\n", 1.0)

finally:
    ser.write(b"STOP\n")
    ser.close()
    print("Closed.")
