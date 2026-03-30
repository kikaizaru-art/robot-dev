#pragma once
#include <M5CoreS3.h>
#include "expressions.h"
#include <math.h>

// Emotion color theme
struct EmotionTheme {
    uint8_t r1, g1, b1;  // primary color
    uint8_t r2, g2, b2;  // secondary color
    float speed;          // animation speed multiplier
    uint8_t pattern;      // 0=breathe, 1=ripple, 2=drip, 3=flash, 4=pulse, 5=glow
};

static const EmotionTheme THEMES[] = {
    // NORMAL: calm teal, gentle breathing
    { 0, 180, 180,   0, 80, 100,   0.5f, 0 },
    // HAPPY: bright green-yellow, ripple outward
    { 80, 255, 50,   255, 220, 0,   1.2f, 1 },
    // SAD: deep blue, slow breathing with radial gradient (like NORMAL but blue)
    { 30, 60, 200,   10, 20, 120,   0.35f, 0 },
    // SURPRISED: instant white flash -> orange pulse
    { 255, 180, 30,  255, 255, 255,  5.0f, 3 },
    // SLEEPY: dark purple, slow breathing
    { 80, 30, 120,   40, 10, 60,    0.25f, 4 },
    // LOVE: warm pink/red, center glow
    { 255, 50, 80,   255, 120, 160,  0.8f, 5 },
};

class Face {
public:
    static constexpr int W = 320;
    static constexpr int H = 240;
    static constexpr int CX = W / 2;
    static constexpr int CY = H / 2;

    void begin() {
        _sprite.createSprite(W, H);
        _sprite.setColorDepth(16);
        _expression = Expression::NORMAL;
        _startTime = millis();
        _transitionStart = millis();
        _prevR = 0; _prevG = 0; _prevB = 0;
    }

    void update() {
        draw();
    }

    void setExpression(Expression expr) {
        if (expr != _expression) {
            _prevR = _curR; _prevG = _curG; _prevB = _curB;
            _transitionStart = millis();
            _expression = expr;
            // SURPRISED: skip transition, instant flash
            if (expr == Expression::SURPRISED) {
                _transitionStart = millis() - (unsigned long)TRANSITION_MS;
            }
        }
    }

    Expression getExpression() const { return _expression; }

    void nextExpression() {
        uint8_t next = (static_cast<uint8_t>(_expression) + 1) % static_cast<uint8_t>(Expression::COUNT);
        setExpression(static_cast<Expression>(next));
    }

    void randomExpression() {
        Expression next;
        do {
            next = static_cast<Expression>(random(0, static_cast<int>(Expression::COUNT)));
        } while (next == _expression);
        setExpression(next);
    }

    // Keep gaze API for compatibility (unused in color mode but main.cpp calls it)
    void setGaze(int8_t x, int8_t y) {}
    void clearExternalGaze() {}

private:
    M5Canvas _sprite{&CoreS3.Display};
    Expression _expression = Expression::NORMAL;
    unsigned long _startTime = 0;
    unsigned long _transitionStart = 0;
    uint8_t _prevR = 0, _prevG = 0, _prevB = 0;
    uint8_t _curR = 0, _curG = 0, _curB = 0;

    static constexpr float TRANSITION_MS = 800.0f;

    // Fast integer square root approximation
    static int isqrt(int val) {
        if (val <= 0) return 0;
        int x = val;
        int y = (x + 1) / 2;
        while (y < x) { x = y; y = (val / y + y) / 2; }
        return x;
    }

    // Mix two colors by ratio (0.0 = a, 1.0 = b)
    static void mixColor(uint8_t ar, uint8_t ag, uint8_t ab,
                         uint8_t br, uint8_t bg, uint8_t bb,
                         float t, uint8_t &or_, uint8_t &og, uint8_t &ob) {
        if (t < 0) t = 0; if (t > 1) t = 1;
        or_ = ar + (br - ar) * t;
        og = ag + (bg - ag) * t;
        ob = ab + (bb - ab) * t;
    }

    uint16_t toRGB565(uint8_t r, uint8_t g, uint8_t b) {
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
    }

    void draw() {
        const auto& th = THEMES[static_cast<uint8_t>(_expression)];
        float t = (millis() - _startTime) / 1000.0f;
        float st = t * th.speed;

        // Transition blending
        float transT = (millis() - _transitionStart) / TRANSITION_MS;
        if (transT > 1.0f) transT = 1.0f;

        switch (th.pattern) {
            case 0: drawBreathe(th, st, transT); break;
            case 1: drawRipple(th, st, transT); break;
            case 2: drawDrip(th, st, transT); break;
            case 3: drawFlash(th, st, transT); break;
            case 4: drawPulse(th, st, transT); break;
            case 5: drawGlow(th, st, transT); break;
        }

        _sprite.pushSprite(0, 0);
    }

