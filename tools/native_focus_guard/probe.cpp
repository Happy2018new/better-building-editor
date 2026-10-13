#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <filesystem>
#include "inject.hpp"

DWORD WINAPI exercise(LPVOID) {
    HINSTANCE instance = GetModuleHandleW(nullptr);
    WNDCLASSW cls{};
    cls.lpfnWndProc = DefWindowProcW;
    cls.hInstance = instance;
    cls.lpszClassName = L"OwnedFocusGuardProbe";
    RegisterClassW(&cls);
    HWND before = GetForegroundWindow();
    HWND window = CreateWindowExW(0, cls.lpszClassName, L"Owned noactivation probe", WS_OVERLAPPEDWINDOW,
        0, 0, 120, 90, nullptr, nullptr, instance, nullptr);
    bool passed = window && (GetWindowLongPtrW(window, GWL_EXSTYLE) & WS_EX_NOACTIVATE);
    if (window) {
        SetWindowLongPtrW(window, GWL_EXSTYLE, 0);
        passed &= (GetWindowLongPtrW(window, GWL_EXSTYLE) & WS_EX_NOACTIVATE) != 0;
        SetWindowLongW(window, GWL_EXSTYLE, 0);
        passed &= (GetWindowLongPtrW(window, GWL_EXSTYLE) & WS_EX_NOACTIVATE) != 0;
        SetWindowLongA(window, GWL_EXSTYLE, 0);
        passed &= (GetWindowLongPtrW(window, GWL_EXSTYLE) & WS_EX_NOACTIVATE) != 0;
        ShowWindow(window, SW_SHOW);
        passed &= GetForegroundWindow() != window;
        passed &= !SetForegroundWindow(window);
        passed &= !BringWindowToTop(window);
        SetActiveWindow(window);
        SetWindowPos(window, HWND_TOP, 0, 0, 120, 90, 0);
        passed &= GetForegroundWindow() != window;
        HWND child = CreateWindowExW(0, L"STATIC", L"Owned child", WS_CHILD | WS_VISIBLE,
            0, 0, 20, 20, window, nullptr, instance, nullptr);
        passed &= child != nullptr;
        for (HWND target : {window, child}) {
            SetLastError(ERROR_SUCCESS);
            passed &= SetFocus(target) == nullptr;
            passed &= GetLastError() == ERROR_ACCESS_DENIED;
            passed &= GetFocus() != target;
            passed &= GetForegroundWindow() != window;
        }
        // Releasing focus does not activate a window and remains available.
        SetLastError(ERROR_SUCCESS);
        SetFocus(nullptr);
        passed &= GetLastError() != ERROR_ACCESS_DENIED;
        DestroyWindow(window);
    }
    // Other applications may legitimately switch during this test.
    std::printf("{\"case\":\"activation_apis\",\"passed\":%s,\"foreground_before\":%llu,\"foreground_after\":%llu}\n",
        passed ? "true" : "false", reinterpret_cast<unsigned long long>(before),
        reinterpret_cast<unsigned long long>(GetForegroundWindow()));
    return passed ? 0 : 1;
}
int wmain(int count, wchar_t** arguments) {
    if (count == 2 && std::wstring(arguments[1]) == L"child") {
        DWORD first = exercise(nullptr);
        HANDLE thread = CreateThread(nullptr, 0, exercise, nullptr, 0, nullptr);
        if (!thread) return 3;
        WaitForSingleObject(thread, 10000);
        DWORD second = 1;
        GetExitCodeThread(thread, &second);
        CloseHandle(thread);
        return first || second;
    }
    wchar_t filename[MAX_PATH];
    GetModuleFileNameW(nullptr, filename, MAX_PATH);
    std::wstring command = L"\"" + std::wstring(filename) + L"\" child";
    STARTUPINFOW startup = {sizeof(startup)};
    startup.dwFlags = STARTF_USESHOWWINDOW;
    startup.wShowWindow = SW_SHOWNOACTIVATE;
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE, CREATE_SUSPENDED,
        nullptr, nullptr, &startup, &process)) return 4;
    try {
        focus_guard::install(process.hProcess, process.dwProcessId, process.dwThreadId,
            std::filesystem::path(filename).parent_path() / L"native_focus_guard.dll");
        ResumeThread(process.hThread);
        if (WaitForSingleObject(process.hProcess, 15000) != WAIT_OBJECT_0) {
            TerminateProcess(process.hProcess, 7);
            WaitForSingleObject(process.hProcess, 5000);
            CloseHandle(process.hThread);
            CloseHandle(process.hProcess);
            return 7;
        }
        DWORD result = 1;
        GetExitCodeProcess(process.hProcess, &result);
        CloseHandle(process.hThread);
        CloseHandle(process.hProcess);
        return result == 0 ? 0 : 5;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "%s\n", error.what());
        TerminateProcess(process.hProcess, 6);
        WaitForSingleObject(process.hProcess, 5000);
        CloseHandle(process.hThread);
        CloseHandle(process.hProcess);
        return 6;
    }
}
