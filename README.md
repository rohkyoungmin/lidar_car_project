# Lidar Auto-drive Vehicle Project

<img width="1920" height="1080" alt="스크린샷 2026-06-07 205349" src="https://github.com/user-attachments/assets/f8959cfb-1bfc-41a2-abbf-0dd527c4ad72" />

Raspberry Pi 4, Arduino Uno R3, RPLIDAR C1, TB6612FNG 2개를 사용하는 4WD differential drive 로봇카 프로젝트입니다.

<img width="4032" height="3024" alt="KakaoTalk_20260607_210739863" src="https://github.com/user-attachments/assets/2c36a01d-7193-4dfb-b8f0-557b212b1da1" />

현재 구현된 범위는 다음입니다.

- PC 브라우저에서 접속하는 IVI 스타일 웹 UI
- Arduino USB Serial 기반 수동 주행
- 바퀴별 PWM scale / invert 튜닝
- 개별 바퀴 테스트
- RPLIDAR `/scan` 실시간 표시
- LiDAR 기반 전/후/좌/우 장애물 감지 표시
- Safe Mode 기반 전진 차단

아직 구현하지 않은 범위:

- SLAM 지도 작성
- Nav2 goal navigation
- 지도 좌표 기반 자율주행

엔코더 odometry가 없기 때문에 현재 LiDAR 화면은 **SLAM map이 아니라 live LiDAR scan view**입니다.

## 1. 하드웨어 상태

- OS: Ubuntu 22.04.5 LTS on Raspberry Pi 4
- ROS2: Humble
- Project root: `~/lidar_car_project`
- ROS2 workspace: `~/lidar_car_project/ros2_ws`
- Arduino Uno R3: `/dev/ttyACM0`
- RPLIDAR C1: `/dev/ttyUSB0`
- RPLIDAR ROS topic: `/scan`
- Motor driver: TB6612FNG 2개
- Drive type: 4WD differential drive

## 2. 전원 안전

반드시 확인하세요.

- 바퀴 테스트는 항상 바퀴를 공중에 띄운 상태에서 합니다.
- 배터리 전원을 바로 뺄 수 있는 상태에서 테스트합니다.
- Arduino 5V는 TB6612 `VCC`, `STBY`에 연결합니다.
- 배터리 `+`는 TB6612 `VM`에만 연결합니다.
- Arduino GND, 배터리 `-`, TB6612 GND는 공통 GND로 묶습니다.
- 배터리 `+`를 Arduino 5V, TB6612 VCC, STBY, 브레드보드 5V 레일에 연결하면 안 됩니다.

## 3. 핀맵

<img width="497" height="810" alt="스크린샷 2026-06-07 210432" src="https://github.com/user-attachments/assets/a5ddac2b-3c9c-4666-8847-48575b3b48e9" />

위 사진은 실제 핀맵을 나타낸 것입니다.
참고하여 배선을 해주십시오.

왼쪽 TB6612:

| Wheel | TB6612 Channel | PWM | IN1 | IN2 |
|---|---|---:|---:|---:|
| Left Rear | A | D5 | D7 | D8 |
| Left Front | B | D6 | D11 | D4 |

오른쪽 TB6612:

| Wheel | TB6612 Channel | PWM | IN1 | IN2 |
|---|---|---:|---:|---:|
| Right Rear | A | D9 | D12 | A0 |
| Right Front | B | D10 | D2 | D3 |

기본 방향 보정값:

```cpp
LR_INVERT = true
LF_INVERT = true
RR_INVERT = false
RF_INVERT = false
```

왼쪽 뒷바퀴가 강하게 도는 증상이 있어 기본 scale은 다음처럼 시작합니다.

```cpp
LR_PWM_SCALE = 0.75
LF_PWM_SCALE = 1.00
RR_PWM_SCALE = 1.00
RF_PWM_SCALE = 1.00
```

웹 UI Settings에서 이 값을 실시간으로 조정할 수 있습니다.

## 4. 프로젝트 구조

```text
lidar_car_project/
  arduino/
    motor_controller/
      motor_controller.ino
    all_wheel_diagnostic/
      all_wheel_diagnostic.ino
    all_wheel_spin_once/
      all_wheel_spin_once.ino
  ros2_ws/
    src/
      car_bridge/
        car_bridge/
          arduino_bridge_node.py
          safety_stop_node.py
          scan_summary_node.py
          scan_to_json_node.py
        config/
          car_bridge.yaml
        launch/
          car_bridge.launch.py
          scan_to_json.launch.py
        package.xml
        setup.py
      sllidar_ros2/
  scripts/
    test_all_wheels.py
    test_drive_serial.py
    test_serial.py
  web_control/
    requirements.txt
    server.py
    static/
      index.html
      app.js
      style.css
      scan_latest.json
```

## 5. Arduino 펌웨어 업로드

자동 업로드는 하지 않습니다. 사용자가 직접 실행합니다.

