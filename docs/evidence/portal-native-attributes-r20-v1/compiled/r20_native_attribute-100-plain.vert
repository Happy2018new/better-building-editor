#version 100
#define MCPE_NETEASE
#define MAT4 highp mat4
#define POS4 highp vec4
#define POS3 highp vec3
// __multiversion__
// This signals the loading code to prepend either #version 100 or #version 300 es as apropriate.

// To use centroid sampling we need to have version 300 es shaders, which requires changing:
// attribute to in
// varying to out when in vertex shaders or in when in fragment shaders
// defining an out vec4 FragColor and replacing uses of gl_FragColor with FragColor
// texture2D to texture

precision highp float;
precision highp int;
// To use centroid sampling we need to have version 300 es shaders, which requires changing:
// attribute to in
// varying to out when in vertex shaders or in when in fragment shaders
// defining an out vec4 FragColor and replacing uses of gl_FragColor with FragColor
// texture2D to texture
#if __VERSION__ >= 300
#define attribute in
#define varying out

#ifdef MSAA_FRAMEBUFFER_ENABLED
#define _centroid centroid
#else
#define _centroid
#endif
#endif



#if __VERSION__ >= 300
	#ifndef BYPASS_PIXEL_SHADER
		_centroid out vec2 colorLookupUV;
		_centroid out vec2 parallaxUV;
	#endif
#else
	#ifndef BYPASS_PIXEL_SHADER
		varying vec2 colorLookupUV;
		varying vec2 parallaxUV;
	#endif
#endif

#ifndef BYPASS_PIXEL_SHADER
	varying lowp vec4 encodedPlane;
	#ifdef FOG
		varying vec4 fogColor;
	#endif
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

#ifndef _UNIFORM_RENDER_CHUNK_CONSTANTS_H
#define _UNIFORM_RENDER_CHUNK_CONSTANTS_H
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
layout(binding = 0) uniform RenderChunkConstants {
#endif
// BEGIN_UNIFORM_BLOCK(RenderChunkConstants) - unfortunately this macro does not work on old Amazon platforms so using above 3 lines instead
UNIFORM POS4 CHUNK_ORIGIN_AND_SCALE;
#ifdef MCPE_NETEASE
UNIFORM float BLOCK_LIGHT_TYPE;
#endif
UNIFORM float RENDER_CHUNK_FOG_ALPHA;
END_UNIFORM_BLOCK

#endif


#ifndef BYPASS_PIXEL_SHADER
	attribute POS4 POSITION;
	attribute vec4 COLOR;
	attribute vec2 TEXCOORD_0;
	attribute vec2 TEXCOORD_1;
#endif

const float MAX_LAYER_DEPTH = 32.0;

void main() {
	///// Vertex Transformation
	POS4 worldPos = vec4((POSITION.xyz * CHUNK_ORIGIN_AND_SCALE.w) + CHUNK_ORIGIN_AND_SCALE.xyz, 1);
	POS4 pos = PROJ * (WORLDVIEW * worldPos);
	gl_Position = pos;

	#ifndef BYPASS_PIXEL_SHADER
		///// End Portal Data
		colorLookupUV = TEXCOORD_0;
		encodedPlane = COLOR; // Color value is used to encode the starfield plane

		vec3 planeNormal = (encodedPlane.xyz - vec3(0.5,0.5,0.5)) * 2.0;
		float planeDistance = encodedPlane.w * MAX_LAYER_DEPTH;

		// Calculate view direction from the surface position and the eye position
		POS3 viewRay = worldPos.xyz;

		///// Ray-cast for parallax-offset UV
		// Perform ray-plane intersection to find the position on the parallax plane
		float t = (dot(viewRay - (planeDistance * planeNormal), planeNormal)) / dot(viewRay, planeNormal);
		POS3 parallaxPositionInWorld = (t * viewRay) + VIEW_POS;

		///// Ridiculous UV-remapping
		// Create a mask with a 1 wherever the normal would have a non-zero value
		// All normals are orthonormal on <x,y,z>, so there should be two 0's and a 1
		vec3 normalMask = floor(abs(planeNormal) + vec3(0.5,0.5,0.5));
		// Mask out the correct uv result
		vec2 raycastUV = parallaxPositionInWorld.yz * normalMask[0] + parallaxPositionInWorld.xz * normalMask[1] + parallaxPositionInWorld.xy * normalMask[2];

		// Scale the UVs to Minecraft pixel size
		raycastUV = raycastUV / 16.0; // TODO: Use TEXTURE_DIMENSIONS

		const float rotor = 3.1415926535897 * (5.0 / 7.0);
		float rotS = sin(planeDistance * rotor);
		float rotC = cos(planeDistance * rotor);

		parallaxUV = mat2(vec2(rotC, rotS), vec2(-rotS, rotC)) * raycastUV;

		parallaxUV += vec2(rotC, rotS) * planeDistance;
		parallaxUV.y += TIME / 256.0;

		// User story 103038: fix visuals for end portal on low-precision devices
		//const float modVal = 64.0;
		//parallaxUV = vec2(mod(parallaxUV.x, modVal), mod(parallaxUV.y, modVal));
		
		///// Fog
		#ifdef FOG
			#ifdef FANCY
				vec3 relPos = -worldPos.xyz;
				float cameraDepth = length(relPos);
				#ifdef NEAR_WATER
					cameraDist = cameraDepth / FAR_CHUNKS_DISTANCE;
				#endif
			#else
				float cameraDepth = pos.z;
				#ifdef NEAR_WATER
					vec3 relPos = -worldPos.xyz;
					float camDist = length(relPos);
					cameraDist = camDist / FAR_CHUNKS_DISTANCE;
				#endif
			#endif
			float len = cameraDepth / RENDER_DISTANCE;
			#ifdef ALLOW_FADE
				len += CURRENT_COLOR.r;
			#endif
				fogColor.rgb = FOG_COLOR.rgb;
			fogColor.a = clamp((len - FOG_CONTROL.x) / (FOG_CONTROL.y - FOG_CONTROL.x), 0.0, 1.0);
		#endif
	#endif
}