    // Apply transition: blend pixel color with previous color
    void setPixelWithTransition(int x, int y, uint8_t r, uint8_t g, uint8_t b, float transT) {
        uint8_t fr, fg, fb;
        mixColor(_prevR, _prevG, _prevB, r, g, b, transT, fr, fg, fb);
        _sprite.drawPixel(x, y, toRGB565(fr, fg, fb));
        // Track current color (center pixel as reference)
        if (x == CX && y == CY) { _curR = r; _curG = g; _curB = b; }
    }

    // NORMAL: calm breathing - whole screen gently pulses
    void drawBreathe(const EmotionTheme& th, float st, float transT) {
        float breath = (sinf(st * 2.0f) + 1.0f) * 0.5f; // 0..1
        float intensity = 0.15f + breath * 0.35f; // 0.15..0.5

        uint8_t r = th.r1 * intensity;
        uint8_t g = th.g1 * intensity;
        uint8_t b = th.b1 * intensity;

        // Subtle radial gradient: brighter in center
        for (int y = 0; y < H; y += 2) {
            for (int x = 0; x < W; x += 2) {
                int dx = x - CX;
                int dy = y - CY;
                float dist = isqrt(dx*dx + dy*dy) / 200.0f;
                float falloff = 1.0f - dist * 0.5f;
                if (falloff < 0.1f) falloff = 0.1f;

                uint8_t pr = r * falloff;
                uint8_t pg = g * falloff;
                uint8_t pb = b * falloff;

                uint16_t col;
                if (transT < 1.0f) {
                    uint8_t fr, fg, fb;
                    mixColor(_prevR, _prevG, _prevB, pr, pg, pb, transT, fr, fg, fb);
                    col = toRGB565(fr, fg, fb);
                } else {
                    col = toRGB565(pr, pg, pb);
                }
                // Draw 2x2 block for performance
                _sprite.fillRect(x, y, 2, 2, col);
            }
        }
        _curR = r; _curG = g; _curB = b;
    }

    // HAPPY: ripple waves expanding from center
    void drawRipple(const EmotionTheme& th, float st, float transT) {
        float phase = st * 3.0f;

        for (int y = 0; y < H; y += 2) {
            for (int x = 0; x < W; x += 2) {
                int dx = x - CX;
                int dy = y - CY;
                float dist = isqrt(dx*dx + dy*dy);
                float wave = sinf(dist * 0.05f - phase);
                float intensity = (wave + 1.0f) * 0.5f; // 0..1
                intensity = intensity * 0.5f + 0.1f; // 0.1..0.6

                uint8_t r, g, b;
                mixColor(th.r1, th.g1, th.b1, th.r2, th.g2, th.b2, intensity, r, g, b);

                // Fade at edges
                float edgeFade = 1.0f - dist / 220.0f;
                if (edgeFade < 0) edgeFade = 0;
                r *= edgeFade; g *= edgeFade; b *= edgeFade;

                uint16_t col;
                if (transT < 1.0f) {
                    uint8_t fr, fg, fb;
                    mixColor(_prevR, _prevG, _prevB, r, g, b, transT, fr, fg, fb);
                    col = toRGB565(fr, fg, fb);
                } else {
                    col = toRGB565(r, g, b);
                }
                _sprite.fillRect(x, y, 2, 2, col);
            }
        }
        _curR = th.r1 / 3; _curG = th.g1 / 3; _curB = th.b1 / 3;
    }

    // SAD: blue drips falling from top
    void drawDrip(const EmotionTheme& th, float st, float transT) {
        // Background: dark blue
        float bgI = 0.08f + sinf(st) * 0.03f;
        uint8_t bgR = th.r2 * bgI;
        uint8_t bgG = th.g2 * bgI;
        uint8_t bgB = th.b2 * bgI;

        _sprite.fillSprite(toRGB565(bgR, bgG, bgB));

        // Multiple drip columns
        for (int d = 0; d < 5; d++) {
            int dripX = 40 + d * 65 + (int)(sinf(d * 1.7f) * 20);
            float dripPhase = fmodf(st * 0.7f + d * 0.4f, 2.0f);
            float dripY = dripPhase * (H + 40) - 40;

            // Draw drip as a vertical gradient blob
            for (int y = (int)dripY - 60; y < (int)dripY + 20; y++) {
                if (y < 0 || y >= H) continue;
                float localT = 1.0f - fabsf(y - dripY) / 60.0f;
                if (localT < 0) localT = 0;
                localT = localT * localT; // sharper falloff

                int width = 8 + localT * 12;
                for (int x = dripX - width; x <= dripX + width; x++) {
                    if (x < 0 || x >= W) continue;
                    float xFade = 1.0f - fabsf(x - dripX) / (float)width;
                    float intensity = localT * xFade * 0.6f;

                    uint8_t r = bgR + (th.r1 - bgR) * intensity;
                    uint8_t g = bgG + (th.g1 - bgG) * intensity;
                    uint8_t b = bgB + (th.b1 - bgB) * intensity;

                    if (transT < 1.0f) {
                        uint8_t fr, fg, fb;
                        mixColor(_prevR, _prevG, _prevB, r, g, b, transT, fr, fg, fb);
                        _sprite.drawPixel(x, y, toRGB565(fr, fg, fb));
                    } else {
                        _sprite.drawPixel(x, y, toRGB565(r, g, b));
                    }
                }
            }
        }
        _curR = bgR; _curG = bgG; _curB = bgB;
    }

