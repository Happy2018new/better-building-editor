param([string]$BuildDirectory = '')
$ErrorActionPreference = 'Stop'
$taskVs = 'D:/Program/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.41.34120'
$taskSdk = 'D:/Windows Kits/10'
$taskSdkVersion = '10.0.22621.0'
$env:INCLUDE = "$taskVs/include;$taskSdk/Include/$taskSdkVersion/ucrt;$taskSdk/Include/$taskSdkVersion/shared;$taskSdk/Include/$taskSdkVersion/um;$taskSdk/Include/$taskSdkVersion/winrt;$taskSdk/Include/$taskSdkVersion/cppwinrt"
$env:LIB = "$taskVs/lib/x64;$taskSdk/Lib/$taskSdkVersion/ucrt/x64;$taskSdk/Lib/$taskSdkVersion/um/x64"
$env:PATH = "$taskVs/bin/Hostx64/x64;$taskSdk/bin/$taskSdkVersion/x64;$env:PATH"
$taskBuild = [IO.Path]::GetFullPath($(if ($BuildDirectory) { $BuildDirectory } else { "$PSScriptRoot/../../.runtime/native_focus_guard" }))
$taskLibrary = [IO.Path]::GetFullPath("$PSScriptRoot/../../.runtime/native_focus_guard/minhook")
New-Item -ItemType Directory -Path $taskBuild -Force | Out-Null
if (!(Test-Path -LiteralPath "$taskLibrary/.git")) { throw 'Clone the pinned MinHook dependency into .runtime/native_focus_guard/minhook first' }
Push-Location -LiteralPath $taskLibrary
try {
    & git checkout --detach c3fcafdc10146beb5919319d0683e44e3c30d537
    if ($LASTEXITCODE -ne 0) { throw 'Cannot select pinned MinHook source' }
} finally { Pop-Location }
Push-Location -LiteralPath $taskBuild
try {
    & cl /nologo /c /O2 /MD "/I$taskLibrary/include" "/I$taskLibrary/src" "$taskLibrary/src/buffer.c" "$taskLibrary/src/hook.c" "$taskLibrary/src/trampoline.c" "$taskLibrary/src/hde/hde64.c"
    if ($LASTEXITCODE -ne 0) { throw 'MinHook compilation failed' }
    & cl /nologo /LD /O2 /MD /EHsc /std:c++20 "/I$taskLibrary/include" "$PSScriptRoot/guard.cpp" buffer.obj hook.obj trampoline.obj hde64.obj user32.lib /link /OUT:native_focus_guard.dll
    if ($LASTEXITCODE -ne 0) { throw 'Focus guard compilation failed' }
    & cl /nologo /O2 /MD /EHsc /std:c++20 "$PSScriptRoot/probe.cpp" user32.lib /link /OUT:native_focus_probe.exe
    if ($LASTEXITCODE -ne 0) { throw 'Focus probe compilation failed' }
    & cl /nologo /O2 /MD /EHsc /std:c++20 "$PSScriptRoot/snapshot_test.cpp" /link /OUT:native_focus_snapshot_test.exe
    if ($LASTEXITCODE -ne 0) { throw 'Module snapshot test compilation failed' }
    & ./native_focus_snapshot_test.exe
    if ($LASTEXITCODE -ne 0) { throw 'Module snapshot retry regression failed' }
} finally { Pop-Location }
