#include <M5CoreS3.h>
#include <Wire.h>
#include <WiFi.h>
#include <ArduinoOTA.h>
#include <ESPmDNS.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>

AsyncWebServer webServer(80);
AsyncWebSocket wsLog("/log");

// Log to both Serial and WebSocket clients
template<typename... Args>
void LOG(const char* fmt, Args... args) {
    Serial.printf(fmt, args...);
    char buf[256];
    snprintf(buf, sizeof(buf), fmt, args...);
    wsLog.textAll(buf);
}

static const char LOG_PAGE[] PROGMEM = R"rawlit(<!DOCTYPE html><html><head>
<meta charset="utf-8"><title>CoreS3 Log</title>
<style>body{background:#111;color:#0f0;font-family:monospace;font-size:13px;margin:0;padding:8px}
#log{white-space:pre-wrap;word-break:break-all}</style></head><body>
<div id="log"></div><script>
var ws=new WebSocket('ws://'+location.host+'/log');
var el=document.getElementById('log');
ws.onmessage=function(e){el.textContent+=e.data;window.scrollTo(0,document.body.scrollHeight);};
</script></body></html>)rawlit";
#include "face.h"
#include "camera_detect.h"
#include "wifi_config.h"

#ifdef ENABLE_VOICE_CHAT
#include "voice_chat.h"
VoiceChat voiceChat;
#endif

Face face;
CameraDetect camDetect;

// --- IMU (tilt detection) ---
float imuTilt = 0;        // 0=horizontal, 90=vertical, 180=upside down
float imuSmoothed = 0;
static const float IMU_ALPHA = 0.15f;  // smoothing

// --- Sound effects (simple single tone) ---
unsigned long micMuteUntil = 0;
unsigned long soundCooldown = 0;
static const unsigned long SOUND_COOLDOWN_MS = 2000;  // min 2s between sounds

// Pre-computed short beep buffers (avoids blocking tone generation)
static const int BEEP_SAMPLES = 800;  // 50ms at 16kHz
int16_t beepBuf[BEEP_SAMPLES];

void generateBeep(float freq, int samples, int16_t* buf) {
    for (int i = 0; i < samples; i++) {
        float t = (float)i / 16000.0f;
        float env = 1.0f - (float)i / samples;  // fade out
        buf[i] = (int16_t)(sinf(2.0f * M_PI * freq * t) * 8000 * env);
    }
}

void playSoundForExpression(Expression expr) {
    unsigned long now = millis();
    if (!CoreS3.Speaker.isEnabled()) return;
    if (now < soundCooldown) return;

    float freq;
    int samples;
    switch (expr) {
        case Expression::HAPPY:    freq = 1500; samples = 640;  break;  // 40ms
        case Expression::SAD:      freq = 500;  samples = 800;  break;  // 50ms
        case Expression::SURPRISED:freq = 2200; samples = 480;  break;  // 30ms
        case Expression::LOVE:     freq = 1200; samples = 640;  break;  // 40ms
        default: return;
    }

    generateBeep(freq, samples, beepBuf);
    CoreS3.Speaker.setVolume(50);
    CoreS3.Speaker.playRaw(beepBuf, samples, 16000, false, 1, 0);

    soundCooldown = now + SOUND_COOLDOWN_MS;
    micMuteUntil = now + 500;
}

// --- Microphone ---
static const int MIC_SAMPLES = 160;
int16_t micBuf[MIC_SAMPLES];
float micAvgLevel = 500;
bool micReady = false;
static const float MIC_SPIKE_RATIO = 3.0f;
static const float MIC_MIN_PEAK = 3000.0f;

// Touch
unsigned long lastTouchTime = 0;
bool touchHeld = false;
static const unsigned long LONG_PRESS_MS = 600;

// Detection timing
unsigned long lastDetectTime = 0;
static const unsigned long DETECT_INTERVAL_MS = 200;

// --- Smoothing: moving average over N frames ---
static const int AVG_FRAMES = 5;
float areaHistory[AVG_FRAMES] = {};
float motionHistory[AVG_FRAMES] = {};
float skinHistory[AVG_FRAMES] = {};
bool faceHistory[AVG_FRAMES] = {};
int historyIdx = 0;
int historyCount = 0;

struct SmoothedResult {
    float area;
    float motion;
    float skin;
    float faceRate;  // fraction of recent frames with face detected
};

