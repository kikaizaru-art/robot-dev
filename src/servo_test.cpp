// Servo Debug Test — Port B pin diagnosis
#include <M5CoreS3.h>
#include <ESP32Servo.h>
#include <WiFi.h>
#include <ArduinoOTA.h>
#include <ESPmDNS.h>
#include "wifi_config.h"

Servo servo8;
Servo servo9;

static M5Canvas canvas(&CoreS3.Display);
bool attached8 = false;
bool attached9 = false;

int currentAngle = 90;
int targetAngle = 90;
int sweepDir = 1;
bool sweeping = false;
unsigned long bootTime = 0;

void servoWrite(int angle) {
    angle = constrain(angle, 0, 180);
    if (attached8) servo8.write(angle);
    if (attached9) servo9.write(angle);
}

void drawUI() {
    canvas.fillSprite(TFT_BLACK);
    canvas.setTextDatum(top_left);
    canvas.setTextSize(2);

    // Status
    canvas.setTextColor(TFT_WHITE);
    canvas.drawString("Servo Debug", 20, 5);
    canvas.setTextColor(attached8 ? TFT_GREEN : TFT_RED);
    canvas.drawString(attached8 ? "G8:OK" : "G8:FAIL", 20, 28);
    canvas.setTextColor(attached9 ? TFT_GREEN : TFT_RED);
    canvas.drawString(attached9 ? "G9:OK" : "G9:FAIL", 150, 28);

    // Angle
    canvas.setTextSize(5);
    canvas.setTextColor(TFT_CYAN);
    char buf[8];
    snprintf(buf, sizeof(buf), "%3d", currentAngle);
    canvas.drawString(buf, 80, 55);

    // Bar
    int barX = map(currentAngle, 0, 180, 20, 300);
    canvas.fillRoundRect(20, 120, 280, 20, 4, TFT_DARKGREY);
    canvas.fillRoundRect(20, 120, max(1, barX - 20), 20, 4, TFT_GREEN);
    canvas.fillCircle(barX, 130, 10, TFT_WHITE);

    // Buttons
    canvas.fillRoundRect(10, 170, 90, 55, 8, TFT_BLUE);
    canvas.fillRoundRect(115, 170, 90, 55, 8, TFT_ORANGE);
    canvas.fillRoundRect(220, 170, 90, 55, 8, sweeping ? TFT_RED : TFT_GREEN);
    canvas.setTextSize(2);
    canvas.setTextColor(TFT_WHITE);
    canvas.setTextDatum(middle_center);
    canvas.drawString("0", 55, 197);
    canvas.drawString("90", 160, 197);
    canvas.drawString(sweeping ? "STOP" : "SWEEP", 265, 197);
    canvas.setTextDatum(top_left);

    canvas.pushSprite(0, 0);
}

void setup() {
    auto cfg = M5.config();
    CoreS3.begin(cfg);
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n\n=== SERVO DEBUG TEST ===");

    canvas.createSprite(320, 240);

    // First: test pins as digital output
    Serial.println("--- Digital pin test ---");
    pinMode(8, OUTPUT);
    digitalWrite(8, HIGH);
    delay(10);
    Serial.printf("G8 digital write: done\n");
    pinMode(9, OUTPUT);
    digitalWrite(9, HIGH);
    delay(10);
    Serial.printf("G9 digital write: done\n");
    // Reset pins
    pinMode(8, INPUT);
    pinMode(9, INPUT);

    // Servo attach
    Serial.println("--- Servo attach ---");
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    servo8.setPeriodHertz(50);
    servo9.setPeriodHertz(50);
    attached8 = servo8.attach(8, 500, 2400);
    attached9 = servo9.attach(9, 500, 2400);

    Serial.printf("G8 attach: %s (channel=%d)\n", attached8 ? "OK" : "FAIL", servo8.attached() ? servo8.readMicroseconds() : -1);
    Serial.printf("G9 attach: %s (channel=%d)\n", attached9 ? "OK" : "FAIL", servo9.attached() ? servo9.readMicroseconds() : -1);

    servoWrite(90);
    Serial.println("Set to 90 deg");

    drawUI();

    WiFi.begin(WIFI_SSID, WIFI_PASS);
    ArduinoOTA.setHostname(OTA_HOSTNAME);
    bootTime = millis();
}

bool otaReady = false;
unsigned long lastSweep = 0;
int prevAngle = -1;
unsigned long lastDiag = 0;

void loop() {
    if (!otaReady && WiFi.status() == WL_CONNECTED) {
        otaReady = true;
        ArduinoOTA.begin();
        Serial.printf("OTA ready: %s\n", WiFi.localIP().toString().c_str());
    }
    if (otaReady) ArduinoOTA.handle();
    CoreS3.update();
    unsigned long now = millis();

    // Print diagnostics every 3 seconds for first 15 seconds
    if (now - bootTime < 15000 && now - lastDiag >= 3000) {
        lastDiag = now;
        Serial.printf("[DIAG] G8:%s G9:%s angle=%d sweep=%d\n",
            attached8 ? "OK" : "FAIL", attached9 ? "OK" : "FAIL",
            currentAngle, sweeping);
    }

    // Touch
    if (CoreS3.Touch.getCount()) {
        auto t = CoreS3.Touch.getDetail();
        if (t.wasPressed()) {
            int tx = t.x, ty = t.y;
            if (ty >= 170) {
                if (tx < 110) { targetAngle = 0; sweeping = false; }
                else if (tx < 210) { targetAngle = 90; sweeping = false; }
                else { sweeping = !sweeping; if (sweeping) sweepDir = 1; }
            } else if (ty >= 105 && ty <= 150) {
                targetAngle = map(constrain(tx, 20, 300), 20, 300, 0, 180);
                sweeping = false;
            }
        }
    }

    // Sweep
    if (sweeping && now - lastSweep >= 20) {
        lastSweep = now;
        currentAngle += sweepDir * 2;
        if (currentAngle >= 180) { currentAngle = 180; sweepDir = -1; }
        if (currentAngle <= 0)   { currentAngle = 0;   sweepDir = 1; }
        servoWrite(currentAngle);
    }

    // Smooth move
    if (!sweeping && currentAngle != targetAngle && now - lastSweep >= 15) {
        lastSweep = now;
        if (currentAngle < targetAngle) currentAngle += 2;
        else currentAngle -= 2;
        if (abs(currentAngle - targetAngle) < 3) currentAngle = targetAngle;
        servoWrite(currentAngle);
    }

    if (currentAngle != prevAngle) {
        prevAngle = currentAngle;
        drawUI();
        Serial.printf("Angle: %d  %s\n", currentAngle, sweeping ? "SWEEP" : "MANUAL");
    }

    delay(10);
}
