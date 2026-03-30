#pragma once
// Voice Chat Module - Gemini API powered voice conversation
//
// Records audio from internal mic, sends to Gemini API,
// plays back audio response through speaker.
//
// To omit: remove ENABLE_VOICE_CHAT from build_flags in platformio.ini

#include <M5CoreS3.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "mbedtls/base64.h"
#include "gemini_config.h"
#include "expressions.h"

// Forward declaration for LOG (defined in main.cpp)
template<typename... Args> void LOG(const char* fmt, Args... args);

class VoiceChat {
public:
    enum class State : uint8_t {
        IDLE,
        LISTENING,      // Recording audio from mic
        PROCESSING,     // Gemini API call in progress
        SPEAKING,       // Playing audio response
    };

    bool begin() {
        if (strlen(GEMINI_API_KEY) < 10 ||
            strcmp(GEMINI_API_KEY, "YOUR_GEMINI_API_KEY_HERE") == 0) {
            LOG("[Voice] No API key - disabled\n");
            return false;
        }

        recBuf_ = (int16_t*)ps_malloc(REC_MAX_SAMPLES * sizeof(int16_t));
        ttsBuf_ = (uint8_t*)ps_malloc(TTS_MAX_BYTES);

        if (!recBuf_ || !ttsBuf_) {
            LOG("[Voice] PSRAM alloc failed\n");
            if (recBuf_) { free(recBuf_); recBuf_ = nullptr; }
            if (ttsBuf_) { free(ttsBuf_); ttsBuf_ = nullptr; }
            return false;
        }

        enabled_ = true;
        LOG("[Voice] Ready\n");
        return true;
    }

    void update(unsigned long now) {
        if (!enabled_) return;

        switch (state_) {
        case State::IDLE:
            break;

        case State::LISTENING:
            handleListening(now);
            break;

        case State::PROCESSING:
            if (taskDone_) {
                taskDone_ = false;
                if (ttsLen_ > 0) {
                    startPlayback();
                    state_ = State::SPEAKING;
                    LOG("[Voice] Speaking...\n");
                } else {
                    state_ = State::IDLE;
                    cooldownUntil_ = now + COOLDOWN_MS;
                    LOG("[Voice] No audio in response\n");
                }
            }
            break;

        case State::SPEAKING:
            if (!CoreS3.Speaker.isPlaying()) {
                state_ = State::IDLE;
                cooldownUntil_ = now + COOLDOWN_MS;
                LOG("[Voice] Done\n");
            }
            break;
        }
    }

    // Start recording (called from touch handler)
    void startListening() {
        if (!enabled_ || state_ != State::IDLE) return;
        if (millis() < cooldownUntil_) return;
        if (WiFi.status() != WL_CONNECTED) {
            LOG("[Voice] No WiFi\n");
            return;
        }
        beginRecording();
    }

    State getState() const { return state_; }
    bool isActive() const { return state_ != State::IDLE; }
    bool isListening() const { return state_ == State::LISTENING; }

    // Suggest expression override while voice chat is active
    bool getExpressionOverride(Expression &out) const {
        switch (state_) {
        case State::LISTENING:  out = Expression::NORMAL;  return true;
        case State::PROCESSING: out = Expression::HAPPY;   return true;
        case State::SPEAKING:   out = Expression::HAPPY;   return true;
        default: return false;
        }
    }

private:
    // --- Config ---
    static const int REC_RATE = 16000;          // 16kHz recording
    static const int REC_DURATION_MS = 3000;    // 3 seconds
    static const int REC_MAX_SAMPLES = REC_RATE * REC_DURATION_MS / 1000;  // 48000
    static const int REC_CHUNK = 800;           // 50ms per mic read

    static const int TTS_MAX_BYTES = 512 * 1024;  // 512KB max audio response
    static const unsigned long COOLDOWN_MS = 3000; // 3s between conversations

    // --- State ---
    bool enabled_ = false;
    State state_ = State::IDLE;
    unsigned long cooldownUntil_ = 0;

    // Recording
    int16_t* recBuf_ = nullptr;
    int recPos_ = 0;
    unsigned long recEndTime_ = 0;

    // TTS playback
    uint8_t* ttsBuf_ = nullptr;
    int ttsLen_ = 0;        // decoded audio bytes
    int ttsRate_ = 24000;   // sample rate from API

    // FreeRTOS task
    TaskHandle_t taskHandle_ = nullptr;
    volatile bool taskDone_ = false;

    // --- Recording ---

    void beginRecording() {
        state_ = State::LISTENING;
        recPos_ = 0;
        recEndTime_ = millis() + REC_DURATION_MS;
        LOG("[Voice] Listening... (%dms)\n", REC_DURATION_MS);
    }

