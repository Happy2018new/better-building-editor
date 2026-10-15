# Interpretation Before Any Appearance Candidate

The original installed renderchunk pair has no normal input or TILE uniform.
Its non-seasonal, non-fog final RGB is texture0.rgb multiplied by native
texture1(uv1).rgb unless ALWAYS_LIT, then by interpolated COLOR.rgb. FOG mixes
that result with fogColor. SEASONS uses its separate texture2/color expression.
Read actual flags first, then use the corresponding original branch.

The south skeleton details confirm explicit geometric normal delivery and
actor TILE=(1,1,1) for this isolated test. They do not prove native terrain light
uses that factor. The candidate front intensity is 210/255 while the native
world front remains visibly darker. Wait for v4 COLOR/lightmap separation;
do not compensate by adjusting a guessed global brightness or TILE constant.

With the exact original v3 camera and image dimensions only, the reviewed
top-body sky ROI x=[912,1088), y=[440,455) spans these useful x ranges:

| X | Slot |
| --- | --- |
| 912-927 | COLOR |
| 928-943 | Magenta marker |
| 944-959 | Lightmap |
| 960-975 | Cyan marker |
| 976-991 | Flags |
| 992-1007 | White marker |
| 1008-1023 | Original final RGB |
| 1024-1039 | Yellow marker |
| 1040-1055 | COLOR repeat |
| 1056-1071 | Magenta repeat |
| 1072-1087 | Lightmap repeat |

These bounds are a planning aid, not automatic v4 qualification. Open the new
raw native/empty images and confirm the body and every marker/data pair again.
Use interior pixels away from edge postprocessing before interpreting values.

If native COLOR changes by face and lightmap is a shared factor, the next
narrow candidate should explicitly match those two measured factors using
the proven normal path and the existing owner inputs. It must separately
establish a supported source of changing world illumination. An isolated
full-daylight numeric constant would only be a diagnostic fit, not a general
product fix. If values vary across vertices from AO or fixture proximity,
record the limitation before selecting a per-face-only approximation.
