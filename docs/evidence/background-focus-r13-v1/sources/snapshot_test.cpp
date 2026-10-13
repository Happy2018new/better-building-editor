#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <string>

static unsigned calls = 0;
static unsigned waits = 0;
static unsigned transientFailures = 0;
static DWORD failure = ERROR_BAD_LENGTH;

static HANDLE WINAPI testSnapshot(DWORD flags, DWORD pid) {
    assert(flags == TH32CS_SNAPMODULE && pid == 42);
    ++calls;
    return calls <= transientFailures ? INVALID_HANDLE_VALUE : reinterpret_cast<HANDLE>(1);
}
static DWORD WINAPI testError() { return failure; }
static void WINAPI testSleep(DWORD milliseconds) { assert(milliseconds == 20); ++waits; }

#define CreateToolhelp32Snapshot testSnapshot
#define GetLastError testError
#define Sleep testSleep
#include "inject.hpp"
#undef CreateToolhelp32Snapshot
#undef GetLastError
#undef Sleep

static void reset(unsigned failures, DWORD error) {
    calls = waits = 0;
    transientFailures = failures;
    failure = error;
}

int main() {
    reset(0, ERROR_SUCCESS);
    assert(focus_guard::snapshotModules(42) == reinterpret_cast<HANDLE>(1));
    assert(calls == 1 && waits == 0);
    reset(3, ERROR_BAD_LENGTH);
    assert(focus_guard::snapshotModules(42) == reinterpret_cast<HANDLE>(1));
    assert(calls == 4 && waits == 3);
    reset(50, ERROR_BAD_LENGTH);
    bool rejected = false;
    try { focus_guard::snapshotModules(42); }
    catch (const std::runtime_error& error) {
        rejected = std::string(error.what()).find("Windows error 24") != std::string::npos;
    }
    assert(rejected && calls == 50 && waits == 49);
    reset(50, ERROR_ACCESS_DENIED);
    rejected = false;
    try { focus_guard::snapshotModules(42); }
    catch (const std::runtime_error& error) {
        rejected = std::string(error.what()).find("Windows error 5") != std::string::npos;
    }
    assert(rejected && calls == 1 && waits == 0);
    return 0;
}
