# Water transparency continuation handoff

Stopped immediately at the user request to save context and end sessions.
No new diagnostic project, launch, capture or production edit occurred after
resuming from the previous handoff. All water-owned games remain stopped.

Current assessment: geometry=true, direction=15/15, transparency=false
(manually rejected), overall product visual acceptance=false. The exact original
JSON reports are unchanged; `review-assessment.json` explicitly supersedes their
confounded transparency conclusion. Six-control crops and RGB means are included.

Confirmed flaw: wet/liquid-only and wet/rearless were captured seconds apart
under animated water. The prior >=8 RGB delta / >=10% pixels gate can pass from
animation alone. Full-world body means: wet [8.40,52.46,83.14], liquid-only
[8.35,52.33,83.27], dry [109.07,88.8,52.74]. Rear wet [8.8,54.63,86.81], rearless
[8.78,53.58,85.07], dry gold [201.44,168.92,44.62]. This looks effectively opaque.

Read actual 3.10 inheritance from
D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/resource_packs/vanilla_netease/materials/entity.material
around line 638: entity_for_skeleton_alpha inherits entity_for_skeleton; states
are Blending and DisableDepthWrite, defines add USE_ALPHA/USE_SKINNING. No extra
render pass is declared there. Product materials explicitly use SourceAlpha /
OneMinusSrcAlpha and InvertCulling. Fragment has default 0.45 alpha and recorded
EXTRA_VECTOR4=[39686,-1,4501493,1]. Actual GPU alpha/state remains unverified.

Fence data: one top part (faces=1), one side part (faces=30), each one visible
slot; Scene double buffers correctly show only one doll per group. Thus no data
level duplicate layer was found. Pool stripes/backface duplication still need
investigation. Do not claim root cause from these observations alone.

Next permitted experiment, after user resumes: make an independent diagnostic
copy; preserve original production snapshots; use existing --frozen path for
same-phase controls and add diagnostic model variants to distinguish constant
shader alpha, actual alpha encoded as opaque grayscale, explicit material states,
base material inheritance and draw order. Do not sign-flip clock or UV; direction
remains valid. Root authorized fixing blend/depth/coverage cause, but production
changes still need agent coordination for shared material registry.

Important launch detail: D:/bbe-r15-water-production-sky/.mcdev.json currently
includes D:/bbe-r15-water-production (both BP/RP were identical in prior captures).
Any new diagnostic copy must update included_mod_dirs to its own absolute path,
otherwise resource edits would not be loaded. No diagnostic copy has been made.

Last owned session: C:/Users/Happy2018new/.pyreact-debug/instances/6bbdb943cc8c499caebdb5bceb8ea924/session.json
owner water-production310-r15, game PID 35392 (stopped), last preclose handles
391410. Natural WM_CLOSE shutdown; process absence confirmed before stop --force
finalized session. See final-runtime-stopped.json. Do not close other owners.

Use the pinned MCDK/guard/WGC hashes from final-runtime-stopped.json and retained
launch inputs. MCDEV_ALLOW_USER_FOREGROUND=1, no input/focus/resize, at most five
instances. Never touch user tools/p0_palette*_probe.py. No commits or staging by
this agent. Item sprite catalog investigation remains paused.

Compact staging scope is this review directory plus the previously listed
water direction host tools/tests. Full raw archive is ~538 MB and stays local.
