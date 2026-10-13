"""Launch and route independent MCDK projects; never select a game by window size."""
# Local redirected-AppData world preparation fix: see docs/PYREACT_UPSTREAM.md.
import argparse
import copy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time
import uuid

from _session import (file_lock, load_session, process_identity, registry_dir,
                      terminate_owned, write_json)
from mcdk import Client, return_value
from setup_mcdk import resolve_game, resolve_mcdk
from _window import (background_guard_state, foreground_snapshot, validate_foreground_snapshot,
                     foreground_policy_satisfied, user_foreground_allowed)

SCRIPTS = Path(__file__).resolve().parent
RUNNABLE = {"mcdk.py", "get_ui_tree.py", "query_tree.py", "print_ui_tree.py",
            "simulate.py", "simulate_and_diff.py", "navigator.py", "expect.py",
            "diff_ui_tree.py", "click_tour.py", "resize_window.py",
            "diagnostics.py", "run_case.py"}


def absolute(project, value):
    return str((project / value).resolve())


def prepare_config(project, config, game_exe, port, instance_id, preset=None):
    result = copy.deepcopy(config)
    exe = game_exe or result.get("game_executable_path")
    if not exe or not (project / exe).is_file():
        raise ValueError("Set a valid game_executable_path or pass --game-exe (no interactive selection)")
    result["game_executable_path"] = absolute(project, exe)
    directories = []
    for item in result.get("included_mod_dirs", ["./"]):
        if isinstance(item, str):
            directories.append(absolute(project, item))
        else:
            item = dict(item)
            item["path"] = absolute(project, item["path"])
            directories.append(item)
    result["included_mod_dirs"] = directories
    source = result.get("world_source_path", "auto")
    if source == "auto":
        source = str(project) if (project / "level.dat").is_file() else ""
    result["world_source_path"] = absolute(project, source) if source else ""
    skin = result.get("skin_info")
    if skin and skin.get("skin"):
        skin["skin"] = absolute(project, skin["skin"])
    result.update(include_debug_mod=True, auto_join_game=True, reset_world=False,
                  world_folder_name="PYR_" + instance_id,
                  world_name="Pyreact " + instance_id[:8])
    result["mcp_server_config"] = {"enabled": True, "server_ip": "127.0.0.1", "server_port": port}
    # IDE debugger ports are opt-in and cannot be inherited across instances.
    result["modpc_debugger"] = {"enabled": False}
    result["ptvsd_debugger"] = {"enabled": False}
    if preset == "ui":
        result.update(world_seed=0, world_type=2, game_mode=1,
                      do_weather_cycle=False, do_daylight_cycle=False,
                      auto_hot_reload_mods=config.get('auto_hot_reload_mods', True),
                      auto_hot_reload_ui=config.get('auto_hot_reload_ui', True))
    return result


def clean_environment(appdata, noactivate=None):
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("MCDEV_")
           and k.upper() not in ("PYREACT_MODULE", "MCDK_NOACTIVATE_DLL")}
    # Scope the data root only to this child and its game; never change user env.
    env["APPDATA"] = str(appdata)
    if noactivate:
        env['MCDK_NOACTIVATE_DLL'] = noactivate['dll']['path']
    return env


def _verified_binary(path, expected, label):
    if not isinstance(expected, str) or len(expected) != 64 or any(
            char not in '0123456789abcdefABCDEF' for char in expected):
        raise ValueError(label + ' needs an explicit SHA256')
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError(label + ' is not a regular file')
    source = path.read_bytes()
    actual = hashlib.sha256(source).hexdigest()
    if actual != expected.lower():
        raise ValueError(label + ' SHA256 mismatch')
    if len(source) < 64 or source[:2] != b'MZ':
        raise ValueError(label + ' must be a Windows x64 PE binary')
    offset = int.from_bytes(source[60:64], 'little')
    if source[offset:offset + 6] != b'PE\0\0\x64\x86':
        raise ValueError(label + ' must be a Windows x64 PE binary')
    return {'path': str(path), 'sha256': actual}, source


