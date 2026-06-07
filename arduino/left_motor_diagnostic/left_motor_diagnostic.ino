// left_motor_diagnostic.ino
// Test only TB6612 #1 left motors.
//
// SAFETY:
// - Lift the wheels before testing.
// - Do not test on the floor.
// - Start with low PWM.
// - Send STOP if anything behaves unexpectedly.

const int LEFT_REAR_PWM = 5;   // TB6612 #1 PWMA
const int LEFT_REAR_IN1 = 7;   // TB6612 #1 AIN1
const int LEFT_REAR_IN2 = 8;   // TB6612 #1 AIN2

const int LEFT_FRONT_PWM = 6;  // TB6612 #1 PWMB
const int LEFT_FRONT_IN1 = 11; // TB6612 #1 BIN1
const int LEFT_FRONT_IN2 = 4;  // TB6612 #1 BIN2

const int MAX_PWM = 120;

unsigned long lastCmdTime = 0;
const unsigned long CMD_TIMEOUT_MS = 1000;

void setup() {
  Serial.begin(115200);

  pinMode(LEFT_REAR_PWM, OUTPUT);
  pinMode(LEFT_REAR_IN1, OUTPUT);
  pinMode(LEFT_REAR_IN2, OUTPUT);

  pinMode(LEFT_FRONT_PWM, OUTPUT);
  pinMode(LEFT_FRONT_IN1, OUTPUT);
  pinMode(LEFT_FRONT_IN2, OUTPUT);

  stopAllMotors();

  Serial.println("READY");
  Serial.println("Commands:");
  Serial.println("M LR 80 500");
  Serial.println("M LF 80 500");
  Serial.println("STOP");

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
    stopAllMotors();
  }
}

void handleCommand(String line) {
  if (line == "STOP") {
    stopAllMotors();
    Serial.println("STOPPED");
    return;
  }

  if (!line.startsWith("M ")) {
    Serial.println("UNKNOWN COMMAND");
    return;
  }

  int s1 = line.indexOf(' ');
  int s2 = line.indexOf(' ', s1 + 1);
  int s3 = line.indexOf(' ', s2 + 1);

  if (s1 < 0 || s2 < 0 || s3 < 0) {
    Serial.println("BAD COMMAND");
    return;
  }

  String wheel = line.substring(s1 + 1, s2);
  int pwm = line.substring(s2 + 1, s3).toInt();
  int durationMs = line.substring(s3 + 1).toInt();

  pwm = constrain(pwm, -MAX_PWM, MAX_PWM);
  durationMs = constrain(durationMs, 0, 2000);

  Serial.print("RUN ");
  Serial.print(wheel);
  Serial.print(" pwm=");
  Serial.print(pwm);
  Serial.print(" duration=");
  Serial.println(durationMs);

  if (wheel == "LR") {
    setMotor(LEFT_REAR_PWM, LEFT_REAR_IN1, LEFT_REAR_IN2, pwm);
  } else if (wheel == "LF") {
    setMotor(LEFT_FRONT_PWM, LEFT_FRONT_IN1, LEFT_FRONT_IN2, pwm);
  } else {
    Serial.println("UNKNOWN WHEEL");
    return;
  }

  delay(durationMs);
  stopAllMotors();
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

void stopAllMotors() {
  setMotor(LEFT_REAR_PWM, LEFT_REAR_IN1, LEFT_REAR_IN2, 0);
  setMotor(LEFT_FRONT_PWM, LEFT_FRONT_IN1, LEFT_FRONT_IN2, 0);
}
