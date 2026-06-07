/*
  One-shot 4WD wheel spin test for Arduino Uno + two TB6612FNG drivers.

  SAFETY WARNING:
  - Lift all wheels off the ground before uploading/running this sketch.
  - Do not run this with the car sitting on the floor.
  - Keep battery power easy to disconnect.
  - This sketch starts its test automatically after upload/reset, then stops.

  Test order:
    1. Left rear only
    2. Left front only
    3. Right rear only
    4. Right front only
    5. Left side
    6. Right side
    7. All wheels
*/

const int LR_PWM = 5;
const int LR_IN1 = 7;
const int LR_IN2 = 8;

const int LF_PWM = 6;
const int LF_IN1 = 11;
const int LF_IN2 = 4;

const int RR_PWM = 9;
const int RR_IN1 = 12;
const int RR_IN2 = A0;

const int RF_PWM = 10;
const int RF_IN1 = 2;
const int RF_IN2 = 3;

const int TEST_PWM = 110;
const int STEP_MS = 900;
const int PAUSE_MS = 600;

bool testDone = false;

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
  Serial.println("READY: lift wheels before this test runs");
  delay(2500);
}

void loop() {
  if (testDone) {
    stopAll();
    return;
  }

  runTest();
  testDone = true;
  stopAll();
  Serial.println("DONE: all motors stopped");
}

void runTest() {
  runOne("LR only", LR_PWM, LR_IN1, LR_IN2, TEST_PWM);
  runOne("LF only", LF_PWM, LF_IN1, LF_IN2, TEST_PWM);
  runOne("RR only", RR_PWM, RR_IN1, RR_IN2, TEST_PWM);
  runOne("RF only", RF_PWM, RF_IN1, RF_IN2, TEST_PWM);

  Serial.println("TEST: left side");
  setMotor(LR_PWM, LR_IN1, LR_IN2, TEST_PWM);
  setMotor(LF_PWM, LF_IN1, LF_IN2, TEST_PWM);
  delay(STEP_MS);
  stopAndPause();

  Serial.println("TEST: right side");
  setMotor(RR_PWM, RR_IN1, RR_IN2, TEST_PWM);
  setMotor(RF_PWM, RF_IN1, RF_IN2, TEST_PWM);
  delay(STEP_MS);
  stopAndPause();

  Serial.println("TEST: all wheels");
  setMotor(LR_PWM, LR_IN1, LR_IN2, TEST_PWM);
  setMotor(LF_PWM, LF_IN1, LF_IN2, TEST_PWM);
  setMotor(RR_PWM, RR_IN1, RR_IN2, TEST_PWM);
  setMotor(RF_PWM, RF_IN1, RF_IN2, TEST_PWM);
  delay(STEP_MS);
  stopAndPause();
}

void runOne(const char *label, int pwmPin, int in1Pin, int in2Pin, int pwm) {
  Serial.print("TEST: ");
  Serial.println(label);
  setMotor(pwmPin, in1Pin, in2Pin, pwm);
  delay(STEP_MS);
  stopAndPause();
}

void stopAndPause() {
  stopAll();
  Serial.println("STOPPED");
  delay(PAUSE_MS);
}

void setMotor(int pwmPin, int in1Pin, int in2Pin, int pwmValue) {
  if (pwmValue > 0) {
    digitalWrite(in1Pin, HIGH);
    digitalWrite(in2Pin, LOW);
    analogWrite(pwmPin, pwmValue);
  } else if (pwmValue < 0) {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, HIGH);
    analogWrite(pwmPin, -pwmValue);
  } else {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, LOW);
    analogWrite(pwmPin, 0);
  }
}

void stopAll() {
  setMotor(LR_PWM, LR_IN1, LR_IN2, 0);
  setMotor(LF_PWM, LF_IN1, LF_IN2, 0);
  setMotor(RR_PWM, RR_IN1, RR_IN2, 0);
  setMotor(RF_PWM, RF_IN1, RF_IN2, 0);
}
