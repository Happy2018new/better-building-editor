#version 300 es
#define MCPE_NETEASE
#define MAT4 highp mat4
#define POS4 highp vec4
#define POS3 highp vec3
#define USE_SKINNING
#define NETEASE_SKINNING
#define USE_INSTANCE
// __multiversion__
precision highp float;
precision highp int;
#ifndef NETEASE_VERTEX_COMMON_H
#define NETEASE_VERTEX_COMMON_H
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
attribute float BONEID_0;
#endif

#ifdef PET_DISTANCE_ALPHA
	varying float cameraDistance;
#endif

#ifdef VIP_MOUNT_ALPHA
	varying float cameraDistToMount;
#endif

#ifdef USE_OVERLAY
	// When drawing horses on specific android devices, overlay color ends up being garbage data.
	// Changing overlay color to high precision appears to fix the issue on devices tested
	varying highp vec4 overlayColor;
#endif

#ifdef GLINT
	varying vec2 layer1UV;
	varying vec2 layer2UV;
	varying vec4 tileLightColor;
	varying vec4 glintColor;
#endif

#ifdef RNGL_LIGHT
	uniform vec4 HIDE_COLOR;
#endif

#ifdef USE_UV_FRAME_ANIM
	uniform vec4 UV_FRAME_ANIM_PARAM;	//(gridRowInverse, gridColInverse, gridCol, curFrame)
#endif
/**************** Preset Variables End ****************/


/**************** Preset Functions Begin ****************/
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

vec2 _calculateFrameAnimUV(vec2 uv, float gridRowInverse, float gridColInverse, float gridCol, float curFrame) {
	float curRow = floor(curFrame * gridColInverse + 0.1);
	float curCol = curFrame - curRow * gridCol;
	return (uv + vec2(curCol, curRow)) * vec2(gridColInverse, gridRowInverse);
}

float _lightIntensity(vec4 position, vec4 normal) {
#if defined(RNGL_UNLIT) || !defined(FANCY)
	return 1.0;
#endif

	const float AMBIENT = 0.45;
	const float XFAC = -0.1;
	const float ZFAC = 0.1;

	vec3 N = normalize((WORLD * normal).xyz);

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
#ifdef LIGHT_IN_PAPERDOLL
	float bias = 0.0;
#else
	float bias = 0.2;
#endif
	return dLight * (1.0 - AMBIENT - bias) + AMBIENT + 0.2;  // origin range [0.65, 1.0]
#else
	float yLight = (1.0+N.y) * 0.5;
	return yLight * (1.0-AMBIENT) + N.x*N.x * XFAC + N.z*N.z * ZFAC + AMBIENT;
#endif // RNGL_LIGHT
}
/**************** Preset Functions End ****************/


void getEntitySpacePositionAndNormal(out POS4 pos, out POS4 normal) {
#ifdef USE_SKINNING
	#ifdef NETEASE_SKINNING
		MAT4 boneMat = GetBoneMatForNetease(int(BONEID_0));
		pos = boneMat * POSITION;
		normal = boneMat * NORMAL;
		#ifdef USE_INSTANCE
			MAT4 instanceMat = GetInstanceWorldMatForNetease();
			pos = instanceMat * pos;
			normal = instanceMat * normal;
		#endif
	#else
		#if defined(LARGE_VERTEX_SHADER_UNIFORMS)
			pos = BONES[int(BONEID_0)] * POSITION;
			normal = BONES[int(BONEID_0)] * NORMAL;
		#else
			pos = BONE * POSITION;
			normal = BONE * NORMAL;
		#endif
	#endif // NETEASE_SKINNING
#else
	pos = POSITION;
	normal = NORMAL * vec4(1.0, 1.0, 1.0, 0.0);
	return;
#endif // USE_SKINNING
}

void applyUVAnim(inout vec2 uv) {
#ifdef USE_UV_FRAME_ANIM
	uv = _calculateFrameAnimUV(uv, UV_FRAME_ANIM_PARAM.x, UV_FRAME_ANIM_PARAM.y, UV_FRAME_ANIM_PARAM.z, UV_FRAME_ANIM_PARAM.w);
#endif
}

vec4 getLightColor(POS4 entitySpacePosition, POS4 entitySpaceNormal) {
	float intensity = _lightIntensity(entitySpacePosition, entitySpaceNormal);
#ifdef USE_OVERLAY
	intensity += OVERLAY_COLOR.a * 0.35;
#endif
	return vec4(vec3(intensity) * TILE_LIGHT_COLOR.xyz, 1.0);
}

vec4 getFogColor(vec4 projSpacePos) {
	float fogAlpha = ((projSpacePos.z / RENDER_DISTANCE) - FOG_CONTROL.x) / (FOG_CONTROL.y - FOG_CONTROL.x);
	return vec4(FOG_COLOR.rgb, clamp(fogAlpha, 0.0, 1.0));
}

void calculateOverlayColor() {
#ifdef USE_OVERLAY
	overlayColor = OVERLAY_COLOR;
#endif
}

void calculateGlint() {
#ifdef GLINT
	glintColor = GLINT_COLOR;
	layer1UV = _calculateLayerUV(UV_OFFSET.x, UV_ROTATION.x);
	layer2UV = _calculateLayerUV(UV_OFFSET.y, UV_ROTATION.y);
	tileLightColor = TILE_LIGHT_COLOR;
#endif
}

