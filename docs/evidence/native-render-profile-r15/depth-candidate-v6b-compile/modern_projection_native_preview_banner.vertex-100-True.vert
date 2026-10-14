#version 100
#define MCPE_NETEASE
#define MAT4 highp mat4
#define POS4 highp vec4
#define USE_SKINNING
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
#define attribute in
#define varying out

#ifdef MSAA_FRAMEBUFFER_ENABLED
#define _centroid centroid
#else
#define _centroid
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

#ifndef _UNIFORM_ENTITY_CONSTANTS_H
#define _UNIFORM_ENTITY_CONSTANTS_H
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
uniform ActorConstants {
#endif
// BEGIN_UNIFORM_BLOCK(ActorConstants) - unfortunately this macro does not work on old Amazon platforms so using above 3 lines instead
UNIFORM vec4 OVERLAY_COLOR;
UNIFORM vec4 TILE_LIGHT_COLOR;
UNIFORM vec2 TILE_LIGHT_INTENSITY;
UNIFORM vec4 CHANGE_COLOR;
UNIFORM vec4 GLINT_COLOR;
UNIFORM vec4 UV_ANIM;
UNIFORM vec2 UV_OFFSET;
UNIFORM vec2 UV_ROTATION;
UNIFORM vec2 GLINT_UV_SCALE;
UNIFORM vec4 MULTIPLICATIVE_TINT_CHANGE_COLOR;
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

#ifndef _UNIFORM_BANNER_CONSTANTS_H
#define _UNIFORM_BANNER_CONSTANTS_H
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
uniform BannerConstants {
#endif
// BEGIN_UNIFORM_BLOCK(BannerConstants) - unfortunately this macro does not work on old Amazon platforms so using above 3 lines instead
UNIFORM vec4 BANNER_COLORS[7];
UNIFORM vec4 BANNER_UV_OFFSETS_AND_SCALES[7];
END_UNIFORM_BLOCK

#endif

#ifdef USE_SKINNING
#ifndef _UNIFORM_ANIMATION_CONSTANTS_H
#define _UNIFORM_ANIMATION_CONSTANTS_H
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
layout(binding = 4) uniform AnimationConstants {
#endif
// BEGIN_UNIFORM_BLOCK(AnimationConstants) - unfortunately this macro does not work on old Amazon platforms so using above 3 lines instead
#if defined(LARGE_VERTEX_SHADER_UNIFORMS)
UNIFORM MAT4 BONES[8];
#else
UNIFORM MAT4 BONE;
#endif
END_UNIFORM_BLOCK

#if defined(USE_INSTANCE) && defined(NTES_ANIMATED_MODEL_BATCH_TEXTURE)
LAYOUT_BINDING(6) uniform highp sampler2D TEXTURE_6;
UNIFORM highp vec4 INSTANCE_TEXTURE_INFO_50;
#elif defined(USE_INSTANCE) && defined(NTES_ANIMATED_MODEL_BATCH)
#ifndef NTES_BATCH_BONES
#ifdef NTES_BATCH_LOW
#define NTES_BATCH_BONES 96
#define NTES_BATCH_INSTANCES 24
#else
#define NTES_BATCH_BONES 224
#define NTES_BATCH_INSTANCES 50
#endif
#endif
#ifndef NTES_BATCH_BONE_BASE_VECTORS
#define NTES_BATCH_BONE_BASE_VECTORS ((NTES_BATCH_INSTANCES + 3) / 4)
#endif
UNIFORM mat3x4 BONES_70[NTES_BATCH_BONES];
UNIFORM mat4x3 INSTANCE_WORLDMAT_50[NTES_BATCH_INSTANCES];
UNIFORM vec4 INSTANCE_BONE_BASE_50[NTES_BATCH_BONE_BASE_VECTORS];
#else
UNIFORM mat3x4 BONES_70[70];
#ifdef USE_INSTANCE
UNIFORM mat4x3 INSTANCE_WORLDMAT_50[50];
#endif
#endif

mat4 mat3x4ToMat4(mat3x4 boneMat3x4){
		mat4 boneMat4x4;

		boneMat4x4[0] = boneMat3x4[0];
		boneMat4x4[1] = boneMat3x4[1];
		boneMat4x4[2] = boneMat3x4[2];
		boneMat4x4[3] = vec4(0, 0, 0, 1);

		return boneMat4x4;
}

#if defined(USE_INSTANCE) && defined(NTES_ANIMATED_MODEL_BATCH_TEXTURE)
highp vec4 NtesFetchAnimationBatchTexel(highp int texelIndex) {
	highp int textureWidth = int(INSTANCE_TEXTURE_INFO_50.x + 0.5);
	highp int y = texelIndex / textureWidth;
	highp int x = texelIndex - y * textureWidth;
	return texelFetch(TEXTURE_6, ivec2(x, y), 0);
}
#endif

mat4 GetBoneMatForNetease(int boneId){
#if defined(USE_INSTANCE) && defined(NTES_ANIMATED_MODEL_BATCH_TEXTURE)
	highp int atlasBaseTexel = int(INSTANCE_TEXTURE_INFO_50.y + 0.5);
	highp int instanceTexelBase = atlasBaseTexel + gl_InstanceID * 4;
	highp vec4 instanceBase = NtesFetchAnimationBatchTexel(instanceTexelBase);
	highp int boneTexelBase = atlasBaseTexel + int(instanceBase.w + 0.5) + boneId * 3;
	mat3x4 boneMat = mat3x4(
		NtesFetchAnimationBatchTexel(boneTexelBase),
		NtesFetchAnimationBatchTexel(boneTexelBase + 1),
		NtesFetchAnimationBatchTexel(boneTexelBase + 2));
	return transpose(mat3x4ToMat4(boneMat));
#else
#if defined(USE_INSTANCE) && defined(NTES_ANIMATED_MODEL_BATCH)
	int boneBaseVecIndex = gl_InstanceID / 4;
	int boneBaseComponent = gl_InstanceID - boneBaseVecIndex * 4;
	vec4 boneBasePacked = INSTANCE_BONE_BASE_50[boneBaseVecIndex];
	float boneBase = boneBaseComponent == 0 ? boneBasePacked.x : (boneBaseComponent == 1 ? boneBasePacked.y : (boneBaseComponent == 2 ? boneBasePacked.z : boneBasePacked.w));
	boneId += int(boneBase + 0.5);
#endif
    return transpose(mat3x4ToMat4(BONES_70[boneId]));
#endif
}

#ifdef USE_INSTANCE
mat4 mat4x3ToMat4(mat4x3 worldMat4x3){
	mat4 worldMat4x4;
	worldMat4x4[0] = vec4(worldMat4x3[0], 0);
	worldMat4x4[1] = vec4(worldMat4x3[1], 0);
	worldMat4x4[2] = vec4(worldMat4x3[2], 0);
	worldMat4x4[3] = vec4(worldMat4x3[3], 1);
	return worldMat4x4;
}

mat4 GetInstanceWorldMatForNetease(){
#if defined(NTES_ANIMATED_MODEL_BATCH_TEXTURE)
	highp int instanceTexelBase = int(INSTANCE_TEXTURE_INFO_50.y + 0.5) + gl_InstanceID * 4;
	vec4 c0 = NtesFetchAnimationBatchTexel(instanceTexelBase);
	vec4 c1 = NtesFetchAnimationBatchTexel(instanceTexelBase + 1);
	vec4 c2 = NtesFetchAnimationBatchTexel(instanceTexelBase + 2);
	vec4 c3 = NtesFetchAnimationBatchTexel(instanceTexelBase + 3);
	c0.w = 0.0;
	c3.w = 1.0;
	return mat4(c0, c1, c2, c3);
#else
	return mat4x3ToMat4(INSTANCE_WORLDMAT_50[gl_InstanceID]);
#endif
}
#endif

#endif

#endif

attribute mediump vec4 POSITION;
attribute vec2 TEXCOORD_0;
attribute vec4 NORMAL;
attribute vec4 COLOR;
#if defined(USE_SKINNING)
#ifdef MCPE_PLATFORM_NX
attribute uint BONEID_0;
#else
attribute float BONEID_0;
#endif
#endif

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

const float AMBIENT = 0.45;

const float XFAC = -0.1;
const float ZFAC = 0.1;

float lightIntensity() {
#ifdef FANCY
#ifdef USE_SKINNING
#if defined(LARGE_VERTEX_SHADER_UNIFORMS)
    vec3 N = normalize(BONES[int(BONEID_0)] * NORMAL).xyz;
#else
    vec3 N = normalize(BONE * NORMAL).xyz;
#endif
#else
    vec3 N = normalize(WORLD * NORMAL).xyz;
#endif

    N.y *= TILE_LIGHT_COLOR.w; //TILE_LIGHT_COLOR.w contains the direction of the light

    //take care of double sided polygons on materials without culling
#ifdef FLIP_BACKFACES
#ifdef USE_SKINNING
#if defined(LARGE_VERTEX_SHADER_UNIFORMS)
    vec3 viewDir = normalize((BONES[int(BONEID_0)] * POSITION).xyz);
#else
	vec3 viewDir = normalize((BONE * POSITION).xyz);
#endif
#else
    vec3 viewDir = normalize((WORLD * POSITION).xyz);
#endif
    if( dot(N, viewDir) > 0.0 ) {
        N *= -1.0;
    }
#endif

    float yLight = (1.0+N.y) * 0.5;
    return yLight * (1.0-AMBIENT) + N.x*N.x * XFAC + N.z*N.z * ZFAC + AMBIENT;
#else
    return 1.0;
#endif
}



varying highp float nativePreviewClip;
// Terrain and native actors in one PaperDoll must share the same depth scale.
// This branch is restricted to the existing tagged orthographic editor packet.
void applyPreviewActorDepth(inout POS4 projected, POS4 localPosition) {
    
    nativePreviewClip=-1.0;
    float tag = floor(CURRENT_COLOR.r*255.0+0.5);
    if (abs(PROJ[3][3]) > 0.5 && tag >= 209.0 && tag <= 222.0) {
        bool layoutPacket = fract(CURRENT_COLOR.r*255.0) > 0.125;
        float distance = layoutPacket ?
            (floor(CURRENT_COLOR.b*65536.0+0.5)-32768.0)/64.0 :
            (floor(CURRENT_COLOR.g*255.0+0.5)*256.0+
             floor(CURRENT_COLOR.b*255.0+0.5)-32768.0)/64.0;
        vec3 viewZ = vec3(WORLDVIEW[0][2], WORLDVIEW[1][2], WORLDVIEW[2][2]);
        float clip = ((WORLDVIEW*localPosition).z+450.0)/max(length(viewZ),0.00001)*0.64+distance;
        nativePreviewClip=clip;
        float centerDepth = PROJ[2][2]*(-350.0)+PROJ[3][2];
        projected.z = (centerDepth+clip*PROJ[2][2]*0.04)/(1.0+abs(centerDepth));
    }
}

void main()
{
#ifdef USE_SKINNING
#if defined(LARGE_VERTEX_SHADER_UNIFORMS)
    POS4 localPosition = BONES[int(BONEID_0)] * POSITION;
    POS4 pos = WORLDVIEWPROJ * localPosition;
#else
	POS4 localPosition = BONE * POSITION;
    POS4 pos = WORLDVIEWPROJ * localPosition;
#endif
#else
    POS4 localPosition = POSITION;
    POS4 pos = WORLDVIEWPROJ * localPosition;
#endif
    applyPreviewActorDepth(pos,localPosition);
    gl_Position = pos;

#ifdef ENABLE_LIGHT
    float L = lightIntensity();
    light = vec4(vec3(L) * TILE_LIGHT_COLOR.xyz, 1.0);
#endif
   
	int frameIndex = int((COLOR.a * 255.0) + 0.5);
	uv.xy = (TEXCOORD_0.xy * BANNER_UV_OFFSETS_AND_SCALES[frameIndex].zw) + BANNER_UV_OFFSETS_AND_SCALES[frameIndex].xy;
	uv.zw = (TEXCOORD_0.xy * BANNER_UV_OFFSETS_AND_SCALES[0].zw) + BANNER_UV_OFFSETS_AND_SCALES[0].xy;

#ifndef DISABLE_TINTING
	color = BANNER_COLORS[frameIndex];
	color.a = 1.0;
	if (frameIndex > 0) {
		color.a = 0.0;
	}
#endif
    
#ifdef ENABLE_FOG
//fog
    fogColor.rgb = FOG_COLOR.rgb;
    fogColor.a = clamp(((pos.z / RENDER_DISTANCE) - FOG_CONTROL.x) / (FOG_CONTROL.y - FOG_CONTROL.x), 0.0, 1.0);
#endif
}