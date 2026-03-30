#pragma once
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include "expressions.h"

// Forward declaration — Presence is defined in main.cpp
enum class Presence : uint8_t;

class ServoCtrl {
public:
    // Channel assignment
    static constexpr int CH_YAW   = 0;
    static constexpr int CH_TILT  = 1;
    static constexpr int CH_ARM_L = 2;
    static constexpr int CH_ARM_R = 3;

    // Servo limits (degrees)
    static constexpr float YAW_MIN  = 45.0f;
    static constexpr float YAW_MAX  = 135.0f;
    static constexpr float YAW_CENTER = 90.0f;
    static constexpr float TILT_MIN = 60.0f;
    static constexpr float TILT_MAX = 120.0f;
    static constexpr float TILT_CENTER = 90.0f;
    static constexpr float ARM_MIN  = 40.0f;
    static constexpr float ARM_MAX  = 140.0f;
    static constexpr float ARM_CENTER = 90.0f;

    // Pulse range (MG90S)
    static constexpr int SERVO_MIN_US = 500;
    static constexpr int SERVO_MAX_US = 2400;
    static constexpr int SERVO_FREQ   = 50;

    // Movement speeds (degrees per update call)
    static constexpr float NORMAL_SPEED = 2.0f;
    static constexpr float FAST_SPEED   = 10.0f;

    // Idle motion
    static constexpr unsigned long IDLE_INTERVAL_MS = 3000;

    bool begin() {
        Wire.beginTransmission(0x40);
        _connected = (Wire.endTransmission() == 0);
        if (!_connected) return false;

        _pwm.begin();
        _pwm.setOscillatorFrequency(25000000);
        _pwm.setPWMFreq(SERVO_FREQ);
        delay(100);

        // All servos to center
        for (int i = 0; i < 4; i++) {
            _current[i] = 90.0f;
            _target[i] = 90.0f;
            writeAngle(i, 90.0f);
        }
        return true;
    }

    bool isConnected() const { return _connected; }

    void update(Expression expr, Presence presence, bool faceDetected,
                int faceCenterX, int faceCenterY) {
        if (!_connected) return;

        unsigned long now = millis();
        _expr = expr;
        _presence = presence;

        // --- Neck: head tracking or idle ---
        updateNeck(faceDetected, faceCenterX, faceCenterY, now);

        // --- Arms: expression-driven animation ---
        updateArms(now);

        // --- Move servos toward targets ---
        for (int i = 0; i < 4; i++) {
            float speed = _speed[i];
            if (_current[i] != _target[i]) {
                float diff = _target[i] - _current[i];
                if (fabsf(diff) <= speed) {
                    _current[i] = _target[i];
                } else {
                    _current[i] += (diff > 0) ? speed : -speed;
                }
                writeAngle(i, _current[i]);
            }
        }
    }

private:
    Adafruit_PWMServoDriver _pwm = Adafruit_PWMServoDriver(0x40, Wire);
    bool _connected = false;
    Expression _expr = Expression::NORMAL;
    Presence _presence = (Presence)0;

    float _current[4] = {90, 90, 90, 90};
    float _target[4]  = {90, 90, 90, 90};
    float _speed[4]   = {NORMAL_SPEED, NORMAL_SPEED, NORMAL_SPEED, NORMAL_SPEED};

    // Idle state
    unsigned long _lastIdleChange = 0;
    float _idleYawTarget = 90.0f;
    float _idleTiltTarget = 90.0f;

    // Arm animation state
    unsigned long _armAnimStart = 0;
    Expression _prevArmExpr = Expression::NORMAL;

    void writeAngle(int channel, float angle) {
        int a = constrain((int)angle, 0, 180);
        _pwm.writeMicroseconds(channel, map(a, 0, 180, SERVO_MIN_US, SERVO_MAX_US));
    }

