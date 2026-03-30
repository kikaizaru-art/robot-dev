// PCA9685 4-Servo Test — I2C via Port A, touch UI control
#include <M5CoreS3.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <WiFi.h>
#include <ArduinoOTA.h>
#include "wifi_config.h"

// PCA9685 on default I2C address 0x40
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40, Wire);

// MG90S pulse range (µs)
#define SERVO_MIN  500
#define SERVO_MAX  2400
#define SERVO_FREQ 50

// Channel assignment
#define CH_YAW   0  // 首ヨー
#define CH_TILT  1  // 首チルト
#define CH_ARM_L 2  // 左腕
#define CH_ARM_R 3  // 右腕

static M5Canvas canvas(&CoreS3.Display);
bool otaReady = false;
bool pca9685Found = false;

// Servo state
struct ServoState {
    const char* name;
    int channel;
    int angle;      // current
    int target;     // target
    uint16_t color;
};

ServoState servos[4] = {
    {"YAW",   CH_YAW,   90, 90, TFT_CYAN},
    {"TILT",  CH_TILT,  90, 90, TFT_GREEN},
    {"ARM_L", CH_ARM_L, 90, 90, TFT_ORANGE},
    {"ARM_R", CH_ARM_R, 90, 90, TFT_MAGENTA},
};

int selectedServo = 0;  // currently selected servo index
bool allSweep = false;
int sweepDir = 1;
unsigned long lastMove = 0;

// Convert angle (0-180) to microseconds and send via PCA9685
void setServoAngle(int channel, int angle) {
    angle = constrain(angle, 0, 180);
    int pulseUs = map(angle, 0, 180, SERVO_MIN, SERVO_MAX);
    pwm.writeMicroseconds(channel, pulseUs);
}

void drawUI() {
    canvas.fillSprite(TFT_BLACK);
    canvas.setTextDatum(top_left);

    // Title + I2C status
    canvas.setTextSize(2);
    canvas.setTextColor(TFT_WHITE);
    canvas.drawString("PCA9685 Test", 10, 4);
    canvas.setTextSize(1);
    canvas.setTextColor(pca9685Found ? TFT_GREEN : TFT_RED);
    canvas.drawString(pca9685Found ? "I2C:OK" : "I2C:NG", 250, 8);
    if (otaReady) {
        canvas.setTextColor(TFT_DARKGREY);
        canvas.drawString("OTA:OK", 290, 8);
    }

    // Servo list (4 buttons at top)
    int btnW = 75, btnH = 36, btnY = 28;
    for (int i = 0; i < 4; i++) {
        int btnX = 5 + i * (btnW + 4);
        uint16_t bg = (i == selectedServo) ? servos[i].color : TFT_DARKGREY;
        canvas.fillRoundRect(btnX, btnY, btnW, btnH, 6, bg);
        canvas.setTextSize(1);
        canvas.setTextColor(TFT_WHITE);
        canvas.setTextDatum(middle_center);
        canvas.drawString(servos[i].name, btnX + btnW/2, btnY + 10);
        char buf[8];
        snprintf(buf, sizeof(buf), "%d", servos[i].angle);
        canvas.setTextSize(2);
        canvas.drawString(buf, btnX + btnW/2, btnY + 26);
    }

    // Angle slider for selected servo
    int sliderY = 75;
    canvas.setTextDatum(top_left);
    canvas.setTextSize(2);
    canvas.setTextColor(servos[selectedServo].color);
    canvas.drawString(servos[selectedServo].name, 10, sliderY);

    // Slider bar
    int barY = sliderY + 24;
    int barX0 = 20, barX1 = 300;
    canvas.fillRoundRect(barX0, barY, barX1 - barX0, 16, 4, TFT_DARKGREY);
    int knobX = map(servos[selectedServo].angle, 0, 180, barX0, barX1);
    canvas.fillRoundRect(barX0, barY, knobX - barX0, 16, 4, servos[selectedServo].color);
    canvas.fillCircle(knobX, barY + 8, 12, TFT_WHITE);

    // Angle display
    canvas.setTextSize(4);
    canvas.setTextColor(TFT_WHITE);
    canvas.setTextDatum(middle_center);
    char angleBuf[8];
    snprintf(angleBuf, sizeof(angleBuf), "%3d", servos[selectedServo].angle);
    canvas.drawString(angleBuf, 160, 140);
    canvas.setTextSize(1);
    canvas.drawString("deg", 220, 140);

    // Bottom buttons: [0] [90] [180] [ALL SWEEP]
    int bbY = 185, bbH = 48;
    canvas.fillRoundRect(5,   bbY, 72, bbH, 8, TFT_BLUE);
    canvas.fillRoundRect(82,  bbY, 72, bbH, 8, TFT_BLUE);
    canvas.fillRoundRect(159, bbY, 72, bbH, 8, TFT_BLUE);
    canvas.fillRoundRect(236, bbY, 78, bbH, 8, allSweep ? TFT_RED : TFT_GREEN);

    canvas.setTextSize(2);
    canvas.setTextColor(TFT_WHITE);
    canvas.setTextDatum(middle_center);
    canvas.drawString("0",    41,  bbY + bbH/2);
    canvas.drawString("90",   118, bbY + bbH/2);
    canvas.drawString("180",  195, bbY + bbH/2);
    canvas.drawString(allSweep ? "STOP" : "SWEEP", 275, bbY + bbH/2);

    canvas.setTextDatum(top_left);
    canvas.pushSprite(0, 0);
}

