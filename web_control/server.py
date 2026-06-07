"""FastAPI manual controller for the lidar car.

SAFETY:
Run wheel tests only with the wheels lifted off the ground or motor power
disconnected. This server sends STOP at startup, shutdown, command timeout, and
when LiDAR safety blocks forward motion.
"""

import asyncio
import json
import math
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

import serial
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
SCAN_PATH = STATIC_DIR / 'scan_latest.json'

SERIAL_PORT = '/dev/ttyACM0'
BAUDRATE = 115200
ARDUINO_RESET_DELAY = 2.5
MAX_LINEAR = 0.15
MAX_ANGULAR = 0.6
COMMAND_TIMEOUT = 0.7
STOP_DISTANCE = 0.35
SCAN_STALE_SECONDS = 1.0
MAX_DIRECTION_DURATION = 1.0
WHEELS = {'LR', 'LF', 'RR', 'RF'}
AUTO_START_LIDAR = os.getenv('AUTO_START_LIDAR', '1').lower() not in {
    '0',
    'false',
    'no',
    'off',
}
ROS_SETUP = (
    'source /opt/ros/humble/setup.bash && '
    'source /home/roh/lidar_car_project/ros2_ws/install/setup.bash'
)


class DriveRequest(BaseModel):
    linear: float = 0.0
    angular: float = 0.0


class DirectionRequest(BaseModel):
    angle: float = 0.0
    duration: float = 0.5
    speed: float = 0.08


class WheelTuningRequest(BaseModel):
    wheel: str
    scale: Optional[float] = None
    invert: Optional[bool] = None


class WheelTestRequest(BaseModel):
    wheel: str
    pwm: int = 80
    duration: float = 0.5


class SafeModeRequest(BaseModel):
    enabled: bool = True


class ControllerState:
    def __init__(self) -> None:
        self.serial_port = SERIAL_PORT
        self.baudrate = BAUDRATE
        self.serial_conn: Optional[serial.Serial] = None
        self.lock = asyncio.Lock()
        self.last_command = 'V 0.000 0.000'
        self.last_command_time = 0.0
        self.connected = False
        self.safety_stop_active = True
        self.lidar_stale = True
        self.front_min: Optional[float] = None
        self.safe_mode = True
        self.wheel_scales = {
            'LR': 0.75,
            'LF': 1.00,
            'RR': 1.00,
            'RF': 1.00,
        }
        self.wheel_inverts = {
            'LR': True,
            'LF': True,
            'RR': False,
            'RF': False,
        }
        self.watchdog_task: Optional[asyncio.Task] = None
        self.safety_task: Optional[asyncio.Task] = None
        self.lidar_process: Optional[subprocess.Popen] = None
        self.scan_bridge_process: Optional[subprocess.Popen] = None


state = ControllerState()
app = FastAPI(title='Lidar Car Web Control')
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


@app.on_event('startup')
async def startup() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    if AUTO_START_LIDAR:
        state.lidar_process = start_ros_process(
            'lidar',
            'ros2 launch sllidar_ros2 sllidar_c1_launch.py',
        )
        await asyncio.sleep(2.0)
        state.scan_bridge_process = start_ros_process(
            'scan_to_json',
            'ros2 launch car_bridge scan_to_json.launch.py',
        )
    open_serial()
    await asyncio.sleep(ARDUINO_RESET_DELAY)
    await send_stop()
    state.watchdog_task = asyncio.create_task(watchdog_loop())
    state.safety_task = asyncio.create_task(safety_loop())


@app.on_event('shutdown')
async def shutdown() -> None:
    for task in (state.watchdog_task, state.safety_task):
        if task:
            task.cancel()
    await send_stop()
    if state.serial_conn and state.serial_conn.is_open:
        state.serial_conn.close()
    state.connected = False
    stop_ros_process(state.scan_bridge_process)
    stop_ros_process(state.lidar_process)


@app.get('/')
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / 'index.html')


@app.post('/api/drive')
async def drive(request: DriveRequest) -> dict:
    linear = clamp(request.linear, -MAX_LINEAR, MAX_LINEAR)
    angular = clamp(request.angular, -MAX_ANGULAR, MAX_ANGULAR)

    if forward_blocked(linear):
        await send_stop()
        return status_payload(blocked=True, command=state.last_command)

    command = await send_velocity(linear, angular)
    return status_payload(blocked=False, command=command)


@app.post('/api/stop')
async def stop() -> dict:
    command = await send_stop()
    return status_payload(blocked=False, command=command)


