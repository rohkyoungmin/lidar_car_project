// force_lr_test.ino
// Force-test TB6612 #1 A channel = left rear motor.
// SAFETY: Lift wheels before powering the motor.

const int LR_PWM = 5;   // PWMA
const int LR_IN1 = 7;   // AIN1
const int LR_IN2 = 8;   // AIN2

void setup() {
  pinMode(LR_PWM, OUTPUT);
  pinMode(LR_IN1, OUTPUT);
  pinMode(LR_IN2, OUTPUT);

  stopMotor();
  delay(2000);

  // Forward direction test
  digitalWrite(LR_IN1, HIGH);
  digitalWrite(LR_IN2, LOW);
  analogWrite(LR_PWM, 200);
  delay(3000);

  stopMotor();
  delay(2000);

  // Reverse direction test
  digitalWrite(LR_IN1, LOW);
  digitalWrite(LR_IN2, HIGH);
  analogWrite(LR_PWM, 200);
  delay(3000);

  stopMotor();
}

void loop() {
  stopMotor();
}

void stopMotor() {
  digitalWrite(LR_IN1, LOW);
  digitalWrite(LR_IN2, LOW);
  analogWrite(LR_PWM, 0);
}