SmoothedResult getSmoothed() {
    SmoothedResult s = {};
    int n = min(historyCount, AVG_FRAMES);
    if (n == 0) return s;
    for (int i = 0; i < n; i++) {
        s.area += areaHistory[i];
        s.motion += motionHistory[i];
        s.skin += skinHistory[i];
        s.faceRate += faceHistory[i] ? 1.0f : 0.0f;
    }
    s.area /= n;
    s.motion /= n;
    s.skin /= n;
    s.faceRate /= n;
    return s;
}

void pushHistory(const DetectResult &r) {
    areaHistory[historyIdx] = r.areaRatio;
    motionHistory[historyIdx] = r.motionLevel;
    skinHistory[historyIdx] = r.skinRatio;
    faceHistory[historyIdx] = r.faceDetected;
    historyIdx = (historyIdx + 1) % AVG_FRAMES;
    if (historyCount < AVG_FRAMES) historyCount++;
}

// Presence levels
enum class Presence : uint8_t {
    NONE = 0,
    MOTION_ONLY = 1,
    FACE_FAR = 2,
    FACE_MID = 3,
    CLOSE = 4,
};

Presence currentPresence = Presence::NONE;

#include "servo_ctrl.h"
ServoCtrl servoCtrl;
unsigned long lastPresenceTime = 0;

// Expression transition: require stable state for N ms before switching
static const unsigned long EXPR_SETTLE_MS = 600;  // hold new state 0.6s before switching
Expression targetExpression = Expression::NORMAL;
Expression currentExpression = Expression::NORMAL;
unsigned long targetSince = 0;

static const unsigned long SURPRISED_DURATION_MS = 800;
static const unsigned long SAD_DURATION_MS = 3000;
static const unsigned long SLEEPY_DELAY_MS = 5000;
unsigned long surprisedUntil = 0;
bool wasPresent = false;
bool cameraActive = false;

int8_t faceXToGaze(int faceX) {
    // Wider range for more visible eye movement
    return (int8_t)constrain(-(faceX - 160) / 8, -12, 12);
}
int8_t faceYToGaze(int faceY) {
    return (int8_t)constrain((faceY - 120) / 12, -6, 6);
}

Presence evaluatePresence(const SmoothedResult &s) {
    // Face visible in most recent frames
    bool faceVisible = s.faceRate >= 0.4f;

    if (faceVisible) {
        if (s.area > 0.30f) return Presence::CLOSE;
        if (s.area > 0.20f) return Presence::FACE_MID;
        return Presence::FACE_FAR;
    }

    // No face — use motion
    if (s.motion >= 0.45f) return Presence::CLOSE;
    if (s.motion >= 0.30f) return Presence::MOTION_ONLY;

    return Presence::NONE;
}

Expression presenceToExpression(Presence p, unsigned long now) {
    switch (p) {
        case Presence::CLOSE:
            return Expression::LOVE;
        case Presence::FACE_MID:
        case Presence::MOTION_ONLY:
            return Expression::HAPPY;
        case Presence::FACE_FAR:
            return Expression::NORMAL;
        case Presence::NONE: {
            if (lastPresenceTime == 0) return Expression::NORMAL;
            unsigned long elapsed = now - lastPresenceTime;
            if (elapsed < SAD_DURATION_MS) return Expression::SAD;
            if (elapsed < SLEEPY_DELAY_MS) return Expression::SAD;
            return Expression::SLEEPY;
        }
    }
    return Expression::NORMAL;
}

void setup() {
    auto cfg = M5.config();
    cfg.internal_mic = true;
#ifdef ENABLE_VOICE_CHAT
    cfg.internal_spk = true;   // required for voice chat audio playback
#endif
    CoreS3.begin(cfg);
    Serial.begin(115200);
    delay(1000);
    Serial.println("--- CoreS3 Robot booting ---");

    // Test: fill screen green to prove display works
    CoreS3.Display.fillScreen(TFT_GREEN);
    Serial.println("Display test: GREEN");
    delay(500);

    Serial.println("Starting face...");
    face.begin();
    face.setExpression(Expression::NORMAL);
    Serial.println("Face OK");

    Serial.println("Starting camera...");
    cameraActive = camDetect.begin();
    Serial.printf("Camera: %s\n", cameraActive ? "ready" : "FAILED");

    // PCA9685 servo driver (I2C on Port A: SDA=G2, SCL=G1)
    Wire.begin(2, 1);
    Wire.setClock(400000);
    bool servoOk = servoCtrl.begin();
    Serial.printf("Servo: %s\n", servoOk ? "PCA9685 ready" : "NOT FOUND");

    // Mic should already be initialized via cfg.internal_mic
    micReady = CoreS3.Mic.isEnabled();
    Serial.printf("Mic: %s\n", micReady ? "ready" : "not available");

    // IMU
    if (CoreS3.Imu.isEnabled()) {
        Serial.println("IMU: ready");
    } else {
        Serial.println("IMU: not available");
    }

#ifdef ENABLE_VOICE_CHAT
    bool vcOk = voiceChat.begin();
    Serial.printf("VoiceChat: %s\n", vcOk ? "ready" : "disabled");
#endif

    // --- WiFi (non-blocking) ---
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    ArduinoOTA.setHostname(OTA_HOSTNAME);
    Serial.printf("WiFi connecting to %s...\n", WIFI_SSID);

    Serial.println("Setup complete");
}