def noactivate_contract(args, executable):
    dll = getattr(args, 'noactivate_dll', None)
    dll_hash = getattr(args, 'noactivate_sha256', None)
    mcdk_hash = getattr(args, 'noactivate_mcdk_sha256', None)
    if not any((dll, dll_hash, mcdk_hash)):
        return None
    if not all((dll, dll_hash, mcdk_hash)) or not args.mcdk:
        raise ValueError('Noactivation requires --noactivate-dll, both SHA256 options and explicit --mcdk')
    guard, source = _verified_binary(dll, dll_hash, 'Noactivation DLL')
    if b'FocusGuardInitialize\0' not in source:
        raise ValueError('Noactivation DLL lacks the guard initialization export')
    mcdk, source = _verified_binary(executable, mcdk_hash, 'Patched MCDK')
    if ('MCDK_NOACTIVATE_DLL'.encode('utf-16le') not in source
            or b'Focus guard DLL identity not found in owned process' not in source):
        raise ValueError('Patched MCDK lacks the suspended-child focus guard contract')
    return {'schema': 1, 'requested': True, 'dll': guard, 'mcdk': mcdk,
            'user_foreground_allowed': user_foreground_allowed(), 'agent_activation_allowed': False,
            'patch': 'native_focus_guard/mcdk-v1.6.1.patch'}


def finish_start(data):
    data['foreground_after'] = foreground_snapshot()
    before = data.get('foreground_before', {})
    data['foreground_before_still_valid'] = validate_foreground_snapshot(before)
    data['foreground_unchanged'] = all(data['foreground_after'].get(key) == before.get(key)
                                       for key in ('hwnd', 'pid', 'identity'))
    write_json(data['session_file'], data)
    return data


def discover(mcdk_pid, port, timeout=20):
    command = (
        "$ErrorActionPreference='Stop'; "
        "$children=@(Get-CimInstance Win32_Process -Filter "
        "'ParentProcessId=%d' | Where-Object Name -eq 'Minecraft.Windows.exe' | "
        "Select-Object -ExpandProperty ProcessId); "
        "$listeners=@(Get-NetTCPConnection -State Listen -LocalPort %d "
        "-ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); "
        "@{children=$children;listeners=$listeners}|ConvertTo-Json -Compress"
    ) % (mcdk_pid, port)
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                            capture_output=True, timeout=timeout,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace"))
    return json.loads(result.stdout.decode("utf-8-sig"))


def tcp_listener_owners(raw, port):
    if len(raw) < 4:
        raise ValueError('Truncated IPv4 TCP table')
    count = struct.unpack_from('<I', raw)[0]
    if count > (len(raw) - 4) // 24:
        raise ValueError('Truncated IPv4 TCP rows')
    owners = set()
    for index in range(count):
        state, address, local_port, _, _, pid = struct.unpack_from('<6I', raw, 4 + index * 24)
        # The MCP URL is explicitly IPv4 loopback; only loopback or wildcard listeners serve it.
        if (state == 2 and address in (0, 0x0100007f) and
                socket.ntohs(local_port & 0xffff) == port):
            owners.add(pid)
    return sorted(owners)


def listener_owners(port):
    from ctypes import wintypes
    library = ctypes.WinDLL('iphlpapi', use_last_error=True)
    query = library.GetExtendedTcpTable
    query.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
                      wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
    query.restype = wintypes.DWORD
    size = wintypes.DWORD()
    result = query(None, ctypes.byref(size), True, socket.AF_INET, 3, 0)
    if result not in (0, 122):
        raise OSError(result, 'GetExtendedTcpTable size query failed')
    for _ in range(3):
        buffer = ctypes.create_string_buffer(size.value)
        result = query(buffer, ctypes.byref(size), True, socket.AF_INET, 3, 0)
        if result == 0:
            return tcp_listener_owners(buffer.raw[:size.value], port)
        if result != 122:
            raise OSError(result, 'GetExtendedTcpTable listener query failed')
    raise RuntimeError('IPv4 listener table changed during all bounded reads')