    void handleListening(unsigned long now) {
        // Record chunks until time is up or buffer full
        if (now >= recEndTime_ || recPos_ >= REC_MAX_SAMPLES) {
            LOG("[Voice] Recorded %d samples (%.1fs)\n",
                recPos_, (float)recPos_ / REC_RATE);

            state_ = State::PROCESSING;
            taskDone_ = false;

            // Run API call on core 0 to keep face animation running
            xTaskCreatePinnedToCore(
                apiTaskEntry, "voice_api", 32768,
                this, 1, &taskHandle_, 0
            );
            return;
        }

        int remaining = REC_MAX_SAMPLES - recPos_;
        int toRead = (remaining < REC_CHUNK) ? remaining : REC_CHUNK;

        if (CoreS3.Mic.record(recBuf_ + recPos_, toRead, REC_RATE)) {
            recPos_ += toRead;
        }
    }

    // --- API Task (runs on core 0) ---

    static void apiTaskEntry(void* param) {
        VoiceChat* self = (VoiceChat*)param;
        self->runApiCall();
        self->taskDone_ = true;
        vTaskDelete(nullptr);
    }

    void runApiCall() {
        ttsLen_ = 0;

        // Build WAV from recorded PCM
        int pcmBytes = recPos_ * 2;  // 16-bit = 2 bytes/sample
        int wavLen = 44 + pcmBytes;
        uint8_t* wav = (uint8_t*)ps_malloc(wavLen);
        if (!wav) { Serial.println("[Voice] WAV alloc fail"); return; }

        writeWavHeader(wav, pcmBytes);
        memcpy(wav + 44, recBuf_, pcmBytes);

        // Base64 encode
        size_t b64Len = 0;
        mbedtls_base64_encode(nullptr, 0, &b64Len, wav, wavLen);

        char* b64 = (char*)ps_malloc(b64Len + 1);
        if (!b64) { free(wav); Serial.println("[Voice] B64 alloc fail"); return; }

        mbedtls_base64_encode((uint8_t*)b64, b64Len + 1, &b64Len, wav, wavLen);
        b64[b64Len] = 0;
        free(wav);

        Serial.printf("[Voice] Encoded %d bytes -> %d b64\n", wavLen, b64Len);

        // Try TTS model first, fallback to text model
        if (!callGeminiTTS(b64)) {
            Serial.println("[Voice] TTS model failed, trying text fallback...");
            callGeminiText(b64);
        }

        free(b64);
    }

    // Primary: Gemini with audio output
    bool callGeminiTTS(const char* audioBase64) {
        WiFiClientSecure client;
        client.setInsecure();
        HTTPClient http;

        String url = String("https://generativelanguage.googleapis.com/v1beta/models/")
            + GEMINI_TTS_MODEL + ":generateContent?key=" + GEMINI_API_KEY;

        if (!http.begin(client, url)) {
            Serial.println("[Voice] HTTP begin failed");
            return false;
        }

        http.addHeader("Content-Type", "application/json");
        http.setTimeout(30000);

        // Build JSON with string concatenation (avoids double-buffering large base64)
        String json;
        json.reserve(strlen(audioBase64) + 2048);

        json += F("{\"system_instruction\":{\"parts\":[{\"text\":\"");
        json += GEMINI_SYSTEM_PROMPT;
        json += F("\"}]},\"contents\":[{\"role\":\"user\",\"parts\":[");
        json += F("{\"inline_data\":{\"mime_type\":\"audio/wav\",\"data\":\"");
        json += audioBase64;
        json += F("\"}},{\"text\":\"");
        json += GEMINI_USER_PROMPT;
        json += F("\"}]}],\"generationConfig\":{");
        json += F("\"response_modalities\":[\"AUDIO\"],");
        json += F("\"speech_config\":{\"voice_config\":{\"prebuilt_voice_config\":{\"voice_name\":\"");
        json += GEMINI_VOICE_NAME;
        json += F("\"}}}}}");

        Serial.printf("[Voice] POST TTS (%d bytes)...\n", json.length());
        int httpCode = http.POST(json);
        json = "";  // free memory

        if (httpCode != 200) {
            Serial.printf("[Voice] TTS HTTP %d\n", httpCode);
            if (httpCode > 0) {
                String err = http.getString();
                Serial.println(err.substring(0, 300));
            }
            http.end();
            return false;
        }

        // Parse response
        String response = http.getString();
        http.end();

        Serial.printf("[Voice] TTS response: %d bytes\n", response.length());
        return parseAudioResponse(response);
    }

