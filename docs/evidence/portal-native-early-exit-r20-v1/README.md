# Unrequested portal instance exit before coordinate readback, R20

The isolated portal-r20-native-v5 clone became ready at 2026-10-16 00:55:43
Asia/Shanghai. Its game PID 44560 and MCDK PID 35760 were absent by the first
incident inspection. No business probe, WGC, stop, force, activation or input
had been performed. The project still matched its frozen launch SHA map. This
is an unexpected exit after readiness, not a successful renderer test.

The original ready session snapshot and raw MCDK log are retained privately in
the ignored runtime area. Only their SHA values and a bounded native log excerpt
are published here; the full session can contain routing credentials. The ready
summary contains exact process identities. After both identities were confirmed
absent, normal stop finalized session metadata; stopped does not imply that the
preceding unrequested exit was normal. No game/MCDK exit code was recovered.

The v5 native log contains a rollover WindowsError 32, a petSysClient toast
AttributeError at 00:56:10, and MCP shutdown lines at 00:56:40. Those errors do
not establish the exit cause. The root-owned watcher also observed the exact
DisabledSkinScreenController::onEntered @47 assertion on this same game identity
at 00:56:03.880626. It sent background WM_COMMAND IDIGNORE and confirmed dismissal
at 00:56:04.012730 with agent_activation=false. This corrects the initial lack
of a known assertion observation; absence from the MCDK log did not establish
that no dialog occurred. The raw recovery receipt and aligned timeline are
included. Dismissal, the subsequent pet error and exit are correlated in time;
none has been established as the exit cause. The watcher was not changed.

The successful v4 instance had the same native
pet toast exception at 23:48:50, survived through its 23:58 acquisition and was
stopped normally at 00:00:20. That counterexample is included separately.

Read-only inspection of the approved local MCDK build found these paths:

- game_process.cpp waits on its owned game process handle, gets its exit code,
  notifies the host bridge, and only then invokes mcpServer.stop(). The three
  MCP shutdown messages therefore do not establish a launcher-initiated exit.
- The Safaia receiver is constructed with the owned game PID and restricts
  discovery by targetProcessId. Instance stdout/stderr go to a per-session log,
  and the launcher runs with a per-session working directory and CREATE_NO_WINDOW.
- In the reviewed launch code, TerminateProcess occurs only in startup guard,
  Safaia startup or ResumeThread failure paths. No global game-close broadcast
  was found in the reviewed MCDK tree. The window-input console handler releases
  held input and returns FALSE; it is only installed after retained input use.
- MCP server destructors can also invoke stop while unwinding. These source
  observations narrow the investigation but cannot prove the OS exit cause.

Reviewed local sources and build metadata are preserved with SHA values. Their
paths and source/object/executable timestamps agree with the approved build;
this is not a reproducible-build attestation. The package includes compile
receipts for the coordinate shaders but no successful coordinate readback and
no new appearance, lifecycle, UI, missing or opacity qualification.

Other agents' crashes and Windows event records are outside this instance's
bounded package. Cross-instance timing requires their independent receipts.
No public tool or game asset was changed during this launcher investigation.