class ReadinessOwnershipError(RuntimeError):
    pass


def verify_startup_endpoint(data):
    for kind in ('mcdk', 'game'):
        if process_identity(data[kind + '_pid']) != data[kind + '_identity']:
            raise ReadinessOwnershipError('Owned %s creation identity changed; refusing to bind' % kind)
    owners = listener_owners(data['port'])
    for kind in ('mcdk', 'game'):
        if process_identity(data[kind + '_pid']) != data[kind + '_identity']:
            raise ReadinessOwnershipError('Owned %s changed during listener check; refusing to bind' % kind)
    if owners and owners != [data['mcdk_pid']]:
        raise ReadinessOwnershipError('MCP loopback port belongs to another process; refusing to bind')
    if not owners:
        raise RuntimeError('Owned MCP loopback listener is not available')


class ReadinessClient(Client):
    def __init__(self, data, deadline):
        self.readiness_data = data
        self.readiness_deadline = deadline
        self.readiness_method = None
        super().__init__(data['mcp_url'], timeout=3, bind_session=False)

    def _post(self, method, params=None, notification=False):
        self.readiness_method = method
        verify_startup_endpoint(self.readiness_data)
        remaining = self.readiness_deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Readiness deadline reached before ' + method)
        self.timeout = min(3, remaining)
        result = super()._post(method, params, notification)
        verify_startup_endpoint(self.readiness_data)
        if time.monotonic() >= self.readiness_deadline:
            raise TimeoutError('Readiness response arrived after deadline: ' + method)
        return result

    def close(self):
        remaining = self.readiness_deadline - time.monotonic()
        if remaining <= 0:
            self.session = None
            return
        try:
            verify_startup_endpoint(self.readiness_data)
        except Exception:
            self.session = None
            return
        remaining = self.readiness_deadline - time.monotonic()
        if remaining <= 0:
            self.session = None
            return
        self.timeout = min(3, remaining)
        super().close()


def native_worlds_dir():
    # Minecraft uses the Windows known folder, even when APPDATA is overridden.
    buffer = ctypes.create_unicode_buffer(32768)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 26, None, 0, buffer):
        raise OSError("Cannot locate the Windows roaming data directory")
    return Path(buffer.value) / "MinecraftPE_Netease" / "minecraftWorlds"


def junction(link, target):
    link, target = Path(link), Path(target).resolve(strict=True)
    if link.exists() or link.is_symlink() or link.is_junction():
        raise FileExistsError("Refusing to replace existing path: " + str(link))
    link.parent.mkdir(parents=True, exist_ok=True)
    # Literal, single-quoted PowerShell paths; never pass filesystem work to cmd.
    quote = lambda value: "'" + str(value).replace("'", "''") + "'"
    command = "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path %s -Target %s | Out-Null" % (quote(link), quote(target))
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], check=True,
                   capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)


