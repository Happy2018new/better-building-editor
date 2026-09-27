// HLSL port of resource_pack/shaders/glsl/modern_projection_staff.fragment.
// RenderDragon callers supply their own vertex outputs and a bounded clock.
// Keep float32 arithmetic: the hash is not safe in min16float/half.
#ifndef MODERN_PROJECTION_STARFIELD_HLSLI
#define MODERN_PROJECTION_STARFIELD_HLSLI
float mpHash(float2 p) {
    return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453);
}
float mpStars(float2 p, float layer, float threshold, float seconds) {
    float2 cell = floor(p), f = frac(p) - .5;
    float seed = mpHash(cell + layer * 19.);
    float2 offset = float2(mpHash(cell + 4.), mpHash(cell + 9.)) * .65 - .325;
    float r = length(f - offset);
    float twinkle = .65 + .35 * sin(seconds * 6.2831853 * 30. / 210. + seed * 40.);
    float core = 1. - smoothstep(.040, .115, r);
    float halo = exp(-r * r * 70.) * .26;
    return (core + halo) * step(threshold, seed) * twinkle;
}
float3 mpStarfield(float3 skyRay, float3 normal, float3 position,
                  float3 localNormal, float seconds, bool violet, bool grip, bool goldMote) {
    float3 ray = normalize(skyRay), n = normalize(normal), view = -ray;
    float latitude = asin(clamp(ray.y, -1., 1.));
    float2 sky = float2(atan2(ray.z, ray.x) * cos(latitude), latitude);
    float skyTime = seconds * 6.2831853 / 105.;
    float2 drift = float2(cos(skyTime), sin(skyTime)) * 7.8;
    float2 local = float2(position.x + position.z * .37, position.y);
    float2 g = sky * 14. + local * .65 + drift;
    if (!goldMote) {
        float3 axis = abs(normalize(localNormal));
        float2 face = axis.x > axis.z
            ? (axis.x > axis.y ? position.zy : position.xz)
            : (axis.z > axis.y ? position.xy : position.xz);
        g = face * .55 + ray.xz * 1.7 + drift;
        local = face * .15;
    }
    float2 p = g;
    float clouds = sin(p.x * 2.3 + sin(p.y * 2.1)) * sin(p.y * 3.7 - p.x * .8);
    float clouds2 = sin(p.x * 5.1 + cos(p.y * 3.3)) * sin(p.y * 6.7 + p.x * 1.1);
    float3 deep = float3(.020, .040, .100);
    float3 nebula = violet ? float3(.135, .060, .300) : float3(.050, .200, .320);
    float3 rgb = lerp(deep, nebula, smoothstep(-.35, .55, clouds) * .9);
    rgb += nebula * .45 * pow(.5 + .5 * clouds2, 3.);
    float filament = pow(.5 + .5 * sin(p.y * 4. + sin(p.x * 2.) * 1.7), 5.);
    rgb += float3(.020, .080, .120) * filament;
    float4 cut = grip ? float4(.70, .78, .84, .90) : float4(.30, .45, .35, .30);
    rgb += float3(.66, .89, 1.) * mpStars(g + drift * .65 + local * 2.8, 1., cut.x, seconds)
        + float3(.63, .54, .90) * mpStars(g * 1.714 + drift * .42 + local * 4.2, 2., cut.y, seconds) * .72
        + float3(.76, .91, 1.) * mpStars(g * 3.143 + drift * .18 + local * 6.1, 3., cut.z, seconds) * .38
        + float3(.60, .70, 1.) * mpStars(g * 5.571 + drift * .10 + local * 9.3, 4., cut.w, seconds) * .22;
    float fresnel = pow(saturate(1. - abs(dot(n, view))), 3.);
    float shine = pow(max(0., dot(reflect(-normalize(float3(-.4, .8, .5)), n), view)), 28.);
    float facet = .5 + .5 * dot(n, normalize(float3(-.45, .7, .6)));
    rgb += float3(.18, .48, .61) * fresnel * .7 + float3(.74, .91, 1.) * shine * .7;
    rgb += float3(.035, .065, .085) * facet;
    if (grip) rgb = rgb * .78 + float3(.012, .020, .032);
    if (goldMote) {
        float3 cells = floor(position * 14.);
        float mineral = mpHash(cells.xy + cells.z * float2(17., 37.));
        float warmCloud = smoothstep(-.5, .6, clouds);
        float3 gold = lerp(float3(.23, .085, .014), float3(.80, .42, .075), warmCloud);
        gold += float3(.42, .32, .13) * smoothstep(.32, .83, mineral);
        float sparks = mpStars(g + drift * .65 + local * 2.8, 1., .30, seconds)
            + mpStars(g * 1.714 + drift * .42 + local * 4.2, 2., .45, seconds) * .72
            + mpStars(g * 3.143 + drift * .18 + local * 6.1, 3., .35, seconds) * .38
            + mpStars(g * 5.571 + drift * .10 + local * 9.3, 4., .30, seconds) * .22;
        rgb = gold + float3(1., .85, .44) * sparks
            + float3(.22, .14, .045) * fresnel + float3(1., .89, .61) * shine * .55;
    }
    return rgb;
}
#endif
