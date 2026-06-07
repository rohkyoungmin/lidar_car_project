/*
  Arduino Uno + two TB6612FNG motor controllers for a 4WD differential car.

  SAFETY:
  - Lift the wheels off the ground or disconnect motor power before testing.
  - The robot must remain stopped until a command is sent by the user.
  - This sketch stops all motors at boot and if commands time out.
  - Battery + goes to TB6612 VM only. Do not connect battery + to Arduino 5V,
    TB6612 VCC/STBY, or a 5V breadboard rail.

  Serial command formats from Raspberry Pi:
    V <linear_x> <angular_z>
    SET <LR|LF|RR|RF> <scale>
    INV <LR|LF|RR|RF> <0|1>
    M <LR|LF|RR|RF> <pwm> <duration_ms>
    STOP
*/

const int LR_PWMA = 5;
const int LR_AIN1 = 7;
const int LR_AIN2 = 8;

const int LF_PWMB = 6;
const int LF_BIN1 = 11;
const int LF_BIN2 = 4;

const int RR_PWMA = 9;
const int RR_AIN1 = 12;
const int RR_AIN2 = A0;

const int RF_PWMB = 10;
const int RF_BIN1 = 2;
const int RF_BIN2 = 3;

// Adjust these after a wheels-lifted direction test.
bool LR_INVERT = true;
bool LF_INVERT = true;
bool RR_INVERT = false;
bool RF_INVERT = false;

// Per-wheel PWM trims. Lower a value if that wheel is stronger than the others.
// LR is reduced because the left rear wheel was observed to be too strong.
float LR_PWM_SCALE = 0.75;
float LF_PWM_SCALE = 1.00;
float RR_PWM_SCALE = 1.00;
float RF_PWM_SCALE = 1.00;

const float WHEEL_BASE = 0.16;
const float TURN_SPEED_GAIN = 0.25;
const float MAX_SPEED = 0.40;
const int MAX_PWM = 140;
const int MIN_DRIVE_PWM = 40;
const unsigned long CMD_TIMEOUT_MS = 500;

unsigned long lastCommandMs = 0;
bool stoppedLogged = false;

void setup() {
  pinMode(LR_PWMA, OUTPUT);
  pinMode(LR_AIN1, OUTPUT);
  pinMode(LR_AIN2, OUTPUT);

  pinMode(LF_PWMB, OUTPUT);
  pinMode(LF_BIN1, OUTPUT);
  pinMode(LF_BIN2, OUTPUT);

  pinMode(RR_PWMA, OUTPUT);
  pinMode(RR_AIN1, OUTPUT);
  pinMode(RR_AIN2, OUTPUT);

  pinMode(RF_PWMB, OUTPUT);
  pinMode(RF_BIN1, OUTPUT);
  pinMode(RF_BIN2, OUTPUT);

  Serial.begin(115200);
  stopAllMotors();
  Serial.println("READY");
  lastCommandMs = millis();
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    parseVelocityCommand(line);
  }

  if (millis() - lastCommandMs > CMD_TIMEOUT_MS) {
    stopAllMotors();
  }
}

void parseVelocityCommand(String line) {
  if (line.length() == 0) {
    return;
  }

  if (line == "STOP") {
    stopAllMotors();
    lastCommandMs = millis();
    return;
  }

  if (line.startsWith("SET ")) {
    parseScaleCommand(line);
    lastCommandMs = millis();
    return;
  }

  if (line.startsWith("INV ")) {
    parseInvertCommand(line);
    lastCommandMs = millis();
    return;
  }

  if (line.startsWith("M ")) {
    parseMotorTestCommand(line);
    lastCommandMs = millis();
    return;
  }

  if (line.charAt(0) != 'V') {
    return;
  }

  int firstSpace = line.indexOf(' ');
  int secondSpace = line.indexOf(' ', firstSpace + 1);
  if (firstSpace < 0 || secondSpace < 0) {
    return;
  }

  float linearX = line.substring(firstSpace + 1, secondSpace).toFloat();
  float angularZ = line.substring(secondSpace + 1).toFloat();

  linearX = constrain(linearX, -MAX_SPEED, MAX_SPEED);
  angularZ = constrain(angularZ, -2.0, 2.0);

  Serial.print("CMD ");
  Serial.print(linearX, 3);
  Serial.print(" ");
  Serial.println(angularZ, 3);

  driveDifferential(linearX, angularZ);
  lastCommandMs = millis();
  stoppedLogged = false;
}

void parseScaleCommand(String line) {
  int s1 = line.indexOf(' ');
  int s2 = line.indexOf(' ', s1 + 1);
  if (s1 < 0 || s2 < 0) {
    return;
  }

  String wheel = line.substring(s1 + 1, s2);
  float scale = constrain(line.substring(s2 + 1).toFloat(), 0.0, 1.0);
  float *target = scaleForWheel(wheel);
  if (target == NULL) {
    Serial.println("BAD SET WHEEL");
    return;
  }

  *target = scale;
  stopAllMotors();
  Serial.print("SET ");
  Serial.print(wheel);
  Serial.print(" ");
  Serial.println(scale, 2);
}

void parseInvertCommand(String line) {
  int s1 = line.indexOf(' ');
  int s2 = line.indexOf(' ', s1 + 1);
  if (s1 < 0 || s2 < 0) {
    return;
  }

  String wheel = line.substring(s1 + 1, s2);
  bool invert = line.substring(s2 + 1).toInt() != 0;
  bool *target = invertForWheel(wheel);
  if (target == NULL) {
    Serial.println("BAD INV WHEEL");
    return;
  }

  *target = invert;
  stopAllMotors();
  Serial.print("INV ");
  Serial.print(wheel);
  Serial.print(" ");
  Serial.println(invert ? 1 : 0);
}