    // Fallback: text-only response
    void callGeminiText(const char* audioBase64) {
        WiFiClientSecure client;
        client.setInsecure();
        HTTPClient http;

        String url = String("https://generativelanguage.googleapis.com/v1beta/models/")
            + GEMINI_TEXT_MODEL + ":generateContent?key=" + GEMINI_API_KEY;

        if (!http.begin(client, url)) return;

        http.addHeader("Content-Type", "application/json");
        http.setTimeout(15000);

        String json;
        json.reserve(strlen(audioBase64) + 1024);

        json += F("{\"system_instruction\":{\"parts\":[{\"text\":\"");
        json += GEMINI_SYSTEM_PROMPT;
        json += F("\"}]},\"contents\":[{\"role\":\"user\",\"parts\":[");
        json += F("{\"inline_data\":{\"mime_type\":\"audio/wav\",\"data\":\"");
        json += audioBase64;
        json += F("\"}},{\"text\":\"");
        json += GEMINI_USER_PROMPT;
        json += F("\"}]}],\"generationConfig\":{\"maxOutputTokens\":100,\"temperature\":0.7}}");

        Serial.printf("[Voice] POST text (%d bytes)...\n", json.length());
        int httpCode = http.POST(json);
        json = "";

        if (httpCode == 200) {
            String response = http.getString();
            JsonDocument doc;
            if (!deserializeJson(doc, response)) {
                const char* text = doc["candidates"][0]["content"]["parts"][0]["text"];
                if (text) {
                    Serial.printf("[Voice] Text response: %s\n", text);
                }
            }
        } else {
            Serial.printf("[Voice] Text HTTP %d\n", httpCode);
        }
        http.end();
    }

    // Parse audio data from Gemini response
    bool parseAudioResponse(const String& response) {
        JsonDocument doc;
        DeserializationError err = deserializeJson(doc, response);
        if (err) {
            Serial.printf("[Voice] JSON error: %s\n", err.c_str());
            return false;
        }

        JsonArray parts = doc["candidates"][0]["content"]["parts"].as<JsonArray>();
        if (!parts) {
            Serial.println("[Voice] No parts in response");
            return false;
        }

        for (JsonObject part : parts) {
            // Check for audio data
            JsonObject inlineData = part["inlineData"].as<JsonObject>();
            if (inlineData) {
                const char* mimeType = inlineData["mimeType"];
                const char* data = inlineData["data"];

                if (data && mimeType) {
                    Serial.printf("[Voice] Audio: %s\n", mimeType);

                    // Parse sample rate (e.g. "audio/pcm;rate=24000")
                    ttsRate_ = 24000;
                    const char* rateStr = strstr(mimeType, "rate=");
                    if (rateStr) ttsRate_ = atoi(rateStr + 5);

                    // Decode base64
                    size_t b64Len = strlen(data);
                    size_t rawLen = 0;
                    mbedtls_base64_decode(nullptr, 0, &rawLen,
                        (const uint8_t*)data, b64Len);

                    if (rawLen > (size_t)TTS_MAX_BYTES) {
                        Serial.printf("[Voice] Audio too large: %d\n", rawLen);
                        return false;
                    }

                    mbedtls_base64_decode(ttsBuf_, TTS_MAX_BYTES, &rawLen,
                        (const uint8_t*)data, b64Len);
                    ttsLen_ = rawLen;
                    Serial.printf("[Voice] Decoded %d bytes @ %dHz\n",
                        ttsLen_, ttsRate_);
                    return true;
                }
            }

            // Log text transcript if present
            const char* text = part["text"];
            if (text) {
                Serial.printf("[Voice] Transcript: %s\n", text);
            }
        }

        Serial.println("[Voice] No audio in response parts");
        return false;
    }

    // --- Playback ---

    void startPlayback() {
        if (ttsLen_ <= 0) return;

        int numSamples = ttsLen_ / 2;  // 16-bit = 2 bytes/sample
        CoreS3.Speaker.setVolume(200);
        CoreS3.Speaker.playRaw((const int16_t*)ttsBuf_, numSamples,
                               ttsRate_, false, 1, 0);
        Serial.printf("[Voice] Playing %d samples @ %dHz (%.1fs)\n",
            numSamples, ttsRate_, (float)numSamples / ttsRate_);
    }

    // --- WAV Header ---

    void writeWavHeader(uint8_t* buf, int dataLen) {
        int fileLen = 44 + dataLen;
        memcpy(buf,      "RIFF", 4);
        *(uint32_t*)(buf +  4) = fileLen - 8;
        memcpy(buf +  8, "WAVE", 4);
        memcpy(buf + 12, "fmt ", 4);
        *(uint32_t*)(buf + 16) = 16;           // fmt chunk size
        *(uint16_t*)(buf + 20) = 1;            // PCM format
        *(uint16_t*)(buf + 22) = 1;            // mono
        *(uint32_t*)(buf + 24) = REC_RATE;     // sample rate
        *(uint32_t*)(buf + 28) = REC_RATE * 2; // byte rate
        *(uint16_t*)(buf + 32) = 2;            // block align
        *(uint16_t*)(buf + 34) = 16;           // bits per sample
        memcpy(buf + 36, "data", 4);
        *(uint32_t*)(buf + 40) = dataLen;
    }
};
