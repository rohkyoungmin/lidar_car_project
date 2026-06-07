// all_wheel_diagnostic.ino
// Arduino Uno + two TB6612FNG + 4WD motor diagnostic
//
// SAFETY:
// - Lift all wheels before testing.
// - Do not test on the floor.
// - Keep battery ready to disconnect.
// - Use low PWM first.
// - If a wheel spins in the wrong forward direction, record it.

const int LR_PWM = 5;   // Left Rear  - TB6612 #1 PWMA
const int LR_IN1 = 7;   // Left Rear  - AIN1
const int LR_IN2 = 8;   // Left Rear  - AIN2

const int LF_PWM = 6;   // Left Front - TB6612 #1 PWMB
const int LF_IN1 = 11;  // Left Front - BIN1
const int LF_IN2 = 4;   // Left Front - BIN2

const int RR_PWM = 9;   // Right Rear - TB6612 #2 PWMA
const int RR_IN1 = 12;  // Right Rear - AIN1
const int RR_IN2 = A0;  // Right Rear - AIN2

const int RF_PWM = 10;  // Right Front - TB6612 #2 PWMB
const int RF_IN1 = 2;   // Right Front - BIN1
const int RF_IN2 = 3;   // Right Front - BIN2

const int MAX_PWM = 180;
const unsigned long CMD_TIMEOUT_MS = 1500;

unsigned long lastCmdTime = 0;

void setup() {
  Serial.begin(115200);

  pinMode(LR_PWM, OUTPUT);
  pinMode(LR_IN1, OUTPUT);
  pinMode(LR_IN2, OUTPUT);

  pinMode(LF_PWM, OUTPUT);
  pinMode(LF_IN1, OUTPUT);
  pinMode(LF_IN2, OUTPUT);

  pinMode(RR_PWM, OUTPUT);
  pinMode(RR_IN1, OUTPUT);
  pinMode(RR_IN2, OUTPUT);

  pinMode(RF_PWM, OUTPUT);
  pinMode(RF_IN1, OUTPUT);
  pinMode(RF_IN2, OUTPUT);

  stopAll();

  Serial.println("READY");
  Serial.println("Commands:");
  Serial.println("  M LR 100 1000");
  Serial.println("  M LF 100 1000");
  Serial.println("  M RR 100 1000");
  Serial.println("  M RF 100 1000");
  Serial.println("  SIDE L 100 1000");
  Serial.println("  SIDE R 100 1000");
  Serial.println("  ALL 100 1000");
  Serial.println("  STOP");

  lastCmdTime = millis();
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (line.length() > 0) {
      handleCommand(line);
      lastCmdTime = millis();
    }
  }

  if (millis() - lastCmdTime > CMD_TIMEOUT_MS) {
    stopAll();
  }
}

void handleCommand(String line) {
  if (line == "STOP") {
    stopAll();
    Serial.println("STOPPED");
    return;
  }

  if (line.startsWith("M ")) {
    handleSingleMotor(line);
    return;
  }

  if (line.startsWith("SIDE ")) {
    handleSide(line);
    return;
  }

  if (line.startsWith("ALL ")) {
    handleAll(line);
    return;
  }

  Serial.print("UNKNOWN COMMAND: ");
  Serial.println(line);
}

void handleSingleMotor(String line) {
  int s1 = line.indexOf(' ');
  int s2 = line.indexOf(' ', s1 + 1);
  int s3 = line.indexOf(' ', s2 + 1);

  if (s1 < 0 || s2 < 0 || s3 < 0) {
    Serial.println("BAD M COMMAND");
    return;
  }

  String wheel = line.substring(s1 + 1, s2);
  int pwm = line.substring(s2 + 1, s3).toInt();
  int durationMs = line.substring(s3 + 1).toInt();

  pwm = constrain(pwm, -MAX_PWM, MAX_PWM);
  durationMs = constrain(durationMs, 0, 3000);

  Serial.print("RUN WHEEL ");
  Serial.print(wheel);
  Serial.print(" pwm=");
  Serial.print(pwm);
  Serial.print(" duration=");
  Serial.println(durationMs);

  if (wheel == "LR") {
    setMotor(LR_PWM, LR_IN1, LR_IN2, pwm);
  } else if (wheel == "LF") {
    setMotor(LF_PWM, LF_IN1, LF_IN2, pwm);
  } else if (wheel == "RR") {
    setMotor(RR_PWM, RR_IN1, RR_IN2, pwm);
  } else if (wheel == "RF") {
    setMotor(RF_PWM, RF_IN1, RF_IN2, pwm);
  } else {
    Serial.println("UNKNOWN WHEEL");
    return;
  }

  delay(durationMs);
  stopAll();
  Serial.println("STOPPED");
}

