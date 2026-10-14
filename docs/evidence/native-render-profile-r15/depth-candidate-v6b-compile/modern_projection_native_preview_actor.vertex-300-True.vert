#version 300 es
#define MCPE_NETEASE
#define MAT4 highp mat4
#define POS4 highp vec4
#define USE_SKINNING
// __multiversion__
// Preserve the installed entity.vertex animation, lighting and UV contract.
precision highp float;
precision highp int;
#ifndef ENTITY_VERTEX_UTIL_H
#define ENTITY_VERTEX_UTIL_H
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

_centroid out highp vec2 uv;

#else

varying highp vec2 uv;

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
#line 12

/**************** Preset Variables Begin ****************/
attribute mediump vec4 POSITION;
attribute vec2 TEXCOORD_0;
attribute vec4 NORMAL;
#if defined(USE_SKINNING)
	#ifdef MCPE_PLATFORM_NX
		attribute uint BONEID_0;
	#else
		attribute float BONEID_0;
	#endif
#endif

#ifdef RNGL_LIGHT
uniform vec4 HIDE_COLOR;
#endif

#ifdef COLOR_BASED
	attribute vec4 COLOR;
	varying vec4 vertColor;
#endif

#ifdef USE_OVERLAY
	// When drawing horses on specific android devices, overlay color ends up being garbage data.
	// Changing overlay color to high precision appears to fix the issue on devices tested
	varying highp vec4 overlayColor;
#endif

#ifdef TINTED_ALPHA_TEST
	varying float alphaTestMultiplier;
#endif

#ifdef NETEASE_METALLIC
varying vec3 worldNormalM;
varying vec3 worldViewDirM;
varying vec3 worldLightDirM;
#endif

#ifdef USE_UV_FRAME_ANIM
uniform vec4 UV_FRAME_ANIM_PARAM;	//(gridRowInverse, gridColInverse, gridCol, curFrame)

vec2 calculateFrameAnimUV(vec2 uv, float gridRowInverse, float gridColInverse, float gridCol, float curFrame) {
	float curRow = floor(curFrame * gridColInverse + 0.1);
	float curCol = curFrame - curRow * gridCol;	
	return (uv + vec2(curCol, curRow)) * vec2(gridColInverse, gridRowInverse);
}
#endif

#ifdef GLINT
varying vec2 layer1UV;
varying vec2 layer2UV;
varying vec4 tileLightColor;
varying vec4 glintColor;
#endif
/**************** Preset Variables End ****************/

vec2 _calculateLayerUV(float offset, float rotation) {
	vec2 uv = TEXCOORD_0;
	uv -= 0.5;
	float rsin = sin(rotation);
	float rcos = cos(rotation);
	uv = mat2(rcos, -rsin, rsin, rcos) * uv;
	uv.x += offset;
	uv += 0.5;

	return uv * GLINT_UV_SCALE;
}

const float AMBIENT = 0.45;
const float XFAC = -0.1;
const float ZFAC = 0.1;
float _lightIntensity(vec4 position, vec4 normal) {
#if defined(RNGL_UNLIT) || !defined(FANCY)
	return 1.0;
#else
	vec3 N = normalize( (WORLD * normal).xyz );
	N.y *= TILE_LIGHT_COLOR.w; //TILE_LIGHT_COLOR.w contains the direction of the light

	//take care of double sided polygons on materials without culling
	#ifdef FLIP_BACKFACES
		vec3 viewDir = normalize((WORLD * position).xyz);
		if( dot(N, viewDir) > 0.0 )
			N *= -1.0;
	#endif

	#ifdef RNGL_LIGHT
		vec3 lightDir = normalize(HIDE_COLOR.xyz);  // light dir uses world coords
		float dLight = max(0.0, dot(N, lightDir));  // diffuse in directional light
		return dLight * (1.0-AMBIENT-0.2) + AMBIENT+0.2;  // origin range [0.65, 1.0]
	#else
		float yLight = (1.0+N.y) * 0.5;
		return yLight * (1.0-AMBIENT) + N.x*N.x * XFAC + N.z*N.z * ZFAC + AMBIENT;
	#endif // RNGL_LIGHT
#endif
}


vec4 getLightColor(vec4 entitySpacePosition, vec4 entitySpaceNormal) {
	float L = _lightIntensity(entitySpacePosition, entitySpaceNormal);

#ifdef USE_OVERLAY
	L += OVERLAY_COLOR.a * 0.35;
#endif

	return vec4(TILE_LIGHT_COLOR.xyz * L, 1.0);
}

