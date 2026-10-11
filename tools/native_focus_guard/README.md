# Owned Background Test Startup

This Windows x64 test helper installs a guard into a newly created, suspended
child process before its main thread resumes. It adds `WS_EX_NOACTIVATE` to
top-level windows and retains it when their extended style changes. The target's
Win32 show/position APIs preserve nonactivation, and explicit foreground,
activation and bring-to-top requests return failure. Other processes are not
hooked. It does not restore focus, synthesize input, resize a game window or
change the installed MCDK executable.

The guard is test instrumentation, not part of the shipped addon. It covers the
listed Win32 APIs; it is not a claim about every possible native activation
mechanism or code executing during DLL initialization before guard installation.
Background WGC capture still independently checks the owned game, session,
fresh frame and foreground identity, with no activation fallback.

## Build And Probe

MinHook v1.3.4 is pinned to
`c3fcafdc10146beb5919319d0683e44e3c30d537`, from
<https://github.com/TsudaKageyu/minhook>. Its source license is retained in the
dependency clone; the project does not vendor its source. On the current host:

```powershell
git clone --no-checkout https://github.com/TsudaKageyu/minhook.git .runtime/native_focus_guard/minhook
& tools/native_focus_guard/build.ps1
& .runtime/native_focus_guard/native_focus_probe.exe
```

The probe installs the guard before resuming its own child, then exercises both
the main thread and a new thread. Each checks window creation, style replacement,
show, explicit foreground, bring-to-top, active-window and position APIs. An
ordinary user switch between other applications is allowed. A timeout closes
only the probe's owned child. `CMakeLists.txt` is the alternate portable build;
the current host script uses MSVC directly because isolated CMake configuration
of this additional dependency failed with `0xC0000409`.

## Isolated MCDK Integration

The launcher patch targets official MCDK v1.6.1,
`cefdfb5ce220e0cc3e9df6d80b2ff87be8b98802`. Copy `inject.hpp` into its
`tools/mcdk/include/mcdk/focus_guard.hpp`, apply `mcdk-v1.6.1.patch`, and build
the isolated clone. Do not overwrite the installed official executable.

```powershell
$env:MCDK_NOACTIVATE_DLL = '<absolute build path>/native_focus_guard.dll'
python -X utf8 .agents/skills/pyreact-debugging/scripts/instances.py start --project '<worktree>' --owner '<owner>' --mcdk '<isolated mcdk.exe>' --game-exe 'D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/Minecraft.Windows.exe'
```

No guard environment variable means ordinary upstream startup. When supplied,
guard failure terminates only the new child before its primary thread resumes.
Both normal stdout and Safaia logging startup paths resume that thread once.
The existing managed session owner/process identity checks remain in force.

## Round Seven Evidence

The isolated two-thread probe passed on 2026-10-11. Three owner-bound NEMC 3.9
instances subsequently reached `ready` and produced fresh, nonblank 1994x1105
WGC frames in the background: snow `db8bd4ce225d4b6d8c29c25e8f9104c2`,
entities `6ae7f141c16a4d6c9ba60e37e6a0c875`, and liquid
`eb105323d4bd4878bef11702d0b1cae1`. The first frame was actually inspected;
its report records another application's PID 42120 before and after capture.
These observations enable background visual tests, not acceptance of the
rendering features being tested. Original probe failures and build artifacts
remain under `.runtime/native_focus_guard` and the isolated MCDK build.

An in-use DLL cannot be overwritten. Use `build.ps1 -BuildDirectory
'<fresh build directory>'` to compile a new revision while existing owned
instances keep their originally loaded version.
