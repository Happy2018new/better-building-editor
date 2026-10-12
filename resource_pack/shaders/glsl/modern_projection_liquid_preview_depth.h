#ifndef MODERN_PROJECTION_LIQUID_PREVIEW_DEPTH_H
#define MODERN_PROJECTION_LIQUID_PREVIEW_DEPTH_H

#include "uniformShaderConstants.h"

// The liquid caller supplies decoded coordinates around its four-cell centre.
void liquidApplyPreviewDepth(vec3 point, float distance, inout vec4 projected, out float clip) {
    vec3 viewZ = vec3(WORLDVIEW[0][2], WORLDVIEW[1][2], WORLDVIEW[2][2]);
    clip = dot(normalize(viewZ), point) + distance;
    float centerDepth = PROJ[2][2] * (-350.0) + PROJ[3][2];
    projected.z = (centerDepth + clip * PROJ[2][2] * 0.04) / (1.0 + abs(centerDepth));
}

void liquidUniformPreviewDepth(vec3 point, float depthCode, inout vec4 projected, out float clip) {
    clip = -1.0;
    if (abs(PROJ[3][3]) <= 0.5 || mod(depthCode,256.0) != 134.0) return;
    float distance = (floor(depthCode / 256.0) - 32768.0) / 64.0;
    liquidApplyPreviewDepth(point, distance, projected, clip);
}

// Retain the image-packet diagnostic path for independent binding controls.
void liquidPreviewDepth(vec3 point, inout vec4 projected, out float clip) {
    clip = -1.0;
    float tag = floor(CURRENT_COLOR.r * 255.0 + 0.5);
    if (abs(PROJ[3][3]) <= 0.5 || tag < 209.0 || tag > 222.0) return;
    bool layoutPacket = fract(CURRENT_COLOR.r * 255.0) > 0.125;
    float distance = (floor(CURRENT_COLOR.g * 255.0 + 0.5) * 256.0 +
                      floor(CURRENT_COLOR.b * 255.0 + 0.5) - 32768.0) / 64.0;
    if (layoutPacket) distance = (floor(CURRENT_COLOR.b * 65536.0 + 0.5) - 32768.0) / 64.0;
    liquidApplyPreviewDepth(point, distance, projected, clip);
}

#endif
