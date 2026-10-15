#version 300 es
#define MCPE_NETEASE
#define MAT4 highp mat4
#define POS4 highp vec4
#define POS3 highp vec3
// __multiversion__
precision highp float;
precision highp int;
#define main nativePortalMain
// __multiversion__
// This signals the loading code to prepend either #version 100 or #version 300 es as apropriate.
// To use centroid sampling we need to have version 300 es shaders, which requires changing:
// attribute to in
// varying to out when in vertex shaders or in when in fragment shaders
// defining an out vec4 FragColor and replacing uses of gl_FragColor with FragColor
// texture2D to texture
#if __VERSION__ >= 300

#ifdef MSAA_FRAMEBUFFER_ENABLED
#define _centroid centroid
#else
#define _centroid
#endif

#define varying in
#define texture2D texture
out vec4 FragColor;
#define gl_FragColor FragColor

#endif

#ifndef _UNIFORM_MACRO_H
#define _UNIFORM_MACRO_H

#ifdef MCPE_PLATFORM_NX
// Unfortunately this macro does not work on old Amazon platforms #define BEGIN_UNIFORM_BLOCK(x) uniform x {
#define END_UNIFORM_BLOCK };
#define UNIFORM 
#else
// Unfortunately this macro does not work on old Amazon platforms #define BEGIN_UNIFORM_BLOCK(x) 
#define END_UNIFORM_BLOCK
#define UNIFORM uniform 
#endif

#if __VERSION__ >= 420
#define LAYOUT_BINDING(x) layout(binding = x)
#else
#define LAYOUT_BINDING(x) 
#endif

#endif


#if __VERSION__ >= 300
	#ifndef BYPASS_PIXEL_SHADER
		#if defined(TEXEL_AA) && defined(TEXEL_AA_FEATURE)
			_centroid in highp vec2 colorLookupUV;
			_centroid in highp vec2 parallaxUV;
		#else
			_centroid in vec2 colorLookupUV;
			_centroid in highp vec2 parallaxUV;
		#endif
	#endif
#else
	#ifndef BYPASS_PIXEL_SHADER
		varying vec2 colorLookupUV;
		varying highp vec2 parallaxUV;
	#endif
#endif

#ifndef BYPASS_PIXEL_SHADER
	varying lowp vec4 encodedPlane;
	#ifdef FOG
		varying vec4 fogColor;
	#endif
#endif

LAYOUT_BINDING(0) uniform sampler2D TEXTURE_0;
LAYOUT_BINDING(1) uniform sampler2D TEXTURE_1;

const float MAX_LAYER_DEPTH = 32.0;

void main()
{
	#ifdef BYPASS_PIXEL_SHADER
		gl_FragColor = vec4(0, 0, 0, 0);
	#else

	///// Color Assembly
	vec4 colorSample = texture2D(TEXTURE_1, colorLookupUV);
	vec4 textureSample = texture2D(TEXTURE_0, parallaxUV);
	float brightness = 1.0 - (encodedPlane.w);
	vec3 result = textureSample.rgb * colorSample.rgb * brightness;

	#ifdef FOG
		if(encodedPlane.w * MAX_LAYER_DEPTH > MAX_LAYER_DEPTH - 1.0) {
			gl_FragColor = vec4(mix(vec3(0,0,0), fogColor.rgb, fogColor.a), 0);
		}
		else {
			gl_FragColor = vec4(result * (1.0 - fogColor.a), 1);
		}
	#else
		// Look for hard-coded value to clear the portal first
		if(encodedPlane.w * MAX_LAYER_DEPTH > MAX_LAYER_DEPTH - 1.0) {
			gl_FragColor = vec4(0, 0, 0, 0);
		}
		else {
			gl_FragColor = vec4(result, 1);
		}
	#endif

	#endif
}

#undef main
#ifndef _UNIFORM_EXTRA_VECTOR_CONSTANTS_H
#define _UNIFORM_EXTRA_VECTOR_CONSTANTS_H
#ifndef _UNIFORM_MACRO_H
#define _UNIFORM_MACRO_H

#ifdef MCPE_PLATFORM_NX
// Unfortunately this macro does not work on old Amazon platforms #define BEGIN_UNIFORM_BLOCK(x) uniform x {
#define END_UNIFORM_BLOCK };
#define UNIFORM 
#else
// Unfortunately this macro does not work on old Amazon platforms #define BEGIN_UNIFORM_BLOCK(x) 
#define END_UNIFORM_BLOCK
#define UNIFORM uniform 
#endif

#if __VERSION__ >= 420
#define LAYOUT_BINDING(x) layout(binding = x)
#else
#define LAYOUT_BINDING(x) 
#endif

