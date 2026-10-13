#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "burst_window_capture.h"

#include <cerrno>
#include <cwchar>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
    uint64_t number(const wchar_t* text) {
        if (!text[0] || text[0] == L'-' || text[0] == L'+' || text[0] < L'0' || text[0] > L'9')
            throw std::runtime_error("Expected an unsigned decimal argument");
        wchar_t* end = nullptr;
        errno = 0;
        const auto result = std::wcstoull(text, &end, 10);
        if (errno == ERANGE || !end || *end) throw std::runtime_error("Invalid or overflowing decimal argument");
        return result;
    }

    uint32_t boundedNumber(const wchar_t* text) {
        const auto result = number(text);
        if (result > std::numeric_limits<uint32_t>::max()) throw std::runtime_error("Argument exceeds 32-bit range");
        return static_cast<uint32_t>(result);
    }
}

int wmain(int argc, wchar_t* argv[]) {
    try {
        if (argc == 2 && std::wcscmp(argv[1], L"--help") == 0) {
            std::cout << "HWND PID creation-time fresh-output-directory duration-ms max-frames max-gap-ms [--allow-user-foreground]\n"
                         "Duration 50..60000 ms; frame cap 1..1800; gap threshold 1..5000 ms.\n"
                         "Captures delivered fresh compositor frames in one persistent WGC session.\n"
                         "Frame cap before duration, time gaps or identity changes are incomplete.\n"
                         "User foreground observation requires explicit opt-in; no activation fallback.\n";
            return 0;
        }
        if (argc != 8 && argc != 9) throw std::runtime_error("Expected HWND PID creation-time fresh-output-directory duration-ms max-frames max-gap-ms [--allow-user-foreground]");
        if (argc == 9 && std::wcscmp(argv[8], L"--allow-user-foreground") != 0)
            throw std::runtime_error("Unknown foreground policy argument");
        NativeWgcBurst::WindowBinding binding{number(argv[1]), boundedNumber(argv[2]), number(argv[3])};
        if (!binding.hwnd || binding.hwnd > std::numeric_limits<uintptr_t>::max() || !binding.pid || !binding.creationTime)
            throw std::runtime_error("A bound HWND, owned PID and process creation time are required");
        NativeWgcBurst::CaptureOptions options{boundedNumber(argv[5]), boundedNumber(argv[6]), boundedNumber(argv[7]), 1000};
        options.allowUserForeground = argc == 9;
        if (!NativeWgcBurst::validOptions(options)) throw std::runtime_error("Burst duration, frame cap or gap threshold is outside its supported range");
        const std::filesystem::path directory = std::filesystem::absolute(argv[4]);
        if (!CreateDirectoryW(directory.c_str(), nullptr)) throw std::runtime_error("Choose a fresh output directory with an existing parent");
        const auto result = NativeWgcBurst::captureWindowBurstPng(binding, options, directory);
        NativeWgcBurst::writeFreshFile(directory / L"manifest.json",
            reinterpret_cast<const uint8_t*>(result.manifestJson.data()), result.manifestJson.size());
        std::cout << result.manifestJson << '\n';
        return result.captureValid && result.temporalComplete ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