바퀴를 공중에 띄우고 실행하세요.

```bash
arduino-cli compile --fqbn arduino:avr:uno --upload -p /dev/ttyACM0 ~/lidar_car_project/arduino/motor_controller
```

Arduino가 받는 Serial 명령:

```text
V <linear_x> <angular_z>
SET <LR|LF|RR|RF> <scale>
INV <LR|LF|RR|RF> <0|1>
M <LR|LF|RR|RF> <pwm> <duration_ms>
STOP
```

예:

```text
V 0.080 0.000
V 0.000 0.400
SET LR 0.75
INV LF 1
M RF 80 400
STOP
```

Arduino 안전 동작:

- 부팅 시 전체 정지
- 명령 timeout 시 전체 정지
- 잘못된 명령은 무시
- `STOP` 명령 수신 시 전체 정지

## 6. ROS2 빌드

처음 한 번 또는 ROS2 패키지 수정 후 실행합니다.

```bash
cd ~/lidar_car_project/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## 7. 웹 서버 준비

처음 한 번만 설치합니다.

```bash
cd ~/lidar_car_project/web_control
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 8. 웹 앱 실행

기본 실행:

```bash
cd ~/lidar_car_project/web_control
source .venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8000
```

PC 브라우저에서 접속:

```text
http://<RPi_IP>:8000/?v=14
```

웹 서버가 시작되면 기본적으로 다음도 자동 실행합니다.

```bash
ros2 launch sllidar_ros2 sllidar_c1_launch.py
ros2 launch car_bridge scan_to_json.launch.py
```

즉, 별도 터미널에서 LiDAR launch를 따로 켜지 않아도 됩니다.

자동 LiDAR 실행을 끄고 싶으면:

```bash
AUTO_START_LIDAR=0 uvicorn server:app --host 0.0.0.0 --port 8000
```

이 경우 LiDAR는 직접 실행해야 합니다.

## 9. 수동으로 LiDAR만 확인하는 방법

웹 서버와 분리해서 LiDAR만 확인하고 싶을 때 사용합니다.

Terminal 1:

```bash
source /opt/ros/humble/setup.bash
source ~/lidar_car_project/ros2_ws/install/setup.bash
ros2 launch sllidar_ros2 sllidar_c1_launch.py
```

Terminal 2:

```bash
source /opt/ros/humble/setup.bash
source ~/lidar_car_project/ros2_ws/install/setup.bash
ros2 launch car_bridge scan_to_json.launch.py
```

JSON이 갱신되는지 확인:

```bash
watch -n 0.5 'head -c 300 ~/lidar_car_project/web_control/static/scan_latest.json'
```

## 10. 웹 UI 사용법

상단바:

- 왼쪽 메뉴 버튼: 서랍 열기
- 상태 칩: Serial, Safety, LiDAR 상태 표시
- 중앙: 서비스 이름
- 오른쪽: 날짜와 AM/PM 시간

서랍 메뉴:

- `Auto-Drive`
- `Manual-Drive`
- `Test`
- `Settings`

현재는 Auto-Drive도 실제 자율주행이 아니라 화면 모드입니다. SLAM/Nav2 기반 자율주행은 아직 구현되지 않았습니다.

Manual-Drive:

- 방향 버튼으로 수동 조작
- 키보드도 사용 가능
  - `W` 또는 `ArrowUp`: 전진
  - `S` 또는 `ArrowDown`: 후진
  - `A` 또는 `ArrowLeft`: 좌회전
  - `D` 또는 `ArrowRight`: 우회전
  - `Space`: 정지
- 키를 떼면 정지 명령 전송
- Linear / Angular 속도 조정
- Safe Mode 스위치 ON/OFF

Settings:

- 각 바퀴별 scale 조정
- scale은 슬라이더와 숫자 입력 둘 다 가능
- 각 바퀴별 invert 조정

Test:

- 바퀴별 `Test +`, `Test -`
- 테스트 PWM, duration 조정
- 반드시 바퀴를 공중에 띄운 상태에서 사용

## 11. LiDAR 화면

왼쪽 LiDAR map은 `scan_latest.json`을 읽어서 실시간 점군을 표시합니다.

데이터 흐름:

```text
RPLIDAR C1
  -> ROS2 /scan
  -> scan_to_json_node
  -> web_control/static/scan_latest.json
  -> browser canvas
```

주의:

- 이것은 SLAM map이 아닙니다.
- 현재 프레임의 LiDAR scan을 그리는 live scan view입니다.
- 지도 누적, loop closure, pose graph optimization은 없습니다.

## 12. 장애물 감지와 Safe Mode

오른쪽 자동차 화면은 LiDAR 점군을 전/후/좌/우로 나누어 가까운 물체를 표시합니다.

현재 UI 표시 임계값:

| 상태 | 거리 |
|---|---:|
| Red | `< 0.22 m` |
| Yellow | `< 0.42 m` |
| Green | `< 0.75 m` |
| None | `>= 0.75 m` 또는 감지 없음 |

