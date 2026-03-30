#pragma once
#include <cstdint>

enum class Expression : uint8_t {
    NORMAL,
    HAPPY,
    SAD,
    SURPRISED,
    SLEEPY,
    LOVE,
    COUNT  // sentinel
};
