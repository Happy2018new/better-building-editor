// Windows RenderDragon SM6 pixel-stage pilot, not an addon registration API.
// Uses the native Actor vertex shader; final local normals/taper still need a VS port.
#include "starfield.hlsli"
#ifndef MP_TIME_REGISTER
#define MP_TIME_REGISTER c0
#endif
// Candidate renderer clock; declaration alone does not establish per-frame binding.
// The pilot has demonstrated visible shading, not verified continuous time advance.
cbuffer FragmentUniforms : register(b1) { float4 Time : packoffset(MP_TIME_REGISTER); };
#if defined(MP_PREPASS)
Texture2D<float4> s_MatTextureTexture : register(t1);
SamplerState s_MatTextureSampler : register(s1);
#elif defined(MP_PBR)
Texture2D<float4> s_MatTextureTexture : register(t2);
SamplerState s_MatTextureSampler : register(s2);
#else
Texture2D<float4> s_MatTextureTexture : register(t0);
SamplerState s_MatTextureSampler : register(s0);
#endif
struct PixelInput {
    float4 position : SV_Position;
#ifdef MP_PBR
    float3 bitangent : BITANGENT;
    float4 clipPosition : COLOR1;
    float4 color0 : COLOR0;
    float3 normal : NORMAL;
    float3 prevWorldPos : TEXCOORD4;
    float3 tangent : TANGENT;
#else
    float4 clipPosition : COLOR1;
    float4 color0 : COLOR0;
    float4 fog : COLOR2;
    float4 light : COLOR3;
#endif
    centroid float2 uv : TEXCOORD0;
    float3 worldPosition : TEXCOORD3;
};
float4 shade(PixelInput input) {
#ifdef MP_SOLID_PROBE
    return float4(1., 0., 1., 1.);
#else
    float4 base = s_MatTextureTexture.Sample(s_MatTextureSampler, input.uv);
    clip(base.a - .1);
    // Diagnostic selection by this project's palette size, not a public material ID.
    uint width, height;
    s_MatTextureTexture.GetDimensions(width, height);
    if (width != 48 || height != 8) return base;
    // Keep gold/ivory frame texels; blue palette cells identify gem/grip surfaces.
    if (base.b <= base.r * 1.25) return base;
    // UV-local diagnostic coordinates isolate the port from native VS transforms.
    // The production gem-local position/normal and camera ray still need a VS port.
    float3 ray = float3((input.uv - .5) * .3, 1.);
    float3 faceNormal = float3(0., 0., -1.);
    float3 local = float3(input.uv.x * 48., input.uv.y * 8., 0.);
    float seconds = isfinite(Time.x) ? frac(Time.x / 210.) * 210. : 0.;
    float3 rgb = mpStarfield(ray, faceNormal, local, float3(0., 0., 1.),
                            seconds, false, base.r < .2, false);
    return float4(rgb, 1.);
#endif
}
#ifdef MP_PREPASS
struct GBufferOutput {
    float4 albedoEmissive : SV_Target0;
    float4 normalMotion : SV_Target1;
    float4 roughnessLightMetal : SV_Target2;
};
GBufferOutput main(PixelInput input) {
    GBufferOutput output;
    output.albedoEmissive = float4(shade(input).rgb, 1.);
    float3 n = normalize(input.normal);
    n /= max(abs(n.x) + abs(n.y) + abs(n.z), .000001);
    float2 octNormal = n.xy;
    if (n.z < 0.) octNormal = (1. - abs(n.yx)) * float2(n.x < 0. ? -1. : 1., n.y < 0. ? -1. : 1.);
    // Minimal diagnostic G-buffer: full emission, rough dielectric, zero motion.
    // Production PBR lighting/motion-vector parity is outside this pixel-stage pilot.
    output.normalMotion = float4(octNormal, 0., 0.);
    output.roughnessLightMetal = float4(.8, 1., 1., 0.);
    return output;
}
#else
float4 main(PixelInput input) : SV_Target0 { return shade(input); }
#endif
