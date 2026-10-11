#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <MinHook.h>

namespace {
decltype(&CreateWindowExW) createW;
decltype(&CreateWindowExA) createA;
decltype(&ShowWindow) show;
decltype(&ShowWindowAsync) showAsync;
decltype(&SetWindowPos) position;
decltype(&SetWindowLongPtrW) longW;
decltype(&SetWindowLongPtrA) longA;

DWORD nonactivatingStyle(DWORD extended, DWORD style) {
    return (style & WS_CHILD) ? extended : extended | WS_EX_NOACTIVATE;
}
int nonactivatingShow(int command) {
    if (command == SW_HIDE || command == SW_SHOWMINNOACTIVE || command == SW_SHOWNOACTIVATE)
        return command;
    return SW_SHOWNOACTIVATE;
}
HWND WINAPI guardedCreateW(DWORD ex, LPCWSTR cls, LPCWSTR title, DWORD style,
    int x, int y, int width, int height, HWND parent, HMENU menu, HINSTANCE instance, LPVOID param) {
    return createW(nonactivatingStyle(ex, style), cls, title, style,
        x, y, width, height, parent, menu, instance, param);
}
HWND WINAPI guardedCreateA(DWORD ex, LPCSTR cls, LPCSTR title, DWORD style,
    int x, int y, int width, int height, HWND parent, HMENU menu, HINSTANCE instance, LPVOID param) {
    return createA(nonactivatingStyle(ex, style), cls, title, style,
        x, y, width, height, parent, menu, instance, param);
}
BOOL WINAPI guardedShow(HWND window, int command) { return show(window, nonactivatingShow(command)); }
BOOL WINAPI guardedShowAsync(HWND window, int command) { return showAsync(window, nonactivatingShow(command)); }
BOOL WINAPI guardedPosition(HWND window, HWND after, int x, int y, int width, int height, UINT flags) {
    return position(window, after, x, y, width, height, flags | SWP_NOACTIVATE);
}
LONG_PTR WINAPI guardedLongW(HWND window, int index, LONG_PTR value) {
    if (index == GWL_EXSTYLE && !(GetWindowLongPtrW(window, GWL_STYLE) & WS_CHILD)) value |= WS_EX_NOACTIVATE;
    return longW(window, index, value);
}
LONG_PTR WINAPI guardedLongA(HWND window, int index, LONG_PTR value) {
    if (index == GWL_EXSTYLE && !(GetWindowLongPtrA(window, GWL_STYLE) & WS_CHILD)) value |= WS_EX_NOACTIVATE;
    return longA(window, index, value);
}
BOOL WINAPI rejectForeground(HWND) { return FALSE; }
BOOL WINAPI rejectBring(HWND) { return FALSE; }
void WINAPI rejectSwitch(HWND, BOOL) {}
HWND WINAPI rejectActivate(HWND) { return nullptr; }

bool attach(LPCSTR name, LPVOID replacement, LPVOID* original = nullptr) {
    return MH_CreateHookApi(L"user32", name, replacement, original) == MH_OK;
}
}

// Installed only into the owned process, before its primary thread resumes.
extern "C" __declspec(dllexport) DWORD WINAPI FocusGuardInitialize(LPVOID) {
    if (!LoadLibraryW(L"user32.dll") || MH_Initialize() != MH_OK) return 1;
    bool ok = attach("CreateWindowExW", reinterpret_cast<LPVOID>(guardedCreateW), reinterpret_cast<LPVOID*>(&createW))
        && attach("CreateWindowExA", reinterpret_cast<LPVOID>(guardedCreateA), reinterpret_cast<LPVOID*>(&createA))
        && attach("ShowWindow", reinterpret_cast<LPVOID>(guardedShow), reinterpret_cast<LPVOID*>(&show))
        && attach("ShowWindowAsync", reinterpret_cast<LPVOID>(guardedShowAsync), reinterpret_cast<LPVOID*>(&showAsync))
        && attach("SetWindowPos", reinterpret_cast<LPVOID>(guardedPosition), reinterpret_cast<LPVOID*>(&position))
        && attach("SetWindowLongPtrW", reinterpret_cast<LPVOID>(guardedLongW), reinterpret_cast<LPVOID*>(&longW))
        && attach("SetWindowLongPtrA", reinterpret_cast<LPVOID>(guardedLongA), reinterpret_cast<LPVOID*>(&longA))
        && attach("SetForegroundWindow", reinterpret_cast<LPVOID>(rejectForeground))
        && attach("BringWindowToTop", reinterpret_cast<LPVOID>(rejectBring))
        && attach("SwitchToThisWindow", reinterpret_cast<LPVOID>(rejectSwitch))
        && attach("SetActiveWindow", reinterpret_cast<LPVOID>(rejectActivate));
    if (!ok || MH_EnableHook(MH_ALL_HOOKS) != MH_OK) {
        MH_Uninitialize();
        return 2;
    }
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(instance);
    return TRUE;
}
