// force_left_side_test.ino
// Test TB6612 left side: A channel + B channel
// A channel = left rear motor
// B channel = left front motor
//
// SAFETY:
// - Lift the wheels before testing.
// - Do not test on the floor.
// - Keep battery ready to disconnect.
// - This code automatically runs both left motors.

const int LR_PWM = 5;   // PWMA
const int LR_IN1 = 7;   // AIN1
const int LR_IN2 = 8;   // AIN2

const int LF_PWM = 6;   // PWMB
const int LF_IN1 = 11;  // BIN1
const int LF_IN2 = 4;   // BIN2

const int TEST_PWM = 180;

void setup() {
  pinMode(LR_PWM, OUTPUT);
  pinMode(LR_IN1, OUTPUT);
  pinMode(LR_IN2, OUTPUT);

  pinMode(LF_PWM, OUTPUT);
  pinMode(LF_IN1, OUTPUT);
  pinMode(LF_IN2, OUTPUT);

  stopAll();
  delay(2000);

  // 1. Left rear motor forward
  setMotor(LR_PWM, LR_IN1, LR_IN2, TEST_PWM);
  delay(3000);
  stopAll();
  delay(1500);

  // 2. Left front motor forward
  setMotor(LF_PWM, LF_IN1, LF_IN2, TEST_PWM);
  delay(3000);
  stopAll();
  delay(1500);

  // 3. Both left motors forward
  setMotor(LR_PWM, LR_IN1, LR_IN2, TEST_PWM);
  setMotor(LF_PWM, LF_IN1, LF_IN2, TEST_PWM);
  delay(3000);
  stopAll();
  delay(1500);

  // 4. Both left motors reverse
  setMotor(LR_PWM, LR_IN1, LR_IN2, -TEST_PWM);
  setMotor(LF_PWM, LF_IN1, LF_IN2, -TEST_PWM);
  delay(3000);
  stopAll();
}

void loop() {
  stopAll();
}

void setMotor(int pwmPin, int in1, int in2, int pwmValue) {
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
}