bool otaReady = false;

const char* exprName(Expression e) {
    switch(e) {
        case Expression::NORMAL:   return "NORMAL";
        case Expression::HAPPY:    return "HAPPY";
        case Expression::SAD:      return "SAD";
        case Expression::SURPRISED:return "SURPRISED";
        case Expression::SLEEPY:   return "SLEEPY";
        case Expression::LOVE:     return "LOVE";
        default:                   return "?";
    }
}

const char* presenceName(Presence p) {
    switch(p) {
        case Presence::NONE:        return "NONE";
        case Presence::MOTION_ONLY: return "MOTION";
        case Presence::FACE_FAR:    return "FAR";
        case Presence::FACE_MID:    return "MID";
        case Presence::CLOSE:       return "CLOSE";
        default:                    return "?";
    }
}

void loop() {
    if (!otaReady && WiFi.status() == WL_CONNECTED) {
        otaReady = true;
        MDNS.begin(OTA_HOSTNAME);
        ArduinoOTA.begin();
        webServer.on("/", HTTP_GET, [](AsyncWebServerRequest *r){
            r->send_P(200, "text/html", LOG_PAGE);
        });
        webServer.addHandler(&wsLog);
        webServer.begin();
        Serial.printf("WiFi OK: %s | OTA+WebLog ready -> http://cores3-robot.local\n", WiFi.localIP().toString().c_str());
    }
    if (otaReady) ArduinoOTA.handle();
    CoreS3.update();
    unsigned long now = millis();

    // --- Touch ---
    if (CoreS3.Touch.getCount()) {
        auto touch = CoreS3.Touch.getDetail();
        if (touch.wasPressed()) { lastTouchTime = now; touchHeld = true; }
        if (touch.wasReleased() && touchHeld) {
            touchHeld = false;
#ifdef ENABLE_VOICE_CHAT
            // Someone nearby: touch starts voice chat
            if (currentPresence > Presence::MOTION_ONLY) {
                voiceChat.startListening();
            } else
#endif
            // Nobody nearby: cycle expressions
            if (currentPresence <= Presence::MOTION_ONLY) {
                if (now - lastTouchTime >= LONG_PRESS_MS) face.randomExpression();
                else face.nextExpression();
                surprisedUntil = 0;
                currentExpression = face.getExpression();
                targetExpression = currentExpression;
            }
        }
    }

    // --- IMU tilt detection ---
    if (CoreS3.Imu.isEnabled()) {
        auto data = CoreS3.Imu.getImuData();
        float ax = data.accel.x;
        float ay = data.accel.y;
        float az = data.accel.z;
        // Tilt angle: 0=screen up (horizontal), 90=vertical, 180=screen down
        float g = sqrtf(ax*ax + ay*ay + az*az);
        if (g > 0.1f) {
            imuTilt = acosf(constrain(az / g, -1.0f, 1.0f)) * 180.0f / M_PI;
        }
        imuSmoothed = imuSmoothed * (1.0f - IMU_ALPHA) + imuTilt * IMU_ALPHA;
    }

    // --- Microphone ---
    static unsigned long lastMicCheck = 0;
#ifdef ENABLE_VOICE_CHAT
    bool micSkip = voiceChat.isActive();
#else
    bool micSkip = false;
#endif
    if (!micSkip && now - lastMicCheck >= 200 && now >= micMuteUntil) {
        lastMicCheck = now;
        bool recorded = CoreS3.Mic.record(micBuf, MIC_SAMPLES, 16000);
        float peak = 0;
        if (recorded) {
            for (int i = 0; i < MIC_SAMPLES; i++) {
                float v = fabsf((float)micBuf[i]);
                if (v > peak) peak = v;
            }
        }
        Serial.printf("MIC: rec=%d peak=%.0f avg=%.0f enabled=%d\n",
            recorded, peak, micAvgLevel, CoreS3.Mic.isEnabled());

        if (recorded && peak > 0) {
            if (peak < micAvgLevel * 2.0f) {
                micAvgLevel = micAvgLevel * 0.95f + peak * 0.05f;
            }
            if (micAvgLevel < 500) micAvgLevel = 500;

            if (now >= surprisedUntil && peak > micAvgLevel * MIC_SPIKE_RATIO && peak > MIC_MIN_PEAK) {
                LOG("LOUD! peak=%.0f avg=%.0f\n", peak, micAvgLevel);
                targetExpression = Expression::SURPRISED;
                currentExpression = Expression::SURPRISED;
                face.setExpression(Expression::SURPRISED);
                // playSoundForExpression(Expression::SURPRISED);
                surprisedUntil = now + SURPRISED_DURATION_MS;
                targetSince = now;
            }
        }
    }

    // --- Camera ---
    if (cameraActive && now - lastDetectTime >= DETECT_INTERVAL_MS) {
        lastDetectTime = now;
        auto r = camDetect.detect();

        // Push to history and get smoothed values
        pushHistory(r);
        auto s = getSmoothed();

        // Gaze tracking (use latest frame, not average)
        if (r.faceDetected) {
            face.setGaze(faceXToGaze(r.centerX), faceYToGaze(r.centerY));
        } else {
            face.clearExternalGaze();
        }

        Presence newPresence = evaluatePresence(s);

        if (newPresence != Presence::NONE) {
            lastPresenceTime = now;
        }

        // Surprised on first appearance
        Expression newTarget;
        bool isPresent = newPresence >= Presence::MOTION_ONLY;

        // Sub-sensors: tilt modifiers
        bool tilted = imuSmoothed > 30.0f;       // held/picked up
        bool veryTilted = imuSmoothed > 60.0f;   // cradled
        bool upsideDown = imuSmoothed > 140.0f;  // flipped

        // Main: camera presence decides base emotion
        // Sub: tilt & touch can upgrade (never downgrade) the emotion
        if (touchHeld && isPresent) {
            newTarget = Expression::LOVE;
        } else if (isPresent && !wasPresent && now >= surprisedUntil) {
            newTarget = Expression::SURPRISED;
            surprisedUntil = now + SURPRISED_DURATION_MS;
        } else if (now < surprisedUntil) {
            newTarget = Expression::SURPRISED;
        } else {
            newTarget = presenceToExpression(newPresence, now);
        }
        wasPresent = isPresent;

        // --- Sub-sensor modifiers: tilt can upgrade emotion ---
        if (upsideDown) {
            // Flipped upside down = always surprised (fun easter egg)
            newTarget = Expression::SURPRISED;
        } else if (veryTilted && newTarget == Expression::HAPPY) {
            // Cradled + someone nearby = LOVE
            newTarget = Expression::LOVE;
        } else if (tilted && newTarget == Expression::NORMAL) {
            // Picked up + face visible = HAPPY
            newTarget = Expression::HAPPY;
        }

        // --- Smooth expression transition ---
        if (newTarget != targetExpression) {
            targetExpression = newTarget;
            targetSince = now;
        }

        // Only switch expression after target has been stable for EXPR_SETTLE_MS
        // Exception: SURPRISED switches immediately
        if (targetExpression != currentExpression) {
            bool immediate = (targetExpression == Expression::SURPRISED) ||
                             (targetExpression == Expression::SAD);
            if (immediate || (now - targetSince >= EXPR_SETTLE_MS)) {
                currentExpression = targetExpression;
                face.setExpression(currentExpression);
                // playSoundForExpression(currentExpression);
            }
        }

        currentPresence = newPresence;

        // Update servos with current state
        servoCtrl.update(currentExpression, currentPresence,
                         r.faceDetected, r.centerX, r.centerY);

        LOG("P:%s area=%.2f mot=%.2f fRate=%.1f tilt=%.0f expr=%s->%s\n",
            presenceName(currentPresence), s.area, s.motion, s.faceRate, imuSmoothed,
            exprName(currentExpression), exprName(targetExpression));
    } else {
        // Camera not active or not time yet — still update servos for smooth motion
        servoCtrl.update(currentExpression, currentPresence, false, 160, 120);
    }

#ifdef ENABLE_VOICE_CHAT
    voiceChat.update(now);

    // Voice chat overrides expression while active
    Expression vcExpr;
    if (voiceChat.getExpressionOverride(vcExpr) && vcExpr != currentExpression) {
        currentExpression = vcExpr;
        face.setExpression(currentExpression);
    }
#endif

    face.update();
    delay(30);
}