void setup() {
    auto cfg = M5.config();
    CoreS3.begin(cfg);
    Serial.begin(115200);
    delay(500);
    Serial.println("\n=== PCA9685 4-Servo Test ===");

    canvas.createSprite(320, 240);

    // I2C on Port A: SDA=G2, SCL=G1
    Wire.begin(2, 1);
    Wire.setClock(400000);

    // Scan for PCA9685
    Wire.beginTransmission(0x40);
    pca9685Found = (Wire.endTransmission() == 0);
    Serial.printf("PCA9685 I2C scan: %s\n", pca9685Found ? "FOUND" : "NOT FOUND");

    if (pca9685Found) {
        pwm.begin();
        pwm.setOscillatorFrequency(25000000);
        pwm.setPWMFreq(SERVO_FREQ);
        delay(100);

        // Startup test: sweep CH0 to confirm signal output
        Serial.println("Startup servo test...");
        for (int ch = 0; ch < 4; ch++) {
            // 0 deg
            pwm.writeMicroseconds(ch, 500);
            delay(500);
            // 180 deg
            pwm.writeMicroseconds(ch, 2400);
            delay(500);
            // 90 deg
            pwm.writeMicroseconds(ch, 1450);
            delay(300);
            Serial.printf("  CH%d: sweep done\n", ch);
        }
        Serial.println("All servos set to 90 deg");
    }

    drawUI();

    // WiFi + OTA
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    ArduinoOTA.setHostname(OTA_HOSTNAME);
    Serial.println("WiFi connecting...");
}

void loop() {
    // OTA
    if (!otaReady && WiFi.status() == WL_CONNECTED) {
        otaReady = true;
        ArduinoOTA.begin();
        Serial.printf("OTA ready: %s\n", WiFi.localIP().toString().c_str());
        drawUI();
    }
    if (otaReady) ArduinoOTA.handle();
    CoreS3.update();
    unsigned long now = millis();
    bool needDraw = false;

    // Touch handling
    if (CoreS3.Touch.getCount()) {
        auto t = CoreS3.Touch.getDetail();
        if (t.wasPressed()) {
            int tx = t.x, ty = t.y;

            // Servo select buttons (y=28..64)
            if (ty >= 28 && ty < 64) {
                int idx = (tx - 5) / 79;
                if (idx >= 0 && idx < 4) {
                    selectedServo = idx;
                    allSweep = false;
                    needDraw = true;
                }
            }
            // Slider area (y=95..120)
            else if (ty >= 85 && ty <= 130) {
                int angle = map(constrain(tx, 20, 300), 20, 300, 0, 180);
                servos[selectedServo].target = angle;
                allSweep = false;
            }
            // Bottom buttons (y=185..233)
            else if (ty >= 185) {
                if (tx < 77) {
                    servos[selectedServo].target = 0; allSweep = false;
                } else if (tx < 154) {
                    servos[selectedServo].target = 90; allSweep = false;
                } else if (tx < 231) {
                    servos[selectedServo].target = 180; allSweep = false;
                } else {
                    allSweep = !allSweep;
                    if (allSweep) sweepDir = 1;
                    needDraw = true;
                }
            }
        }
    }

    // All sweep mode
    if (allSweep && pca9685Found && now - lastMove >= 20) {
        lastMove = now;
        for (int i = 0; i < 4; i++) {
            servos[i].angle += sweepDir * 2;
            if (servos[i].angle >= 180) { servos[i].angle = 180; }
            if (servos[i].angle <= 0)   { servos[i].angle = 0; }
            setServoAngle(servos[i].channel, servos[i].angle);
        }
        if (servos[0].angle >= 180) sweepDir = -1;
        if (servos[0].angle <= 0)   sweepDir = 1;
        needDraw = true;
    }

    // Smooth move to target (individual)
    if (!allSweep && pca9685Found && now - lastMove >= 15) {
        lastMove = now;
        for (int i = 0; i < 4; i++) {
            if (servos[i].angle != servos[i].target) {
                if (servos[i].angle < servos[i].target)
                    servos[i].angle = min(servos[i].angle + 3, servos[i].target);
                else
                    servos[i].angle = max(servos[i].angle - 3, servos[i].target);
                setServoAngle(servos[i].channel, servos[i].angle);
                needDraw = true;
            }
        }
    }

    if (needDraw) {
        drawUI();
        Serial.printf("[%s] YAW:%d TILT:%d L:%d R:%d %s\n",
            pca9685Found ? "OK" : "NG",
            servos[0].angle, servos[1].angle,
            servos[2].angle, servos[3].angle,
            allSweep ? "SWEEP" : "");
    }

    delay(10);
}
