#version 300 es
#define MCPE_NETEASE
#define MAT4 highp mat4
#define POS4 highp vec4
// __multiversion__
// This signals the loading code to prepend either #version 100 or #version 300 es as apropriate.

precision highp float;
precision highp int;
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

varying highp float nativePreviewClip;
#ifndef _UNIFORM_SHADER_CONSTANTS_H
#define _UNIFORM_SHADER_CONSTANTS_H
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
#extension GL_ARB_enhanced_layouts : enable
layout(binding = 3) uniform ShaderConstants {
#endif
// BEGIN_UNIFORM_BLOCK(ShaderConstants) - unfortunately this macro does not work on old Amazon platforms so using above 3 lines instead
UNIFORM vec4 CURRENT_COLOR;
UNIFORM vec4 DARKEN;
UNIFORM vec3 TEXTURE_DIMENSIONS;
UNIFORM float HUD_OPACITY;
UNIFORM MAT4 UV_TRANSFORM;
END_UNIFORM_BLOCK

#endif


LAYOUT_BINDING(0) uniform sampler2D TEXTURE_0;

#if __VERSION__ >= 300
_centroid varying vec4 uv;
#else
varying vec4 uv;
#endif

#ifdef ENABLE_FOG
varying vec4 fogColor;
#endif

#ifdef ENABLE_LIGHT
varying vec4 light;
#endif

#ifndef DISABLE_TINTING
varying vec4 color;
#endif

void main()
{
    if(nativePreviewClip>=0.0) discard;
	vec4 diffuse = texture2D(TEXTURE_0, uv.xy);
	vec4 base = texture2D(TEXTURE_0, uv.zw);

#ifndef DISABLE_TINTING
	base.a = mix(diffuse.r * diffuse.a, diffuse.a, color.a);
	base.rgb *= color.rgb;
#endif

#ifdef ENABLE_LIGHT
	base.rgb *= light.rgb;
#endif

#ifdef ENABLE_FOG
	//apply fog
	base.rgb = mix( base.rgb, fogColor.rgb, fogColor.a );
#endif

#ifdef UI_ENTITY
	base.a *= HUD_OPACITY;
#endif
	gl_FragColor = base;
}