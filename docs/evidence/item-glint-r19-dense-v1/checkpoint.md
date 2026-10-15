# Final Shader R19 Continuous Animation Checkpoint

Captured 2026-10-15 16:11–16:16 Asia/Shanghai in the owned private `D:/bbe-r18-item-glint` instance. Final fragment SHA256 is `3c288ec16d18d66b908393c34dd84b6bb4a884ca52b8a2e1039a94a392a3da87`; resource contract is `515be879b61fc352b3e00e66d063f8da6e05036a8cd7d83aa54db563fb86815e`. Capture launch/after snapshots and root fragment bytes match. No old-shader success frames are substituted.

**Four-route continuous visible motion is accepted. Product qualification remains false.**

| Route | Valid frames | Measured duration | Maximum frame gap | Minimum changed body fraction in overlapping 1s windows |
| --- | ---: | ---: | ---: | ---: |
| Editor | 280 | 7.9635105s | 42.4226ms | 93.1818% |
| World full | 91 | 7.9513868s | 193.9440ms | 93.5678% |
| World missing | 81 | 7.9513830s | 139.3983ms | 88.3512% |
| Actual native item frame | 73 | 7.8483556s | 145.4524ms | 99.7214% |

The unchanged limits require at least 7s, a maximum 250ms gap, and more than 5% visible body RGB change in every overlapping 1s window. All routes have stable declared camera/layout. All ordinary-item controls pass. Every route rejects frozen-body and empty-body negative controls. Sparse source-associated analysis reports evidence_valid=true, all_bodies_passed=true, reference_valid=true and native_glint_visibility_accepted=true. Dense analysis reports continuous_motion_accepted=true, diagnostic_only=false and product_qualified=false.

The four dense contact sheets were visually inspected and show evolving glint over the observed sword body. The custom route remains brighter than the actual native frame. This evidence does not establish exact native texture phase speed, lighting parity or 60fps presentation. Bright-area centroid displacement ratios remain diagnostic and do not qualify phase speed.

The first R19 capture used the default wide layout, completed and restored correctly, and produced four valid timelines. Its approximately 50px item bodies do not satisfy the dense analyzer 150px body requirement. It is retained at `.runtime/item-glint-final-dense-r19-v1` and is not used for this acceptance. This second capture uses the same successful compact layout as the final-byte R18 static reference.

## Credential Redaction and Local Sources

`report.json` is a credential-redacted review copy, not original capture bytes. Only `$.session.token` and `$.camera_calibration.session.token` are semantically changed, both to `REDACTED`. The original raw report remains git-ignored at `.runtime/item-glint-final-dense-r19-v2/report.json`, SHA256 `df86c53dd9877cf47aba7f6dc63947c0c9035ece6e15a019229dfafeb348da2a`. The redacted report SHA256 is `5efaa67f23b414bc120a652e5c8c3547959e0076c92988c0404c5f45e519d45e`.

Both analyzers were actually rerun with the redacted report as input. Every measurement matches the original raw-input analysis; regenerated GIF and contact-sheet hashes match the originals. Selected PNG screenshots and capture receipts are unchanged. `provenance.json` records both report identities, executed host analyzer bindings, transformations and commands. The project contains unused older analyzer copies; they were not executed, and provenance distinguishes them from the actual host analyzers.

This is a local review copy. The full 1277 original artifacts, including every full-resolution dense frame and native receipt, remain in ignored runtime. `original-local-artifacts.json` binds their paths, sizes and SHA256 hashes. They are not all distributed inside this compact review directory. `manifest.json` binds every review file. No original credential bytes remain in this directory.

## Runtime Cleanup and Remaining Product Scope

Capture completed with source_unchanged=true and empty report, closeup and native-reference cleanup arrays. Actual native frame blocks and player position were restored. Camera locks were released. Owned session `a973e93e5fff431b934e0924f72089b6`, game PID 43620 identity 134365250182649481 and MCDK PID 40404 identity 134365250180495826 are stopped and both process identities are gone. No activation, resize or desktop input was used. User-controlled foreground changes were allowed.

The next pixel-risk checks belong to the integrated product matrix: frame/glow-frame facing and rotation extremes, opacity/depth/occupancy transitions, and representative catalog alias/aux variants. Shelf three-slot and campfire four-slot gates remain independent. Patterned shields/banners, filled-map world pixels, charged crossbows, tridents/spears, heads/skins, tinted potion/leather/spawn eggs and clocks/compasses remain separate content-family work. This sword continuity result does not qualify those families or the production registry.