#endif


#ifdef MCPE_PLATFORM_NX
layout(binding = 1) uniform SfxConstants {
#endif
// BEGIN_UNIFORM_BLOCK(SfxConstants) - unfortunately this macro does not work on old Amazon platforms so using above 3 lines instead
UNIFORM vec4 EXTRA_VECTOR1;
UNIFORM vec4 EXTRA_VECTOR2;
UNIFORM vec4 EXTRA_VECTOR3;
UNIFORM vec4 EXTRA_VECTOR4;
UNIFORM vec4 EXTRA_VECTOR5;
UNIFORM vec4 EXTRA_VECTOR6;
UNIFORM vec4 EXTRA_VECTOR7;
UNIFORM vec4 EXTRA_VECTOR8;
UNIFORM vec4 EXTRA_VECTOR9;
UNIFORM vec4 EXTRA_VECTOR10;
UNIFORM vec4 EXTRA_VECTOR11;
UNIFORM vec4 EXTRA_VECTOR12;
UNIFORM vec4 EXTRA_VECTOR13;
UNIFORM vec4 EXTRA_VECTOR14;
UNIFORM vec4 EXTRA_VECTOR15;
UNIFORM vec4 EXTRA_VECTOR16;
UNIFORM vec4 NTES_PBR_ENTITY_SHADOW_MATRIX0;
UNIFORM vec4 NTES_PBR_ENTITY_SHADOW_MATRIX1;
UNIFORM vec4 NTES_PBR_ENTITY_SHADOW_MATRIX2;
UNIFORM vec4 NTES_PBR_ENTITY_SHADOW_MATRIX3;
UNIFORM vec4 NTES_PBR_ENTITY_SHADOW_PARAMS;
UNIFORM vec4 NTES_PBR_ENTITY_SHADOW_PARAMS2;
UNIFORM vec4 MATERIAL_INSTANCE_PARAM1;
UNIFORM vec4 MATERIAL_INSTANCE_PARAM2;
UNIFORM vec4 MATERIAL_INSTANCE_PARAM3;
UNIFORM vec4 MATERIAL_INSTANCE_PARAM4;
UNIFORM vec4 SUN_DIR;
UNIFORM vec4 WATER_TEXTURE_UV_RANGE;
UNIFORM vec4 SKY_NEAR_COLOR;
UNIFORM vec4 SKY_FAR_COLOR;
UNIFORM vec4 RAIN_NEAR_COLOR;
UNIFORM vec4 RAIN_FAR_COLOR;
UNIFORM vec4 COLOR_MAPPING_PARAM;
END_UNIFORM_BLOCK

#endif

#ifndef _UNIFORM_WORLD_CONSTANTS_H
#define _UNIFORM_WORLD_CONSTANTS_H
#ifndef _UNIFORM_MACRO_H
#define _UNIFORM_MACRO_H

#ifdef MCPE_PLATFORM_NX
// Unfortunately this macro does not work on old Amazon platforms #define BEGIN_UNIFORM_BLOCK(x) uniform x {
#define END_UNIFORM_BLOCK };
#define UNIFORM 
#else
// Unfortunately this macro does not work on old Amazon platforms #define BEGIN_UNIFORM_BLOCK(x) 
#define END_UNIFORM_BLOCK
#define UNIFORM uniform 
#endif

#if __VERSION__ >= 420
#define LAYOUT_BINDING(x) layout(binding = x)
#else
#define LAYOUT_BINDING(x) 
#endif

#endif


#ifdef MCPE_PLATFORM_NX
layout(binding = 1) uniform WorldConstants {
#endif
// BEGIN_UNIFORM_BLOCK(WorldConstants) - unfortunately this macro does not work on old Amazon platforms so using above 3 lines instead
UNIFORM MAT4 WORLDVIEWPROJ;
UNIFORM MAT4 WORLD;
UNIFORM MAT4 WORLDVIEW;
UNIFORM MAT4 PROJ;
#ifdef MCPE_NETEASE
UNIFORM MAT4 VIEWPROJ;
#endif
END_UNIFORM_BLOCK

#endif

varying highp float portalVisible;
varying highp float portalClip;
void main() {
    if(portalVisible<0.5 || portalClip>0.0 || EXTRA_VECTOR4.w<=0.0) discard;
    nativePortalMain();
    float opacity=EXTRA_VECTOR4.w;
    // Native One/SourceAlpha clears once, then adds the colored star planes.
    if(encodedPlane.w*MAX_LAYER_DEPTH>MAX_LAYER_DEPTH-1.0) gl_FragColor.a=1.0-opacity;
    else gl_FragColor.rgb*=opacity;
}