void parseMotorTestCommand(String line) {
  int s1 = line.indexOf(' ');
  int s2 = line.indexOf(' ', s1 + 1);
  int s3 = line.indexOf(' ', s2 + 1);
  if (s1 < 0 || s2 < 0 || s3 < 0) {
    return;
  }

  String wheel = line.substring(s1 + 1, s2);
  int pwm = constrain(line.substring(s2 + 1, s3).toInt(), -MAX_PWM, MAX_PWM);
  int durationMs = constrain(line.substring(s3 + 1).toInt(), 0, 1500);

  Serial.print("M ");
  Serial.print(wheel);
  Serial.print(" ");
  Serial.print(pwm);
  Serial.print(" ");
  Serial.println(durationMs);

  setWheel(wheel, pwm);
  delay(durationMs);
  stopAllMotors();
}

void driveDifferential(float linearX, float angularZ) {
  // Encoder-free open-loop turning needs more authority than the physical
  // wheelbase formula gives at low web-control angular speeds.
  float turnSpeed = angularZ * TURN_SPEED_GAIN;
  float leftSpeed = linearX - turnSpeed;
  float rightSpeed = linearX + turnSpeed;

  int leftPwm = applyMinimumDrivePwm(speedToPwm(leftSpeed));
  int rightPwm = applyMinimumDrivePwm(speedToPwm(rightSpeed));

  setMotor(LR_PWMA, LR_AIN1, LR_AIN2, leftPwm, LR_INVERT, LR_PWM_SCALE);
  setMotor(LF_PWMB, LF_BIN1, LF_BIN2, leftPwm, LF_INVERT, LF_PWM_SCALE);
  setMotor(RR_PWMA, RR_AIN1, RR_AIN2, rightPwm, RR_INVERT, RR_PWM_SCALE);
  setMotor(RF_PWMB, RF_BIN1, RF_BIN2, rightPwm, RF_INVERT, RF_PWM_SCALE);
}

int speedToPwm(float speed) {
  float limited = constrain(speed, -MAX_SPEED, MAX_SPEED);
  float normalized = limited / MAX_SPEED;
  return (int)(normalized * MAX_PWM);
}

int applyMinimumDrivePwm(int pwm) {
  if (pwm == 0) {
    return 0;
  }

  if (abs(pwm) < MIN_DRIVE_PWM) {
    return pwm > 0 ? MIN_DRIVE_PWM : -MIN_DRIVE_PWM;
  }

  return pwm;
}

void setMotor(int pwmPin, int in1Pin, int in2Pin, int pwmValue, bool invert, float pwmScale) {
  int pwm = constrain(pwmValue, -MAX_PWM, MAX_PWM);
  pwm = (int)(pwm * constrain(pwmScale, 0.0, 1.0));
  if (invert) {
    pwm = -pwm;
  }

  if (pwm > 0) {
    digitalWrite(in1Pin, HIGH);
    digitalWrite(in2Pin, LOW);
  } else if (pwm < 0) {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, HIGH);
  } else {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, LOW);
  }

  analogWrite(pwmPin, abs(pwm));
}

void setWheel(String wheel, int pwm) {
  if (wheel == "LR") {
    setMotor(LR_PWMA, LR_AIN1, LR_AIN2, pwm, LR_INVERT, LR_PWM_SCALE);
  } else if (wheel == "LF") {
    setMotor(LF_PWMB, LF_BIN1, LF_BIN2, pwm, LF_INVERT, LF_PWM_SCALE);
  } else if (wheel == "RR") {
    setMotor(RR_PWMA, RR_AIN1, RR_AIN2, pwm, RR_INVERT, RR_PWM_SCALE);
  } else if (wheel == "RF") {
    setMotor(RF_PWMB, RF_BIN1, RF_BIN2, pwm, RF_INVERT, RF_PWM_SCALE);
  }
}

float *scaleForWheel(String wheel) {
  if (wheel == "LR") {
    return &LR_PWM_SCALE;
  } else if (wheel == "LF") {
    return &LF_PWM_SCALE;
  } else if (wheel == "RR") {
    return &RR_PWM_SCALE;
  } else if (wheel == "RF") {
    return &RF_PWM_SCALE;
  }
  return NULL;
}

bool *invertForWheel(String wheel) {
  if (wheel == "LR") {
    return &LR_INVERT;
  } else if (wheel == "LF") {
    return &LF_INVERT;
  } else if (wheel == "RR") {
    return &RR_INVERT;
  } else if (wheel == "RF") {
    return &RF_INVERT;
  }
  return NULL;
}

void stopAllMotors() {
  setMotor(LR_PWMA, LR_AIN1, LR_AIN2, 0, LR_INVERT, LR_PWM_SCALE);
  setMotor(LF_PWMB, LF_BIN1, LF_BIN2, 0, LF_INVERT, LF_PWM_SCALE);
  setMotor(RR_PWMA, RR_AIN1, RR_AIN2, 0, RR_INVERT, RR_PWM_SCALE);
  setMotor(RF_PWMB, RF_BIN1, RF_BIN2, 0, RF_INVERT, RF_PWM_SCALE);

  if (!stoppedLogged) {
    Serial.println("STOPPED");
    stoppedLogged = true;
  }
}