void neteaseModelCommonVert() {
#ifdef PET_DISTANCE_ALPHA
	cameraDistance = length(VIEW_POS.xyz - (WORLD * vec4(0.0, 0.0, 0.0, 1.0)).xyz);
#endif

#ifdef VIP_MOUNT_ALPHA
	const vec3 VIP_MOUNT_OFFSET = vec3(0.0, 1.5, 0.0);
	cameraDistToMount = length(VIEW_POS.xyz - ((WORLD * vec4(0.0, 0.0, 0.0, 1.0)).xyz + VIP_MOUNT_OFFSET));
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

#endif // NETEASE_VERTEX_COMMON_H

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


varying highp vec2 portalUv;
varying highp float portalVisible;
varying highp float portalClip;
varying vec2 colorLookupUV;
varying highp vec2 parallaxUV;
varying lowp vec4 encodedPlane;
#ifdef FOG
varying vec4 fogColor;
#endif
void main() {
    float slot = floor(POSITION.x / 2.0);
    float face = floor(POSITION.y / 2.0);
    float u = mod(POSITION.x,2.0);
    float v = mod(POSITION.y,2.0);
    float code;
    vec2 pairCodes;
    if (slot < 0.5) { code=EXTRA_VECTOR1.x; pairCodes=EXTRA_VECTOR2.xy; }
    else if (slot < 1.5) { code=EXTRA_VECTOR1.y; pairCodes=EXTRA_VECTOR2.zw; }
    else if (slot < 2.5) { code=EXTRA_VECTOR1.z; pairCodes=EXTRA_VECTOR3.xy; }
    else { code=EXTRA_VECTOR1.w; pairCodes=EXTRA_VECTOR3.zw; }
    float address = mod(code,64.0);
    float faces = mod(floor(code/64.0),64.0);
    vec4 heights=vec4(mod(pairCodes.x,256.0),floor(pairCodes.x/256.0),
                       mod(pairCodes.y,256.0),floor(pairCodes.y/256.0))/255.0;
    vec3 cell=vec3(mod(address,4.0),floor(address/16.0),mod(floor(address/4.0),4.0));
    vec3 point;
    if (face < 0.5) {
        point=vec3(u,mix(mix(heights.x,heights.y,u),mix(heights.w,heights.z,u),v),v);
        portalUv=vec2(u,v);
    } else if (face > 4.5) {
        point=vec3(1.0-u,0.0,v);
        portalUv=vec2(u,v);
    } else {
        float left;
        float right;
        if (face < 1.5) { left=heights.x; right=heights.y; }
        else if (face < 2.5) { left=heights.z; right=heights.w; }
        else if (face < 3.5) { left=heights.w; right=heights.x; }
        else { left=heights.y; right=heights.z; }
        float height=v*mix(left,right,u);
        if (face < 1.5) point=vec3(u,height,0.0);
        else if (face < 2.5) point=vec3(1.0-u,height,1.0);
        else if (face < 3.5) point=vec3(0.0,height,1.0-u);
        else point=vec3(1.0,height,u);
        portalUv=vec2(u,1.0-height);
    }
    portalVisible=mod(floor(faces/pow(2.0,face)),2.0);
    bool payloadValid=abs(EXTRA_VECTOR4.x-39686.0)<0.25 || mod(EXTRA_VECTOR4.x,256.0)==134.0;
    if (!payloadValid || floor(code/4096.0)>0.5) portalVisible=0.0;
    vec3 localPoint=cell+point-vec3(2.0);
    vec4 entityPoint=vec4(localPoint,1.0);
    
    #if defined(USE_SKINNING) && defined(NETEASE_SKINNING)
    entityPoint.z=-entityPoint.z;
    entityPoint=GetBoneMatForNetease(int(BONEID_0))*entityPoint;
#ifdef USE_INSTANCE
    entityPoint=GetInstanceWorldMatForNetease()*entityPoint;
#endif
#endif
    gl_Position=WORLDVIEWPROJ*entityPoint;
    // The native block renderer supplies these through COLOR/UV attributes.
    // Our mesh supplies the same logical fields through its decoded payload.
    float layerIndex=POSITION.z;
    float planeDistance=layerIndex>31.0 ? 32.0 : floor(layerIndex*(255.0/16.0))*(32.0/255.0);
    vec3 planeNormal=NORMAL.xyz;
    vec3 viewRay=(WORLD*entityPoint).xyz;
    float denominator=dot(viewRay,planeNormal);
    // Only an exactly edge-on face needs a finite diagnostic guard.
    if(abs(denominator)<0.00001) denominator=denominator<0.0 ? -0.00001 : 0.00001;
    float t=dot(viewRay-planeDistance*planeNormal,planeNormal)/denominator;
    vec3 parallaxPositionInWorld=t*viewRay+VIEW_POS;
    vec3 normalMask=floor(abs(planeNormal)+vec3(0.5));
    vec2 raycastUV=parallaxPositionInWorld.yz*normalMask.x+
                   parallaxPositionInWorld.xz*normalMask.y+
                   parallaxPositionInWorld.xy*normalMask.z;
    raycastUV/=16.0;
    const float rotor=3.1415926535897*(5.0/7.0);
    float rotS=sin(planeDistance*rotor);
    float rotC=cos(planeDistance*rotor);
    parallaxUV=mat2(vec2(rotC,rotS),vec2(-rotS,rotC))*raycastUV;
    parallaxUV+=vec2(rotC,rotS)*planeDistance;
    parallaxUV.y+=TIME/256.0;
    float colorIndex=15.0-layerIndex;
    colorLookupUV=(vec2(mod(colorIndex,4.0),mod(floor(colorIndex/4.0),4.0))+0.5)/4.0;
    encodedPlane=vec4((planeNormal+vec3(1.0))*0.5,planeDistance/32.0);
    #ifdef FOG
    fogColor=vec4(0.0);
    #endif
    if(portalVisible<0.5) gl_Position=vec4(2.0,2.0,2.0,1.0);
    portalClip=-1.0;
    
    gl_PointSize=1.0;
}
