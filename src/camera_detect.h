#pragma once
#include <M5CoreS3.h>
#include "human_face_detect_msr01.hpp"

struct DetectResult {
    // Face detection (ML)
    bool faceDetected;
    int centerX;
    int centerY;
    int width;
    int height;
    float score;
    float areaRatio;

    // Skin detection
    bool skinDetected;
    float skinRatio;       // 0.0-1.0

    // Proximity (frame difference)
    bool motionDetected;
    float motionLevel;     // 0.0-1.0

    // Combined brightness
    float brightness;      // 0.0-1.0
};

class CameraDetect {
public:
    static constexpr int CAM_W = 320;
    static constexpr int CAM_H = 240;
    static constexpr float SCREEN_AREA = CAM_W * CAM_H;
    static constexpr int SAMPLE_STEP = 4;

    // Thresholds
    static constexpr float SKIN_CLOSE = 0.35f;
    static constexpr float SKIN_NEARBY = 0.10f;
    static constexpr float MOTION_THRESHOLD = 0.30f;

    bool begin() {
        if (!CoreS3.Camera.begin()) {
            Serial.println("Camera init failed!");
            return false;
        }
        _detector = new HumanFaceDetectMSR01(0.3f, 0.3f, 1, 1.0f);
        _prevFrame = (uint16_t *)ps_malloc(CAM_W * CAM_H * sizeof(uint16_t));
        _hasPrevFrame = false;
        Serial.println("Camera + all detectors ready");
        return true;
    }

    DetectResult detect() {
        DetectResult result = {};

        if (!CoreS3.Camera.get()) return result;

        uint16_t *frame = (uint16_t *)CoreS3.Camera.fb->buf;

        // Run all analyses
        analyzeFrame(frame, result);

        // Face detection (ML)
        std::vector<int> shape = {CAM_H, CAM_W, 3};
        auto &detections = _detector->infer<uint16_t>(frame, shape);

        if (!detections.empty()) {
            auto &best = detections.front();
            result.faceDetected = true;
            result.width = best.box[2] - best.box[0];
            result.height = best.box[3] - best.box[1];
            result.centerX = (best.box[0] + best.box[2]) / 2;
            result.centerY = (best.box[1] + best.box[3]) / 2;
            result.score = best.score;
            result.areaRatio = (float)(result.width * result.height) / SCREEN_AREA;
        }

        // Save for next frame diff
        if (_prevFrame) {
            memcpy(_prevFrame, frame, CAM_W * CAM_H * sizeof(uint16_t));
            _hasPrevFrame = true;
        }

        CoreS3.Camera.free();
        return result;
    }

private:
    HumanFaceDetectMSR01 *_detector = nullptr;
    uint16_t *_prevFrame = nullptr;
    bool _hasPrevFrame = false;

    static inline bool isSkinPixel(uint16_t pixel) {
        uint8_t r = ((pixel >> 11) & 0x1F) << 3;
        uint8_t g = ((pixel >> 5) & 0x3F) << 2;
        uint8_t b = (pixel & 0x1F) << 3;
        if (r < 60 || g < 30 || b < 15) return false;
        if (r <= g || g <= b) return false;
        if (r - g > 80) return false;
        if (r + g + b < 120 || r + g + b > 680) return false;
        return true;
    }

    static inline uint8_t brightness565(uint16_t pixel) {
        uint8_t r = (pixel >> 11) & 0x1F;
        uint8_t g = (pixel >> 5) & 0x3F;
        uint8_t b = pixel & 0x1F;
        return (r * 5 + g * 3 + b * 5) >> 2;
    }

    void analyzeFrame(uint16_t *frame, DetectResult &result) {
        int skinCount = 0;
        uint32_t diffSum = 0;
        uint32_t brightSum = 0;
        int sampleCount = 0;

        for (int y = 0; y < CAM_H; y += SAMPLE_STEP) {
            for (int x = 0; x < CAM_W; x += SAMPLE_STEP) {
                int idx = y * CAM_W + x;
                uint16_t px = frame[idx];

                if (isSkinPixel(px)) skinCount++;

                uint8_t b = brightness565(px);
                brightSum += b;

                if (_hasPrevFrame) {
                    uint8_t pb = brightness565(_prevFrame[idx]);
                    diffSum += abs((int)b - (int)pb);
                }
                sampleCount++;
            }
        }

        if (sampleCount > 0) {
            result.skinRatio = (float)skinCount / sampleCount;
            result.skinDetected = result.skinRatio >= SKIN_NEARBY;
            result.brightness = (float)brightSum / (sampleCount * 40.0f);
            if (_hasPrevFrame) {
                result.motionLevel = (float)diffSum / (sampleCount * 40.0f);
                result.motionDetected = result.motionLevel >= MOTION_THRESHOLD;
            }
        }
    }
};