@app.post('/api/direction')
async def direction(request: DirectionRequest) -> dict:
    duration = clamp(request.duration, 0.1, MAX_DIRECTION_DURATION)
    speed = clamp(abs(request.speed), 0.02, MAX_LINEAR)
    angle = clamp(request.angle, -math.pi, math.pi)

    turn_duration = clamp(abs(angle) / math.pi * MAX_DIRECTION_DURATION, 0.15, MAX_DIRECTION_DURATION)
    angular = MAX_ANGULAR if angle > 0.0 else -MAX_ANGULAR

    if abs(angle) > 0.08:
        await hold_velocity(0.0, angular, turn_duration)

    if forward_blocked(speed):
        await send_stop()
        return status_payload(blocked=True, command=state.last_command)

    await hold_velocity(speed, 0.0, duration)
    command = await send_stop()
    return status_payload(blocked=False, command=command)


@app.post('/api/tuning')
async def tuning(request: WheelTuningRequest) -> dict:
    wheel = normalize_wheel(request.wheel)

    await send_stop()
    if request.scale is not None:
        scale = clamp(request.scale, 0.0, 1.0)
        state.wheel_scales[wheel] = scale
        await send_raw_command(f'SET {wheel} {scale:.2f}')

    if request.invert is not None:
        invert_value = 1 if request.invert else 0
        state.wheel_inverts[wheel] = request.invert
        await send_raw_command(f'INV {wheel} {invert_value}')

    await send_stop()
    return status_payload(blocked=False, command=state.last_command)


@app.post('/api/wheel_test')
async def wheel_test(request: WheelTestRequest) -> dict:
    wheel = normalize_wheel(request.wheel)
    pwm = int(clamp(request.pwm, -120, 120))
    duration_ms = int(clamp(request.duration, 0.1, 0.7) * 1000)

    await send_stop()
    command = await send_raw_command(f'M {wheel} {pwm} {duration_ms}')
    await asyncio.sleep(duration_ms / 1000.0 + 0.1)
    await send_stop()
    return status_payload(blocked=False, command=command)


@app.post('/api/safe_mode')
async def safe_mode(request: SafeModeRequest) -> dict:
    state.safe_mode = request.enabled
    if state.safe_mode:
        ensure_lidar_running()
        read_scan_safety()
        if state.safety_stop_active:
            await send_stop()
    else:
        state.safety_stop_active = False
        stop_ros_process(state.scan_bridge_process)
        state.scan_bridge_process = None
        stop_ros_process(state.lidar_process)
        state.lidar_process = None
        state.lidar_stale = True
        state.front_min = None
        write_empty_scan()
    return status_payload(blocked=False, command=state.last_command)


@app.get('/api/status')
async def status() -> dict:
    return status_payload(blocked=state.safety_stop_active, command=state.last_command)


def open_serial() -> None:
    try:
        state.serial_conn = serial.Serial(
            SERIAL_PORT,
            BAUDRATE,
            timeout=1.0,
            write_timeout=1.0,
        )
        state.connected = True
    except serial.SerialException as exc:
        state.serial_conn = None
        state.connected = False
        state.last_command = f'serial open failed: {exc}'


def start_ros_process(name: str, command: str) -> Optional[subprocess.Popen]:
    full_command = f'{ROS_SETUP} && {command}'
    try:
        process = subprocess.Popen(
            ['bash', '-lc', full_command],
            cwd='/home/roh/lidar_car_project/ros2_ws',
            preexec_fn=os.setsid,
        )
        print(f'Started {name}: pid={process.pid}', flush=True)
        return process
    except OSError as exc:
        state.last_command = f'{name} start failed: {exc}'
        print(state.last_command, flush=True)
        return None


def ensure_lidar_running() -> None:
    if not AUTO_START_LIDAR:
        return

    if not process_running(state.lidar_process):
        state.lidar_process = start_ros_process(
            'lidar',
            'ros2 launch sllidar_ros2 sllidar_c1_launch.py',
        )
        time.sleep(2.0)

    if not process_running(state.scan_bridge_process):
        state.scan_bridge_process = start_ros_process(
            'scan_to_json',
            'ros2 launch car_bridge scan_to_json.launch.py',
        )


def stop_ros_process(process: Optional[subprocess.Popen]) -> None:
    if process is None or process.poll() is not None:
        return

    try:
        os.killpg(os.getpgid(process.pid), signal.SIGINT)
        process.wait(timeout=5.0)
    except (OSError, subprocess.TimeoutExpired):
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except OSError:
            pass