팝업:

- 장애물이 `0.35 m` 미만이면 LiDAR map 하단에 팝업 표시
- 예: `전방에 장애물이 있습니다.`

Safe Mode ON:

- LiDAR 자동 실행
- scan bridge 자동 실행
- forward command 차단 가능
- LiDAR map 표시
- 자동차 주변 감지 표시

Safe Mode OFF:

- LiDAR 프로세스 종료
- scan bridge 종료
- LiDAR map 초기화
- 오른쪽 자동차 감지 glow 제거

## 13. 테스트 스크립트

모든 테스트는 바퀴를 공중에 띄우고 실행하세요.

전체 바퀴 순차 테스트:

```bash
python3 ~/lidar_car_project/scripts/test_all_wheels.py
```

기본 주행 Serial 테스트:

```bash
python3 ~/lidar_car_project/scripts/test_drive_serial.py
```

기존 간단 Serial 테스트:

```bash
python3 ~/lidar_car_project/scripts/test_serial.py
```

## 14. ROS2 car_bridge 노드

`car_bridge` 패키지에 포함된 노드:

- `scan_to_json_node`
  - `/scan`을 읽어서 `web_control/static/scan_latest.json` 생성
- `scan_summary_node`
  - `/scan`의 front/left/right/rear 거리 요약 출력
- `safety_stop_node`
  - `/scan` 기반으로 `/cmd_vel_raw`를 `/cmd_vel` 안전 명령으로 변환
- `arduino_bridge_node`
  - ROS2 `/cmd_vel`을 Arduino Serial 명령으로 변환

웹 서버 사용 중에는 `arduino_bridge_node`를 동시에 실행하지 마세요.

둘 다 `/dev/ttyACM0`를 열려고 해서 충돌합니다.

## 15. 자주 생기는 문제

### 웹 화면이 예전 디자인으로 보임

브라우저 캐시 문제일 가능성이 큽니다.

```text
http://<RPi_IP>:8000/?v=14
```

또는 브라우저에서 강력 새로고침:

```text
Ctrl + Shift + R
```

### LiDAR map이 비어 있음

확인 순서:

```bash
ros2 topic list | grep scan
```

```bash
ros2 topic echo /scan --once
```

```bash
head -c 300 ~/lidar_car_project/web_control/static/scan_latest.json
```

`scan_latest.json`의 `points`가 비어 있으면 `/scan` 또는 `scan_to_json_node` 쪽을 확인합니다.

### Forward만 안 됨

Safe Mode가 전진을 차단하고 있을 수 있습니다.

- LiDAR가 stale인지 확인
- 전방에 물체가 가까운지 확인
- 튜닝 중이면 Safe Mode를 잠깐 끄고 바퀴를 공중에 띄운 상태에서 테스트

### Test는 되는데 Manual drive가 약함

Manual drive는 `V linear angular` 명령을 쓰고, Test는 `M wheel pwm duration` 명령을 씁니다.

Manual drive가 약하면 Arduino의 다음 값을 조정합니다.

```cpp
TURN_SPEED_GAIN
MIN_DRIVE_PWM
MAX_PWM
```

### Serial 연결이 Off로 보임

확인:

```bash
ls -l /dev/ttyACM0
```

Arduino가 다른 프로그램에 의해 열려 있으면 웹 서버가 Serial을 열 수 없습니다.

## 16. SLAM으로 가려면

현재는 SLAM이 아닙니다.

SLAM을 하려면 최소한 다음이 필요합니다.

```text
LiDAR /scan
encoder odometry /odom
TF: map -> odom -> base_link -> laser
slam_toolbox
```

다음 개발 단계:

1. 바퀴 엔코더 추가
2. Arduino에서 encoder tick 읽기
3. ROS2 `encoder_odom_node.py` 작성
4. `/odom` publish
5. `odom -> base_link` TF publish
6. `base_link -> laser` static TF 추가
7. `slam_toolbox`로 지도 작성

엔코더 없이 LiDAR만으로 SLAM을 시도할 수는 있지만, 4WD 수동 로봇에서는 안정적이지 않습니다.

## 17. 가장 짧은 실행 순서

처음 보는 사람이 따라 할 때는 이 순서만 기억하면 됩니다.

1. Arduino 업로드

```bash
arduino-cli compile --fqbn arduino:avr:uno --upload -p /dev/ttyACM0 ~/lidar_car_project/arduino/motor_controller
```

2. ROS2 빌드

```bash
cd ~/lidar_car_project/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

3. 웹 서버 실행

```bash
cd ~/lidar_car_project/web_control
source .venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8000
```

4. PC 브라우저 접속

```text
http://<RPi_IP>:8000/?v=14
```

5. 바퀴를 공중에 띄우고 Test / Manual부터 확인

6. 실제 바닥 주행은 낮은 속도와 Safe Mode ON 상태에서 시작
