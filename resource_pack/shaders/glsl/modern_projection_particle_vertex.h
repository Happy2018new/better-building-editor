// Native billboard particles render after the sky and translucent terrain.
// Keep the original GPU paths/palettes; UV and COLOR carry their parameters.
attribute highp vec4 POSITION;
attribute highp vec2 TEXCOORD_0;
attribute highp vec4 COLOR;
vec3 nativeOrigin;
float nativeId;
vec2 nativeCorner;
vec4 EXTRA_ACTOR_UNIFORM1;
vec4 EXTRA_ACTOR_UNIFORM2;
vec4 EXTRA_ACTOR_UNIFORM3;
vec4 EXTRA_ACTOR_UNIFORM4;
void nativeCarrier(vec2 code){
 const float radius=.000001;
 // Static four-code cells use corners .5/3; atlas inset and UNORM16
 // quantization keep them on their own side of the threshold at 2.
 nativeCorner=step(vec2(2.),mod(code,4.))*2.-1.;
 vec3 right=normalize(vec3(WORLDVIEWPROJ[0][0],WORLDVIEWPROJ[1][0],WORLDVIEWPROJ[2][0]));
 vec3 up=normalize(vec3(WORLDVIEWPROJ[0][1],WORLDVIEWPROJ[1][1],WORLDVIEWPROJ[2][1]));
 // Only visible, tiny carriers reach this function. A separate hidden
 // sentinel supplies the native emitter bounds without affecting positions.
 nativeOrigin=POSITION.xyz-right*nativeCorner.x*radius+up*nativeCorner.y*radius;
}
#ifdef AURA_GLOW
bool nativeAura(){
 // Alpha zero is reserved for registration/cleanup. RGB metadata remains
 // valid while hidden; readiness never destroys a sentinel's address.
 if(COLOR.a*255.<.5)return false;
 vec2 code=TEXCOORD_0*65535.;
 vec2 data=floor(code/4.);
 vec4 bytes=COLOR*255.;
 float index=mod(data.x,256.);
 if(index>=176.)return false;
 nativeId=index<112.?index+128.:index+352.;
 float from=floor(data.x/256.)+mod(data.y,4.)*64.;
 float to=mod(floor(data.y/4.),256.);
 float modes=floor(data.y/1024.);
 // Each moving velocity stays inside its own fixed 64-code interval.
 // Interpolation cannot carry into the birth-progress metadata above it.
 vec3 metadata=floor((bytes.rgb+vec3(.5))/64.);
 vec3 velocity=(clamp(bytes.rgb-metadata*64.,0.,62.)-vec3(31.))*(7./31.);
 float birth=dot(metadata,vec3(1.,4.,16.))/63.;
 float switching=clamp((bytes.a-1.)/254.,0.,1.);
 float entered=min(1.,birth+switching*(.7/.65));
 float tool=mod(modes,2.);
 float moving=mod(floor(modes/2.),2.);
 float thirdPerson=floor(modes/4.);
 EXTRA_ACTOR_UNIFORM1=vec4(entered,tool,moving,thirdPerson);
 EXTRA_ACTOR_UNIFORM2=vec4(velocity,length(velocity));
 EXTRA_ACTOR_UNIFORM3=vec4(from,to,switching,1.);
 nativeCarrier(code);
 return true;
}
#else
bool nativeSurvey(){
 if(COLOR.a*255.<.5)return false;
 vec2 code=TEXCOORD_0*65535.;
 vec2 data=floor(code/4.);
 vec4 bytes=COLOR*255.;
 float metadata=floor((bytes.r+.5)/64.);
 nativeId=floor(data.y/64.)+floor(data.x/8192.)*256.+floor(metadata/2.)*512.;
#ifdef SURVEY_STRIKE
 if(nativeId>=328.)return false;
#else
 if(nativeId>=971.)return false;
#endif
 float theme=mod(metadata,2.);
 float brightness=bytes.g/170.;
 float density=.3+clamp(bytes.r-metadata*64.,0.,60.)/40.;
 float orbit=bytes.b/85.;
 float entered=clamp((bytes.a-1.)/254.,0.,1.);
 float sizeXY=mod(data.x,8192.);
#ifdef SURVEY_STRIKE
 nativeId=nativeId<149.?nativeId:nativeId+184.;
 vec3 size=vec3(1.);
 density=sizeXY;
#else
 nativeId=nativeId<449.?nativeId:nativeId+1584.;
 vec3 size=vec3(mod(sizeXY,64.)+1.,floor(sizeXY/64.)+1.,mod(data.y,64.)+1.);
#endif
 nativeCarrier(code);
 EXTRA_ACTOR_UNIFORM1=vec4(size,0.);
 EXTRA_ACTOR_UNIFORM2=vec4(0.);
 EXTRA_ACTOR_UNIFORM3=vec4(entered,brightness,theme+.1,orbit);
 EXTRA_ACTOR_UNIFORM4=vec4(-nativeOrigin,density);
 return true;
}
#endif
