#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include "window_capture.h"

#include <cwchar>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace {
    struct Handle {
        HANDLE value = nullptr;
        ~Handle() {
            if (value && value != INVALID_HANDLE_VALUE) CloseHandle(value);
        }
    };

    unsigned long long number(const wchar_t* text) {
        wchar_t* end = nullptr;
        const auto value = std::wcstoull(text, &end, 10);
        if (!text[0] || !end || *end) throw std::runtime_error("Invalid numeric capture identity");
        return value;
    }

    bool matches(HANDLE process, unsigned long long expected) {
        FILETIME created{}, exited{}, kernel{}, user{};
        DWORD state = 0;
        if (!GetProcessTimes(process, &created, &exited, &kernel, &user) ||
            !GetExitCodeProcess(process, &state) || state != STILL_ACTIVE) return false;
        const auto identity = (static_cast<unsigned long long>(created.dwHighDateTime) << 32) | created.dwLowDateTime;
        return identity == expected;
    }
}

int wmain(int argc, wchar_t* argv[]) {
    try {
        if (argc != 5) throw std::runtime_error("Expected HWND PID creation-time output-path");
        const auto hwnd = reinterpret_cast<HWND>(static_cast<uintptr_t>(number(argv[1])));
        const auto rawPid = number(argv[2]);
        if (!rawPid || rawPid > std::numeric_limits<DWORD>::max()) throw std::runtime_error("Invalid game PID");
        const auto pid = static_cast<DWORD>(rawPid);
        const auto identity = number(argv[3]);
        Handle process{OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid)};
        DWORD windowPid = 0;
        GetWindowThreadProcessId(hwnd, &windowPid);
        if (!process.value || !matches(process.value, identity) || !IsWindow(hwnd) || windowPid != pid)
            throw std::runtime_error("Window or game process identity changed");
        if (IsIconic(hwnd)) throw std::runtime_error("Minimized window cannot be captured without restoration");
        MCDevTool::Style::Detail::CaptureTiming timing;
        const auto png = MCDevTool::Style::Detail::captureWindowNativePng(hwnd, timing);
        GetWindowThreadProcessId(hwnd, &windowPid);
        if (!matches(process.value, identity) || !IsWindow(hwnd) || windowPid != pid)
            throw std::runtime_error("Window or game process identity changed during capture");
        if (!png || png->empty()) throw std::runtime_error("WGC did not return a client frame; no activation fallback");
        Handle output{CreateFileW(argv[4], GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr)};
        if (output.value == INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot create a fresh PNG output");
        if (png->size() > std::numeric_limits<DWORD>::max()) throw std::runtime_error("PNG payload exceeds write limit");
        DWORD written = 0;
        if (!WriteFile(output.value, png->data(), static_cast<DWORD>(png->size()), &written, nullptr) ||
            written != png->size()) throw std::runtime_error("Could not write the complete PNG payload");
        std::cout << "{\"ok\":true,\"backend\":\"Windows.Graphics.Capture\",\"native_resolution\":true,"
                  << "\"request_qpc_100ns\":" << timing.requestQpc100ns
                  << ",\"frame_qpc_100ns\":" << timing.frameQpc100ns
                  << ",\"width\":" << timing.clientWidth << ",\"height\":" << timing.clientHeight << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
