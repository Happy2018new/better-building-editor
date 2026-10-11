#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <filesystem>
#include <stdexcept>
#include <string>

namespace focus_guard {
inline DWORD runRemote(HANDLE process, LPTHREAD_START_ROUTINE function, LPVOID argument) {
    HANDLE thread = CreateRemoteThread(process, nullptr, 0, function, argument, 0, nullptr);
    if (!thread) throw std::runtime_error("Focus guard remote thread creation failed");
    DWORD result = 1;
    DWORD wait = WaitForSingleObject(thread, 15000);
    bool finished = wait == WAIT_OBJECT_0 && GetExitCodeThread(thread, &result);
    CloseHandle(thread);
    if (!finished) throw std::runtime_error("Focus guard initialization timed out");
    return result;
}
inline void install(HANDLE process, DWORD pid, DWORD, const std::filesystem::path& path) {
    const auto absolute = std::filesystem::absolute(path);
    if (!std::filesystem::is_regular_file(absolute)) throw std::runtime_error("Focus guard DLL missing");
    HMODULE local = LoadLibraryW(absolute.c_str());
    if (!local) throw std::runtime_error("Focus guard DLL cannot be loaded");
    auto initialize = GetProcAddress(local, "FocusGuardInitialize");
    if (!initialize) throw std::runtime_error("Focus guard initialization export missing");
    const auto dll = absolute.wstring();
    const SIZE_T bytes = (dll.size() + 1) * sizeof(wchar_t);
    LPVOID remote = VirtualAllocEx(process, nullptr, bytes, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    SIZE_T written = 0;
    if (!remote || !WriteProcessMemory(process, remote, dll.c_str(), bytes, &written) || written != bytes)
        throw std::runtime_error("Focus guard DLL path transfer failed");
    auto loader = reinterpret_cast<LPTHREAD_START_ROUTINE>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "LoadLibraryW"));
    DWORD loaded = runRemote(process, loader, remote);
    VirtualFreeEx(process, remote, 0, MEM_RELEASE);
    if (!loaded) throw std::runtime_error("Remote focus guard DLL load failed");
    HANDLE modules = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid);
    if (modules == INVALID_HANDLE_VALUE) throw std::runtime_error("Focus guard module snapshot failed");
    MODULEENTRY32W entry = {sizeof(entry)};
    uintptr_t base = 0;
    if (Module32FirstW(modules, &entry)) {
        do {
            if (_wcsicmp(entry.szModule, absolute.filename().c_str()) == 0) {
                base = reinterpret_cast<uintptr_t>(entry.modBaseAddr);
                break;
            }
        } while (Module32NextW(modules, &entry));
    }
    CloseHandle(modules);
    if (!base) throw std::runtime_error("Focus guard DLL identity not found in owned process");
    auto offset = reinterpret_cast<uintptr_t>(initialize) - reinterpret_cast<uintptr_t>(local);
    if (runRemote(process, reinterpret_cast<LPTHREAD_START_ROUTINE>(base + offset), nullptr) != 0)
        throw std::runtime_error("Target focus guard failed; primary thread remains suspended");
    // Keep the target-only guard loaded for the owned child's lifetime.
}
}