    // SURPRISED: instant white flash then pulsing orange
    void drawFlash(const EmotionTheme& th, float st, float transT) {
        float flashPhase = fmodf(st, 1.5f);
        float intensity;

        if (flashPhase < 0.08f) {
            // Instant white flash
            intensity = 1.0f;
            uint8_t v = 220 + 35 * (1.0f - flashPhase / 0.08f);
            for (int y = 0; y < H; y += 2) {
                for (int x = 0; x < W; x += 2) {
                    uint16_t col;
                    if (transT < 1.0f) {
                        uint8_t fr, fg, fb;
                        mixColor(_prevR, _prevG, _prevB, v, v, v, transT, fr, fg, fb);
                        col = toRGB565(fr, fg, fb);
                    } else {
                        col = toRGB565(v, v, v);
                    }
                    _sprite.fillRect(x, y, 2, 2, col);
                }
            }
            _curR = v; _curG = v; _curB = v;
            return;
        }

        // Pulsing orange after flash
        float pulse = sinf((flashPhase - 0.15f) * 4.0f);
        intensity = 0.2f + (pulse + 1.0f) * 0.2f;

        for (int y = 0; y < H; y += 2) {
            for (int x = 0; x < W; x += 2) {
                int dx = x - CX;
                int dy = y - CY;
                float dist = isqrt(dx*dx + dy*dy) / 200.0f;
                float i = intensity * (1.0f - dist * 0.4f);
                if (i < 0) i = 0;

                uint8_t r = th.r1 * i;
                uint8_t g = th.g1 * i;
                uint8_t b = th.b1 * i;

                uint16_t col;
                if (transT < 1.0f) {
                    uint8_t fr, fg, fb;
                    mixColor(_prevR, _prevG, _prevB, r, g, b, transT, fr, fg, fb);
                    col = toRGB565(fr, fg, fb);
                } else {
                    col = toRGB565(r, g, b);
                }
                _sprite.fillRect(x, y, 2, 2, col);
            }
        }
        _curR = th.r1 * intensity; _curG = th.g1 * intensity; _curB = th.b1 * intensity;
    }

    // SLEEPY: very slow dim purple breathing
    void drawPulse(const EmotionTheme& th, float st, float transT) {
        float breath = (sinf(st * 1.5f) + 1.0f) * 0.5f;
        float intensity = 0.05f + breath * 0.15f; // very dim

        for (int y = 0; y < H; y += 2) {
            for (int x = 0; x < W; x += 2) {
                // Soft noise-like variation
                float noise = sinf(x * 0.02f + st * 0.5f) * sinf(y * 0.025f + st * 0.3f);
                float i = intensity + noise * 0.03f;
                if (i < 0) i = 0;

                uint8_t r, g, b;
                mixColor(th.r2, th.g2, th.b2, th.r1, th.g1, th.b1, breath, r, g, b);
                r *= i; g *= i; b *= i;

                uint16_t col;
                if (transT < 1.0f) {
                    uint8_t fr, fg, fb;
                    mixColor(_prevR, _prevG, _prevB, r, g, b, transT, fr, fg, fb);
                    col = toRGB565(fr, fg, fb);
                } else {
                    col = toRGB565(r, g, b);
                }
                _sprite.fillRect(x, y, 2, 2, col);
            }
        }
        _curR = th.r1 * intensity; _curG = th.g1 * intensity; _curB = th.b1 * intensity;
    }

    // LOVE: warm pink glow radiating from center
    void drawGlow(const EmotionTheme& th, float st, float transT) {
        float pulse = (sinf(st * 2.5f) + 1.0f) * 0.5f;
        float radius = 80.0f + pulse * 60.0f; // breathing radius

        for (int y = 0; y < H; y += 2) {
            for (int x = 0; x < W; x += 2) {
                int dx = x - CX;
                int dy = y - CY;
                float dist = isqrt(dx*dx + dy*dy);

                // Soft glow from center
                float glow = 1.0f - dist / radius;
                if (glow < 0) glow = 0;
                glow = glow * glow; // quadratic falloff for soft edge

                float intensity = glow * (0.4f + pulse * 0.3f);

                uint8_t r, g, b;
                mixColor(th.r2, th.g2, th.b2, th.r1, th.g1, th.b1, glow, r, g, b);
                r *= intensity + 0.05f;
                g *= intensity + 0.02f;
                b *= intensity + 0.02f;

                uint16_t col;
                if (transT < 1.0f) {
                    uint8_t fr, fg, fb;
                    mixColor(_prevR, _prevG, _prevB, r, g, b, transT, fr, fg, fb);
                    col = toRGB565(fr, fg, fb);
                } else {
                    col = toRGB565(r, g, b);
                }
                _sprite.fillRect(x, y, 2, 2, col);
            }
        }
        _curR = th.r1 / 3; _curG = th.g1 / 3; _curB = th.b1 / 3;
    }
};