void handleSide(String line) {
  int s1 = line.indexOf(' ');
  int s2 = line.indexOf(' ', s1 + 1);
  int s3 = line.indexOf(' ', s2 + 1);

  if (s1 < 0 || s2 < 0 || s3 < 0) {
    Serial.println("BAD SIDE COMMAND");
    return;
  }

  String side = line.substring(s1 + 1, s2);
  int pwm = line.substring(s2 + 1, s3).toInt();
  int durationMs = line.substring(s3 + 1).toInt();

  pwm = constrain(pwm, -MAX_PWM, MAX_PWM);
  durationMs = constrain(durationMs, 0, 3000);

  Serial.print("RUN SIDE ");
  Serial.print(side);
  Serial.print(" pwm=");
  Serial.print(pwm);
  Serial.print(" duration=");
  Serial.println(durationMs);

  if (side == "L") {
    setMotor(LR_PWM, LR_IN1, LR_IN2, pwm);
    setMotor(LF_PWM, LF_IN1, LF_IN2, pwm);
  } else if (side == "R") {
    setMotor(RR_PWM, RR_IN1, RR_IN2, pwm);
    setMotor(RF_PWM, RF_IN1, RF_IN2, pwm);
  } else {
    Serial.println("UNKNOWN SIDE");
    return;
  }

  delay(durationMs);
  stopAll();
  Serial.println("STOPPED");
}

void handleAll(String line) {
  int s1 = line.indexOf(' ');
  int s2 = line.indexOf(' ', s1 + 1);

  if (s1 < 0 || s2 < 0) {
    Serial.println("BAD ALL COMMAND");
    return;
  }

  int pwm = line.substring(s1 + 1, s2).toInt();
  int durationMs = line.substring(s2 + 1).toInt();

  pwm = constrain(pwm, -MAX_PWM, MAX_PWM);
  durationMs = constrain(durationMs, 0, 3000);

  Serial.print("RUN ALL pwm=");
  Serial.print(pwm);
  Serial.print(" duration=");
  Serial.println(durationMs);

  setMotor(LR_PWM, LR_IN1, LR_IN2, pwm);
  setMotor(LF_PWM, LF_IN1, LF_IN2, pwm);
  setMotor(RR_PWM, RR_IN1, RR_IN2, pwm);
  setMotor(RF_PWM, RF_IN1, RF_IN2, pwm);

  delay(durationMs);
  stopAll();
  Serial.println("STOPPED");
}

void setMotor(int pwmPin, int in1, int in2, int pwmValue) {
  pwmValue = constrain(pwmValue, -MAX_PWM, MAX_PWM);

  if (pwmValue > 0) {
    digitalWrite(in1, HIGH);
    digitalWrite(in2, LOW);
    analogWrite(pwmPin, pwmValue);
  } else if (pwmValue < 0) {
    digitalWrite(in1, LOW);
    digitalWrite(in2, HIGH);
    analogWrite(pwmPin, -pwmValue);
  } else {
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
    analogWrite(pwmPin, 0);
  }
}

void stopAll() {
  setMotor(LR_PWM, LR_IN1, LR_IN2, 0);
  setMotor(LF_PWM, LF_IN1, LF_IN2, 0);
  setMotor(RR_PWM, RR_IN1, RR_IN2, 0);
  setMotor(RF_PWM, RF_IN1, RF_IN2, 0);
}
