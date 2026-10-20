#pragma once

#ifdef _WIN32
#include <windows.h>
#include <cstdint>
#include <optional>
#include <vector>

namespace MCDevTool::Style::Detail {
    struct CaptureTiming {
        int64_t requestQpc100ns = 0;
        int64_t frameQpc100ns = 0;
        uint32_t clientWidth = 0;
        uint32_t clientHeight = 0;
    };
    std::optional<std::vector<uint8_t>> captureWindowNativePng(HWND hwnd, CaptureTiming& timing);
}
#endif