void getEntitySpacePositionAndNormal(out POS4 entitySpacePosition, out POS4 entitySpaceNormal) {
#ifdef USE_SKINNING
	#ifdef NETEASE_SKINNING
		MAT4 boneMat = GetBoneMatForNetease(int(BONEID_0));
		entitySpacePosition = boneMat * POSITION;
		entitySpaceNormal = boneMat * NORMAL;
	#else
		#if defined(LARGE_VERTEX_SHADER_UNIFORMS)
			entitySpacePosition = BONES[int(BONEID_0)] * POSITION;
			entitySpaceNormal = BONES[int(BONEID_0)] * NORMAL;
		#else
			entitySpacePosition = BONE * POSITION;
			entitySpaceNormal = BONE * NORMAL;
		#endif
	#endif
#else
	entitySpacePosition = POSITION;
	entitySpaceNormal = NORMAL;
#endif
}

void applyUVAnim(inout vec2 uv) {
#ifdef USE_UV_ANIM
	uv = UV_ANIM.xy + (uv * UV_ANIM.zw);
#endif

#ifdef USE_UV_FRAME_ANIM
	uv = calculateFrameAnimUV(uv, UV_FRAME_ANIM_PARAM.x, UV_FRAME_ANIM_PARAM.y, UV_FRAME_ANIM_PARAM.z, UV_FRAME_ANIM_PARAM.w);	
#endif
}

void calculateGlint(){
#ifdef GLINT
	glintColor = GLINT_COLOR;
	layer1UV = _calculateLayerUV(UV_OFFSET.x, UV_ROTATION.x);
	layer2UV = _calculateLayerUV(UV_OFFSET.y, UV_ROTATION.y);
	tileLightColor = TILE_LIGHT_COLOR;
#endif
}

void calculateOverlayColor(){
#ifdef USE_OVERLAY
	overlayColor = OVERLAY_COLOR;
#endif
}

vec4 getFogColor(vec4 pos){
	float fogControl = ((pos.z / RENDER_DISTANCE) - FOG_CONTROL.x) / (FOG_CONTROL.y - FOG_CONTROL.x);
	return vec4(
		FOG_COLOR.rgb,
		clamp(fogControl, 0.0, 1.0)
	);
}

void entityCommonVert() {
#ifdef TINTED_ALPHA_TEST
	alphaTestMultiplier = OVERLAY_COLOR.a;
#endif

#ifdef COLOR_BASED
	vertColor = COLOR;
#endif
}

vec3 getViewDir(POS4 entitySpacePosition) {
#if defined(RNGL_REFLECT)
	vec3 worldPos = (WORLD * entitySpacePosition).xyz;
	return worldPos.xyz - VIEW_POS.xyz;
#else
	return vec3(0.0, 1.0, 0.0);
#endif
}

void calculateSpecificProcess(inout POS4 entitySpacePosition, in POS4 entitySpaceNormal) {
#ifdef NETEASE_DRAWLINE
	// 放大轮廓
	entitySpacePosition = entitySpacePosition + normalize(entitySpaceNormal) * OVERLAY_COLOR.a;
#endif
#ifdef NETEASE_METALLIC
	worldNormalM = (WORLD * entitySpaceNormal).xyz;
	worldViewDirM = VIEW_POS - (WORLD * entitySpacePosition).xyz;
	worldLightDirM = SUN_DIR.xyz; 
#endif
} 

#endif // ENTITY_VERTEX_UTIL_H

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


varying vec4 light;
varying vec4 fogColor;
#ifdef RNGL_LOCAL_LIGHT
varying vec4 worldSpacePos;
varying vec4 worldSpaceNormal;
#endif


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

void main() {
    POS4 entitySpacePosition, entitySpaceNormal;
    getEntitySpacePositionAndNormal(entitySpacePosition, entitySpaceNormal);
    calculateOverlayColor();
    calculateGlint();
    entityCommonVert();
    light = getLightColor(entitySpacePosition, entitySpaceNormal);
    uv = TEXCOORD_0;
    applyUVAnim(uv);
    calculateSpecificProcess(entitySpacePosition, entitySpaceNormal);
    POS4 projSpacePos = WORLDVIEWPROJ*entitySpacePosition;
    applyPreviewActorDepth(projSpacePos, entitySpacePosition);
    gl_Position = projSpacePos;
    #ifdef RNGL_LOCAL_LIGHT
    worldSpacePos = WORLD*entitySpacePosition;
    worldSpaceNormal = WORLD*entitySpaceNormal;
    worldSpaceNormal.xyz = normalize(worldSpaceNormal.xyz);
    #endif
    fogColor = getFogColor(projSpacePos);
}
