#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <ESP32Servo.h>

namespace {

constexpr uint8_t BUTTON_PIN = 18;
constexpr uint8_t TRIG_PIN = 5;
constexpr uint8_t ECHO_PIN = 17;
constexpr uint8_t SERVO_PIN = 19;
constexpr uint8_t LED_PIN = 23;
constexpr uint8_t BUZZER_PIN = 16;

constexpr uint8_t PIXEL_COUNT = 8;
constexpr uint8_t BUZZER_CHANNEL = 0;

constexpr float ALERT_DISTANCE_CM = 18.0f;
constexpr float RECOVER_DISTANCE_CM = 24.0f;

constexpr unsigned long DIST_SAMPLE_MS = 100;
constexpr unsigned long TELEMETRY_MS = 500;

enum class RobotState {
  Idle,
  Wake,
  Track,
  Alert,
  Cooldown
};

volatile bool buttonInterruptFired = false;

Servo headServo;
Adafruit_NeoPixel pixels(PIXEL_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

RobotState state = RobotState::Idle;
unsigned long stateEnteredAt = 0;
unsigned long lastDistanceSampleAt = 0;
unsigned long lastTelemetryAt = 0;
unsigned long lastAlertBeepAt = 0;

float filteredDistanceCm = 200.0f;
bool obstacleDetected = false;
bool buttonEventPending = false;
String pendingHostAction = "IDLE";
bool actionConsumed = false;

void IRAM_ATTR onButtonPressed() {
  buttonInterruptFired = true;
}

const char *stateName(RobotState value) {
  switch (value) {
    case RobotState::Idle:
      return "IDLE";
    case RobotState::Wake:
      return "WAKE";
    case RobotState::Track:
      return "TRACK";
    case RobotState::Alert:
      return "ALERT";
    case RobotState::Cooldown:
      return "COOLDOWN";
  }
  return "UNKNOWN";
}

void setLed(uint8_t r, uint8_t g, uint8_t b) {
  for (uint8_t i = 0; i < PIXEL_COUNT; ++i) {
    pixels.setPixelColor(i, pixels.Color(r, g, b));
  }
  pixels.show();
}

void beepTone(uint16_t freq, uint16_t durationMs) {
  ledcWriteTone(BUZZER_CHANNEL, freq);
  delay(durationMs);
  ledcWriteTone(BUZZER_CHANNEL, 0);
}

void publishLine(const String &message) {
  Serial.println(message);
}

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long durationUs = pulseIn(ECHO_PIN, HIGH, 25000UL);
  if (durationUs == 0) {
    return filteredDistanceCm;
  }

  return static_cast<float>(durationUs) * 0.0343f * 0.5f;
}

void centerHead() {
  headServo.write(90);
}

void lookAlert() {
  headServo.write(145);
}

void doGreetingMotion() {
  headServo.write(70);
  delay(180);
  headServo.write(115);
  delay(180);
  centerHead();
}

void doThinkingMotion() {
  headServo.write(80);
  delay(150);
  headServo.write(100);
  delay(150);
  headServo.write(90);
}

void enterState(RobotState nextState) {
  state = nextState;
  stateEnteredAt = millis();
  actionConsumed = false;
  publishLine(String("STATE:") + stateName(state));
}

void refreshObstacleFlag() {
  if (!obstacleDetected && filteredDistanceCm < ALERT_DISTANCE_CM) {
    obstacleDetected = true;
  } else if (obstacleDetected && filteredDistanceCm > RECOVER_DISTANCE_CM) {
    obstacleDetected = false;
  }
}

void sampleDistanceIfNeeded() {
  if (millis() - lastDistanceSampleAt < DIST_SAMPLE_MS) {
    return;
  }

  lastDistanceSampleAt = millis();
  float rawCm = readDistanceCm();
  filteredDistanceCm = 0.65f * filteredDistanceCm + 0.35f * rawCm;
  refreshObstacleFlag();
}

void publishTelemetryIfNeeded() {
  if (millis() - lastTelemetryAt < TELEMETRY_MS) {
    return;
  }

  lastTelemetryAt = millis();
  publishLine(String("DIST:") + String(filteredDistanceCm, 1));
}

void handleHostCommand(const String &line) {
  if (!line.startsWith("ACT:")) {
    return;
  }

  pendingHostAction = line.substring(4);
  actionConsumed = false;
  publishLine(String("ACK:") + pendingHostAction);
}

void pollSerial() {
  while (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) {
      continue;
    }
    handleHostCommand(line);
  }
}

void processButtonInterrupt() {
  if (!buttonInterruptFired) {
    return;
  }

  noInterrupts();
  buttonInterruptFired = false;
  interrupts();

  buttonEventPending = true;
}

void handleIdle() {
  setLed(0, 0, 24);
  centerHead();

  if (buttonEventPending) {
    buttonEventPending = false;
    pendingHostAction = "THINK";
    publishLine("EVENT:BUTTON");
    beepTone(1200, 60);
    enterState(RobotState::Wake);
    return;
  }

  if (obstacleDetected) {
    enterState(RobotState::Alert);
  }
}

void handleWake() {
  setLed(0, 24, 0);

  if (obstacleDetected) {
    enterState(RobotState::Alert);
    return;
  }

  if (pendingHostAction != "THINK" || millis() - stateEnteredAt > 2500) {
    enterState(RobotState::Track);
  }
}

void handleTrack() {
  setLed(18, 18, 18);

  if (obstacleDetected || pendingHostAction == "RETREAT" || pendingHostAction == "ALERT") {
    enterState(RobotState::Alert);
    return;
  }

  if (!actionConsumed) {
    if (pendingHostAction == "GREET") {
      doGreetingMotion();
      beepTone(1400, 80);
    } else if (pendingHostAction == "THINK") {
      doThinkingMotion();
    } else if (pendingHostAction == "IDLE") {
      centerHead();
    }
    actionConsumed = true;
  }

  if (millis() - stateEnteredAt > 1800) {
    enterState(RobotState::Cooldown);
  }
}

void handleAlert() {
  setLed(28, 0, 0);
  lookAlert();

  if (millis() - lastAlertBeepAt > 700) {
    lastAlertBeepAt = millis();
    beepTone(900, 70);
  }

  if (!obstacleDetected && millis() - stateEnteredAt > 1200) {
    enterState(RobotState::Cooldown);
  }
}

void handleCooldown() {
  setLed(28, 20, 0);
  centerHead();

  if (millis() - stateEnteredAt > 1500) {
    pendingHostAction = "IDLE";
    enterState(RobotState::Idle);
  }
}

void updateStateMachine() {
  switch (state) {
    case RobotState::Idle:
      handleIdle();
      break;
    case RobotState::Wake:
      handleWake();
      break;
    case RobotState::Track:
      handleTrack();
      break;
    case RobotState::Alert:
      handleAlert();
      break;
    case RobotState::Cooldown:
      handleCooldown();
      break;
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  ledcSetup(BUZZER_CHANNEL, 2000, 8);
  ledcAttachPin(BUZZER_PIN, BUZZER_CHANNEL);

  pixels.begin();
  pixels.clear();
  pixels.show();

  headServo.attach(SERVO_PIN, 500, 2400);
  centerHead();

  attachInterrupt(digitalPinToInterrupt(BUTTON_PIN), onButtonPressed, FALLING);

  publishLine("BOOT:MINIPAL");
  enterState(RobotState::Idle);
}

void loop() {
  processButtonInterrupt();
  pollSerial();
  sampleDistanceIfNeeded();
  publishTelemetryIfNeeded();
  updateStateMachine();
}