def prepare_world(executable, root, appdata, prepared):
    """Let MCDK generate the world before exposing world-local pack junctions."""
    bootstrap = copy.deepcopy(prepared)
    # MCDK 1.6 has no prepare-only command. where.exe exits immediately without
    # touching game data; all world/debug-pack generation still belongs to MCDK.
    bootstrap["game_executable_path"] = str(Path(os.environ["SystemRoot"]) / "System32" / "where.exe")
    bootstrap["mcp_server_config"]["enabled"] = False
    bootstrap["auto_join_game"] = False
    write_json(root / ".mcdev.json", bootstrap)
    with (root / "prepare.log").open("wb") as log:
        subprocess.run([executable], cwd=str(root), env=clean_environment(appdata),
                       stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                       timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    world = appdata / "MinecraftPE_Netease" / "minecraftWorlds" / prepared["world_folder_name"]
    if not (world / "level.dat").is_file():
        raise RuntimeError("MCDK world preparation failed; read " + str(root / "prepare.log"))
    exposed = native_worlds_dir() / prepared["world_folder_name"]
    if exposed.exists() or exposed.is_junction():
        raise FileExistsError("World already exists: " + str(exposed))
    exposed.parent.mkdir(parents=True, exist_ok=True)
    # Local fix: relocate before adding junctions. Across redirected AppData
    # volumes shutil.move falls back to copying, which follows those junctions
    # and can copy entire packs into paths beyond the Win32 path limit.
    shutil.move(str(world), str(exposed))
    junction(world, exposed)
    for kind in ("behavior_packs", "resource_packs"):
        container = exposed / kind
        container.mkdir(exist_ok=True)
        # Preserve packs deployed from a map project. Addon/debug packs live in
        # MCDK's private pack root and are recreated there during normal launch.
        runtime = appdata / "MinecraftPE_Netease" / "games" / "com.netease" / kind
        for pack in runtime.iterdir() if runtime.exists() else []:
            if not pack.is_dir():
                continue
            junction(container / ("mcdk_" + pack.name), pack)
    write_json(root / ".mcdev.json", prepared)
    return exposed, world


def create_probe(root, instance_id, token):
    pack = root / "session_probe"
    module = "PyreactSession_" + instance_id
    source = pack / module
    source.mkdir(parents=True)
    write_json(pack / "manifest.json", {
        "format_version": 2,
        "header": {"name": module, "description": "Managed instance identity",
                   "uuid": str(uuid.uuid4()), "version": [1, 0, 0], "min_engine_version": [1, 18, 0]},
        "modules": [{"type": "data", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}]})
    (source / "__init__.py").write_text("", encoding="ascii")
    (source / "modMain.py").write_text(
        "from mod.common.mod import Mod\nimport sys\n"
        "@Mod.Binding(name=%r, version='1.0.0')\n"
        "class SessionProbe(object):\n"
        "    @Mod.InitClient()\n    def client(self):\n        sys._pyreact_mcdk_session = %r\n"
        "    @Mod.InitServer()\n    def server(self):\n        sys._pyreact_mcdk_session = %r\n" %
        (module, token, token), encoding="ascii")
    return str(pack)


def start(args):
    if os.name != "nt":
        raise RuntimeError("Managed instances currently require Windows")
    if sys.version_info < (3, 12):
        raise RuntimeError("Managed instances require Python 3.12 or newer")
    project = Path(args.project).resolve(strict=True)
    source_config = project / ".mcdev.json"
    config = json.loads(source_config.read_text(encoding="utf-8-sig")) if source_config.exists() else {}
    executable = resolve_mcdk(args.mcdk)
    if not executable:
        raise FileNotFoundError("Run setup_mcdk.py --install, or pass --mcdk / MCDK_EXE")
    noactivate = noactivate_contract(args, executable)
    game_exe = resolve_game(project, config, args.game_exe)
    instance_id = uuid.uuid4().hex
    root = registry_dir() / instance_id
    appdata = root / "appdata"
    appdata.mkdir(parents=True)
    session_file = root / "session.json"
    data = {"schema": 1, "id": instance_id, "name": args.name or project.name,
            "owner": args.owner, "project": str(project), "session_file": str(session_file),
            "artifacts": str(root / "artifacts"), "appdata": str(appdata),
            "log": str(root / "mcdk.log"), "token": uuid.uuid4().hex,
            "state": "starting", "created_at": time.time(), "ready": False}
    if noactivate:
        data['noactivation'] = noactivate
    with file_lock(registry_dir() / "launch.lock"):
        with socket.socket() as reservation:
            reservation.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            reservation.bind(("127.0.0.1", args.port or 0))
            port = reservation.getsockname()[1]
            prepared = prepare_config(project, config, game_exe, port, instance_id, args.preset)
            prepared["included_mod_dirs"].append(create_probe(root, instance_id, data["token"]))
            write_json(root / ".mcdev.json", prepared)
            data.update(mcp_url="http://127.0.0.1:%d/mcp" % port, port=port,
                        world=prepared["world_folder_name"], game_executable=prepared["game_executable_path"])
            write_json(session_file, data)
            try:
                world, exposed = prepare_world(executable, root, appdata, prepared)
                data.update(world_path=str(world), world_link=str(exposed))
            except Exception as exc:
                data.update(state="failed", error=str(exc))
                write_json(session_file, data)
                return finish_start(data)
        data['foreground_before'] = foreground_snapshot()
        if (noactivate and not user_foreground_allowed() and
                data['foreground_before']['process'].lower().startswith('minecraft')):
            data.update(state='failed', error='Noactivation startup requires a non-Minecraft foreground')
            return finish_start(data)
        try:
            # Check approved binary bytes again after world preparation, before spawn.
            if noactivate:
                noactivate = noactivate_contract(args, executable)
            with Path(data["log"]).open("wb") as log:
                process = subprocess.Popen([executable], cwd=str(root), env=clean_environment(appdata, noactivate),
                                           stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
        except (OSError, ValueError) as exc:
            data.update(state='failed', error=str(exc))
            return finish_start(data)
        data.update(mcdk_pid=process.pid, mcdk_identity=process_identity(process.pid))
        write_json(session_file, data)
    deadline = time.monotonic() + args.wait
    last_error = "World IPC not ready"
    discovery_attempt = 0
    fatal_error = False
    while time.monotonic() < deadline:
        try:
            if process.poll() is not None:
                raise RuntimeError("MCDK exited with code %s; read %s" % (process.returncode, data["log"]))
            if process_identity(process.pid) != data['mcdk_identity']:
                raise ReadinessOwnershipError('Owned MCDK creation identity changed; refusing to bind')
            if not data.get('game_pid'):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                discovery_timeout = min(20, remaining)
                discovery_started = time.monotonic()
                discovery_attempt += 1
                try:
                    observed = discover(process.pid, port, timeout=discovery_timeout)
                except Exception as exc:
                    data['last_discovery_error'] = {'attempt': discovery_attempt,
                        'error_type': type(exc).__name__, 'error': str(exc)}
                    if isinstance(exc, subprocess.TimeoutExpired):
                        data.setdefault('discovery_timeouts', []).append({
                            'attempt': discovery_attempt, 'command': exc.cmd,
                            'timeout_seconds': exc.timeout,
                            'elapsed_seconds': round(time.monotonic() - discovery_started, 3),
                            'error': str(exc),
                            'stdout': exc.output.decode('utf-8', 'replace') if isinstance(exc.output, bytes) else exc.output,
                            'stderr': exc.stderr.decode('utf-8', 'replace') if isinstance(exc.stderr, bytes) else exc.stderr})
                    write_json(session_file, data)
                    raise
                data.setdefault('discovery_observations', []).append({'attempt': discovery_attempt,
                    'elapsed_seconds': round(time.monotonic() - discovery_started, 3),
                    'children': observed['children'], 'listeners': observed['listeners']})
                if process_identity(process.pid) != data['mcdk_identity']:
                    raise ReadinessOwnershipError('Owned MCDK changed during discovery; refusing to bind')
                if time.monotonic() >= deadline:
                    break
                if observed["listeners"] and observed["listeners"] != [process.pid]:
                    raise ReadinessOwnershipError("MCP port belongs to another process; refusing to bind")
                if len(observed["children"]) != 1 or observed["listeners"] != [process.pid]:
                    time.sleep(min(.5, max(0, deadline - time.monotonic())))
                    continue
                game_pid = observed["children"][0]
                identity = process_identity(game_pid)
                if not identity:
                    continue
                data.update(game_pid=game_pid, game_identity=identity)
                data['startup_endpoint_discovered'] = True
            game_pid, identity = data['game_pid'], data['game_identity']
            verify_startup_endpoint(data)
            if noactivate:
                guard = background_guard_state(game_pid, Path(data['game_executable']).name)
                data['noactivation'].update(guard)
                if (not foreground_policy_satisfied(guard, game_pid) or
                        guard['windows'] and not guard['window_noactivate']):
                    data.update(state='failed', error='Owned game violated the noactivation window contract')
                    terminate_owned(game_pid, identity)
                    terminate_owned(data['mcdk_pid'], data['mcdk_identity'])
                    return finish_start(data)
                if not guard['windows']:
                    time.sleep(min(.5, max(0, deadline - time.monotonic())))
                    continue
            write_json(session_file, data)
            sdk_phase, client = 'client_initialize', None
            try:
                client = ReadinessClient(data, deadline)
                with client:
                    sdk_phase = 'client_process_environment'
                    info = return_value(client.call("execute_code", {
                        "code": "import os\n_result = {'pid':os.getpid(), 'appdata':os.environ.get('APPDATA')}",
                        "is_client": True, "direct_return": True}))
                    if info != {"pid": game_pid, "appdata": str(appdata)}:
                        raise RuntimeError("Game identity/data environment mismatch: " + repr(info))
                    code = "import sys\n_result = getattr(sys, '_pyreact_mcdk_session', None)"
                    for side in (True, False):
                        sdk_phase = 'client_session_marker' if side else 'server_session_marker'
                        if return_value(client.call("execute_code", {"code": code, "is_client": side,
                                                                      "direct_return": True})) != data["token"]:
                            raise RuntimeError("Could not bind game runtime")
            except Exception as exc:
                error = {'phase': sdk_phase, 'method': getattr(client, 'readiness_method', None),
                         'error_type': type(exc).__name__, 'error': str(exc)}
                if isinstance(getattr(exc, 'error', None), dict):
                    error['raw_error'] = exc.error
                data['last_sdk_error'] = error
                data.setdefault('sdk_errors', []).append(error)
                write_json(session_file, data)
                raise
            verify_startup_endpoint(data)
            if noactivate:
                guard = background_guard_state(game_pid, Path(data['game_executable']).name)
                data['noactivation'].update(guard)
                if not foreground_policy_satisfied(guard, game_pid) or not guard['window_noactivate']:
                    data.update(state='failed', ready=False,
                                error='Owned game violated the noactivation contract before readiness')
                    terminate_owned(game_pid, identity)
                    terminate_owned(data['mcdk_pid'], data['mcdk_identity'])
                    return finish_start(data)
            if time.monotonic() >= deadline:
                raise TimeoutError('Readiness deadline reached before acceptance')
            data.update(state="ready", ready=True)
            write_json(session_file, data)
            return finish_start(data)
        except Exception as exc:
            last_error = str(exc)
            if isinstance(exc, ReadinessOwnershipError) or process.poll() is not None or "refusing to bind" in last_error:
                fatal_error = True
                break
            time.sleep(min(.5, max(0, deadline - time.monotonic())))
    if not fatal_error and data.get('last_sdk_error'):
        last_error = data['last_sdk_error']['error']
    data['readiness_deadline_reached'] = time.monotonic() >= deadline
    data.update(state="failed", error=last_error)
    write_json(session_file, data)
    # Keep identities/evidence so a failed launch remains inspectable and stoppable.
    return finish_start(data)


def stop(data, force=False):
    with file_lock(Path(data["session_file"]).with_suffix(".lock")):
        if data.get("game_pid"):
            current = process_identity(data["game_pid"])
            if current and current != data["game_identity"]:
                raise RuntimeError("Game PID was reused; refusing to stop")
            if current:
                if force:
                    terminate_owned(data["game_pid"], data["game_identity"])
                else:
                    from _window import _list_windows, user32
                    from ctypes import wintypes
                    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
                    for window in _list_windows():
                        if window["pid"] == data["game_pid"]:
                            user32.PostMessageW(window["hwnd"], 0x0010, 0, 0)
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline and process_identity(data["game_pid"]) == current:
                        time.sleep(.2)
                    if process_identity(data["game_pid"]) == current:
                        raise RuntimeError("Game has not closed; inspect it or explicitly use stop --force")
        if data.get("mcdk_pid"):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and process_identity(data["mcdk_pid"]) == data["mcdk_identity"]:
                time.sleep(.2)
            if force:
                terminate_owned(data["mcdk_pid"], data["mcdk_identity"])
            elif process_identity(data["mcdk_pid"]) == data["mcdk_identity"]:
                raise RuntimeError("MCDK cleanup still running; inspect or use stop --force")
        data.update(state="stopped", ready=False)
        link = Path(data["world_link"]) if data.get("world_link") else None
        if link and link.is_junction() and link.resolve() == Path(data["world_path"]).resolve():
            # rmdir removes only the junction, retaining the private world/evidence.
            link.rmdir()
        write_json(data["session_file"], data)
        return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    launch = sub.add_parser("start")
    launch.add_argument("--project", required=True)
    launch.add_argument("--owner", required=True, help="agent/task identifier; carried by every command")
    launch.add_argument("--name")
    launch.add_argument("--mcdk", help="existing MCDK; defaults to MCDK_EXE, managed installation, then PATH")
    launch.add_argument('--noactivate-dll', help='Approved native focus guard DLL for patched MCDK')
    launch.add_argument('--noactivate-sha256', help='Expected SHA256 of the noactivation DLL')
    launch.add_argument('--noactivate-mcdk-sha256', help='Expected SHA256 of the explicitly supplied patched MCDK')
    launch.add_argument("--game-exe")
    launch.add_argument("--port", type=int)
    launch.add_argument("--wait", type=float, default=60)
    launch.add_argument("--preset", choices=["ui"])
    sub.add_parser("list")
    for action in ("status", "stop", "exec"):
        command = sub.add_parser(action)
        command.add_argument("--session", required=True)
        command.add_argument("--owner", required=True)
        if action == "stop":
            command.add_argument("--force", action="store_true")
        if action == "exec":
            command.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == "start":
            if not 1 <= args.wait <= 180:
                raise ValueError("--wait must be 1..180 seconds")
            result = start(args)
        elif args.action == "list":
            result = []
            for path in registry_dir().glob("*/session.json"):
                entry = json.loads(path.read_text(encoding="utf-8"))
                result.append({k: entry.get(k) for k in ("id", "name", "owner", "project", "session_file", "state", "mcp_url")})
        else:
            result = load_session(args.session, args.owner, live=args.action == "exec")
            if args.action == "stop":
                result = stop(result, args.force)
            elif args.action == "status":
                result = dict(result)
                result["process_alive"] = {k: bool(result.get(k + "_identity")) and
                    process_identity(result[k + "_pid"]) == result[k + "_identity"] for k in ("mcdk", "game")}
                result.pop("token", None)
            else:
                command = args.command
                if command and command[0] == "--":
                    command = command[1:]
                if not command or command[0] not in RUNNABLE:
                    raise ValueError("Choose a skill script: " + ", ".join(sorted(RUNNABLE)))
                env = os.environ.copy()
                env.update(MCDEV_SESSION_FILE=result["session_file"], MCDEV_OWNER=args.owner,
                           MCDEV_MCP_URL=result["mcp_url"])
                return subprocess.call([sys.executable, str(SCRIPTS / command[0])] + command[1:], env=env)
        if isinstance(result, dict):
            result = {k: v for k, v in result.items() if k != "token"}
        sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 1 if isinstance(result, dict) and result.get("state") == "failed" else 0
    except Exception as exc:
        print("[instances] %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