async def watchdog_loop() -> None:
    while True:
        await asyncio.sleep(0.1)
        if time.monotonic() - state.last_command_time > COMMAND_TIMEOUT:
            await send_stop()


async def safety_loop() -> None:
    while True:
        read_scan_safety()
        if state.safety_stop_active and is_forward_command(state.last_command):
            await send_stop()
        await asyncio.sleep(0.2)


def read_scan_safety() -> None:
    try:
        payload = json.loads(SCAN_PATH.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        state.lidar_stale = True
        state.safety_stop_active = state.safe_mode
        state.front_min = None
        return

    stamp = float(payload.get('stamp') or 0.0)
    front_min = payload.get('front_min')
    now = time.time()
    state.lidar_stale = (now - stamp) > SCAN_STALE_SECONDS
    state.front_min = float(front_min) if isinstance(front_min, (int, float)) else None
    close_obstacle = state.front_min is not None and state.front_min < STOP_DISTANCE
    state.safety_stop_active = state.safe_mode and (state.lidar_stale or close_obstacle)


def write_empty_scan() -> None:
    payload = {
        'stamp': time.time(),
        'points': [],
        'front_min': None,
        'stop_distance': STOP_DISTANCE,
    }
    try:
        SCAN_PATH.write_text(json.dumps(payload, separators=(',', ':')) + '\n', encoding='utf-8')
    except OSError as exc:
        state.last_command = f'clear scan failed: {exc}'


def forward_blocked(linear: float) -> bool:
    return state.safe_mode and linear > 0.0 and state.safety_stop_active


def is_forward_command(command: str) -> bool:
    parts = command.split()
    if len(parts) < 3 or parts[0] != 'V':
        return False
    try:
        return float(parts[1]) > 0.0
    except ValueError:
        return False


async def send_stop() -> str:
    return await send_raw_command('STOP')


async def hold_velocity(linear: float, angular: float, duration: float) -> None:
    end_time = time.monotonic() + duration
    while time.monotonic() < end_time:
        await send_velocity(linear, angular)
        await asyncio.sleep(0.25)


async def send_velocity(linear: float, angular: float) -> str:
    command = f'V {linear:.3f} {angular:.3f}'
    return await send_raw_command(command)


async def send_raw_command(command: str) -> str:
    async with state.lock:
        state.last_command = command
        state.last_command_time = time.monotonic()
        if not state.serial_conn or not state.serial_conn.is_open:
            state.connected = False
            return command
        try:
            state.serial_conn.write((command + '\n').encode('ascii'))
            state.serial_conn.flush()
            state.connected = True
        except serial.SerialException as exc:
            state.connected = False
            state.last_command = f'serial write failed: {exc}'
    return command


def status_payload(blocked: bool, command: str) -> dict:
    safety_reason = 'off'
    if state.safe_mode and state.lidar_stale:
        safety_reason = 'lidar_stale'
    elif state.safe_mode and state.front_min is not None and state.front_min < STOP_DISTANCE:
        safety_reason = 'front_obstacle'
    elif state.safe_mode:
        safety_reason = 'clear'

    return {
        'connected': state.connected,
        'last_command': command,
        'safety_stop_active': state.safety_stop_active or blocked,
        'safety_reason': safety_reason,
        'lidar_stale': state.lidar_stale,
        'front_min': state.front_min,
        'safe_mode': state.safe_mode,
        'wheel_scales': state.wheel_scales,
        'wheel_inverts': state.wheel_inverts,
        'auto_start_lidar': AUTO_START_LIDAR,
        'lidar_process_running': process_running(state.lidar_process),
        'scan_bridge_process_running': process_running(state.scan_bridge_process),
        'limits': {
            'max_linear': MAX_LINEAR,
            'max_angular': MAX_ANGULAR,
            'command_timeout': COMMAND_TIMEOUT,
            'stop_distance': STOP_DISTANCE,
        },
    }


def clamp(value: float, lower: float, upper: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return min(max(value, lower), upper)


def normalize_wheel(wheel: str) -> str:
    normalized = wheel.strip().upper()
    if normalized not in WHEELS:
        raise HTTPException(status_code=400, detail=f'unknown wheel: {wheel}')
    return normalized


def process_running(process: Optional[subprocess.Popen]) -> bool:
    return process is not None and process.poll() is None
