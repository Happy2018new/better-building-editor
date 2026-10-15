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
#ifndef _UNIFORM_PER_FRAME_CONSTANTS_H
#define _UNIFORM_PER_FRAME_CONSTANTS_H
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
layout(binding = 2) uniform PerFrameConstants {
#endif
// BEGIN_UNIFORM_BLOCK(PerFrameConstants) - unfortunately this macro does not work on old Amazon platforms so using above 3 lines instead
UNIFORM vec3 VIEW_POS;
#ifdef MCPE_NETEASE
// TIME will loop from [0, 210]
// make sure your shader handles the case when it transitions from 210 to 0
#endif
UNIFORM float TIME;
#ifdef MCPE_NETEASE
UNIFORM vec4 BLEND_COLOR;
UNIFORM vec4 USER_FOR_COLOR_NEAR;
UNIFORM vec4 USER_FOR_COLOR_FAR;

UNIFORM vec4 LIGHT_NUM_STRENGTH;
UNIFORM vec4 LIGHT_POS_RANGE_0;
UNIFORM vec4 LIGHT_COLOR_ATTEN_0;
UNIFORM vec4 LIGHT_DIR_TYPE_0;
UNIFORM vec4 LIGHT_FALLOFF_COS_0;

UNIFORM vec4 LIGHT_POS_RANGE_1;
UNIFORM vec4 LIGHT_COLOR_ATTEN_1;
UNIFORM vec4 LIGHT_DIR_TYPE_1;
UNIFORM vec4 LIGHT_FALLOFF_COS_1;

UNIFORM vec4 LIGHT_POS_RANGE_2;
UNIFORM vec4 LIGHT_COLOR_ATTEN_2;
UNIFORM vec4 LIGHT_DIR_TYPE_2;
UNIFORM vec4 LIGHT_FALLOFF_COS_2;

UNIFORM vec4 PLANAR_SHADOW_PARAMS1;
UNIFORM vec4 PLANAR_SHADOW_PARAMS2;
UNIFORM vec4 PLANAR_SHADOW_PARAMS3;
UNIFORM vec4 PLANAR_SHADOW_PARAMS4;
#endif
UNIFORM vec4 FOG_COLOR;
UNIFORM vec2 FOG_CONTROL;
UNIFORM float RENDER_DISTANCE;
UNIFORM float FAR_CHUNKS_DISTANCE;
UNIFORM float OCCLUSION_HEIGHT_OFFSET;
END_UNIFORM_BLOCK

#endif

void main() {
    float depth=encodedPlane.w*32.0;
    if(depth>31.0) { gl_FragColor=vec4(0.,0.,0.,0.); return; }
    float stripe=mod(floor(gl_FragCoord.x/4.0),32.0);
    if(abs(floor(depth+0.5)-stripe)>0.25) discard;
    gl_FragColor=vec4(vec3(0.25)+0.75*vec3(colorLookupUV,encodedPlane.w),0.);
}