    // --- Neck logic ---
    void updateNeck(bool faceDetected, int fx, int fy, unsigned long now) {
        _speed[CH_YAW] = NORMAL_SPEED;
        _speed[CH_TILT] = NORMAL_SPEED;

        if (_expr == Expression::SLEEPY) {
            // Droopy: tilt head down, yaw center
            _target[CH_YAW] = YAW_CENTER;
            _target[CH_TILT] = 75.0f;
            return;
        }

        if (faceDetected) {
            // Track face
            // Camera image is mirrored, so invert X
            // X: 0(left edge)→135°, 160(center)→90°, 320(right edge)→45°
            float yaw = mapFloat((float)fx, 0.0f, 320.0f, YAW_MAX, YAW_MIN);
            // Y: 0(top)→110°, 120(center)→90°, 240(bottom)→70°
            float tilt = mapFloat((float)fy, 0.0f, 240.0f, 110.0f, 70.0f);

            _target[CH_YAW]  = constrain(yaw, YAW_MIN, YAW_MAX);
            _target[CH_TILT] = constrain(tilt, TILT_MIN, TILT_MAX);
            _lastIdleChange = now;  // reset idle timer
            return;
        }

        // No face, no presence → idle look-around
        if ((uint8_t)_presence == 0) {  // Presence::NONE
            if (now - _lastIdleChange >= IDLE_INTERVAL_MS) {
                _lastIdleChange = now;
                // Random target within a gentle range
                _idleYawTarget = YAW_CENTER + (float)(random(-30, 31));
                _idleTiltTarget = TILT_CENTER + (float)(random(-10, 11));
                _idleYawTarget = constrain(_idleYawTarget, YAW_MIN, YAW_MAX);
                _idleTiltTarget = constrain(_idleTiltTarget, TILT_MIN, TILT_MAX);
            }
            _target[CH_YAW] = _idleYawTarget;
            _target[CH_TILT] = _idleTiltTarget;
            _speed[CH_YAW] = 1.0f;   // slow idle motion
            _speed[CH_TILT] = 1.0f;
        } else {
            // Someone nearby but no face detected — hold last position
        }
    }

    // --- Arm logic ---
    void updateArms(unsigned long now) {
        // Reset animation timer on expression change
        if (_expr != _prevArmExpr) {
            _armAnimStart = now;
            _prevArmExpr = _expr;
        }

        float elapsed = (float)(now - _armAnimStart);

        switch (_expr) {
        case Expression::HAPPY: {
            // Small wave: 70°-110° at ~1Hz
            float phase = sinf(elapsed * 0.006f);  // ~1Hz
            float angle = ARM_CENTER + phase * 20.0f;
            _target[CH_ARM_L] = angle;
            _target[CH_ARM_R] = ARM_CENTER - phase * 20.0f;  // opposite phase
            _speed[CH_ARM_L] = NORMAL_SPEED;
            _speed[CH_ARM_R] = NORMAL_SPEED;
            break;
        }
        case Expression::LOVE: {
            // Slow gentle wave: 60°-120° at ~0.5Hz
            float phase = sinf(elapsed * 0.003f);
            float angle = ARM_CENTER + phase * 30.0f;
            _target[CH_ARM_L] = angle;
            _target[CH_ARM_R] = angle;  // sync
            _speed[CH_ARM_L] = NORMAL_SPEED;
            _speed[CH_ARM_R] = NORMAL_SPEED;
            break;
        }
        case Expression::SURPRISED: {
            // Arms up fast, then return after 800ms
            if (elapsed < 800) {
                _target[CH_ARM_L] = ARM_MIN;  // 40° = arms up
                _target[CH_ARM_R] = ARM_MIN;
                _speed[CH_ARM_L] = FAST_SPEED;
                _speed[CH_ARM_R] = FAST_SPEED;
            } else {
                _target[CH_ARM_L] = ARM_CENTER;
                _target[CH_ARM_R] = ARM_CENTER;
                _speed[CH_ARM_L] = NORMAL_SPEED;
                _speed[CH_ARM_R] = NORMAL_SPEED;
            }
            break;
        }
        case Expression::SAD: {
            _target[CH_ARM_L] = 130.0f;  // droopy
            _target[CH_ARM_R] = 130.0f;
            _speed[CH_ARM_L] = 1.0f;  // slow droop
            _speed[CH_ARM_R] = 1.0f;
            break;
        }
        case Expression::SLEEPY: {
            _target[CH_ARM_L] = 140.0f;  // fully drooped
            _target[CH_ARM_R] = 140.0f;
            _speed[CH_ARM_L] = 0.5f;  // very slow
            _speed[CH_ARM_R] = 0.5f;
            break;
        }
        default: {
            // NORMAL / NONE: neutral
            _target[CH_ARM_L] = ARM_CENTER;
            _target[CH_ARM_R] = ARM_CENTER;
            _speed[CH_ARM_L] = NORMAL_SPEED;
            _speed[CH_ARM_R] = NORMAL_SPEED;
            break;
        }
        }
    }

    static float mapFloat(float x, float inMin, float inMax, float outMin, float outMax) {
        return (x - inMin) * (outMax - outMin) / (inMax - inMin) + outMin;
    }
};
