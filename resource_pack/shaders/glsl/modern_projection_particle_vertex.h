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
 // Four-texel-wide quads leave guard space around both corners in the
 // normalized ushort UV buffer instead of relying on adjacent UV bits.
 nativeCorner=step(vec2(4.),mod(code,8.))*2.-1.;
 vec3 right=normalize(vec3(WORLDVIEWPROJ[0][0],WORLDVIEWPROJ[1][0],WORLDVIEWPROJ[2][0]));
 vec3 up=normalize(vec3(WORLDVIEWPROJ[0][1],WORLDVIEWPROJ[1][1],WORLDVIEWPROJ[2][1]));
 // Only visible, tiny carriers reach this function. A separate hidden
 // sentinel supplies the native emitter bounds without affecting positions.
 nativeOrigin=POSITION.xyz-right*nativeCorner.x*radius+up*nativeCorner.y*radius;
}
#ifdef AURA_GLOW
bool nativeAura(){
 // Before Python commits ready=1, every COLOR channel is zero. In this
 // state the sentinel's high ID bits are absent, so reject before decoding.
 if(dot(COLOR,COLOR)==0.)return false;
 vec2 code=TEXCOORD_0*65535.;
 vec2 data=floor(code/8.);
 vec4 bytes=floor(COLOR*255.+.5);
 float index=mod(data.x,256.);
 if(index>=176.)return false;
 nativeId=index<112.?index+128.:index+352.;
 float from=floor(data.x/256.)+mod(data.y,8.)*32.;
 float to=mod(floor(data.y/8.),256.);
 vec3 velocity=vec3(floor(data.y/2048.)+mod(bytes.r,16.)*4.,
                    floor(bytes.r/16.)+mod(bytes.g,4.)*16.,floor(bytes.g/4.));
 velocity=(velocity-vec3(31.))*(7./31.);
 float entered=mod(bytes.b,128.)/127.;
 float switching=(floor(bytes.b/128.)+mod(bytes.a,32.)*2.)/63.;
 float tool=mod(floor(bytes.a/32.),2.);
 float moving=mod(floor(bytes.a/64.),2.);
 float thirdPerson=floor(bytes.a/128.);
 EXTRA_ACTOR_UNIFORM1=vec4(entered,tool,moving,thirdPerson);
 EXTRA_ACTOR_UNIFORM2=vec4(velocity,length(velocity));
 EXTRA_ACTOR_UNIFORM3=vec4(from,to,switching,1.);
 nativeCarrier(code);
 return true;
}
#else
bool nativeSurvey(){
 if(dot(COLOR,COLOR)==0.)return false;
 vec2 code=TEXCOORD_0*65535.;
 vec2 data=floor(code/8.);
 vec4 bytes=floor(COLOR*255.+.5);
 nativeId=floor(data.y/64.)+mod(bytes.r,8.)*128.;
#ifdef SURVEY_STRIKE
 if(nativeId>=328.)return false;
#else
 if(nativeId>=971.)return false;
#endif
 float theme=mod(floor(bytes.r/8.),2.);
 float brightness=(floor(bytes.r/16.)+mod(bytes.g,8.)*16.)/84.;
 float density=(floor(bytes.g/8.)+mod(bytes.b,4.)*32.)/70.;
 float orbit=(floor(bytes.b/4.)+mod(bytes.a,4.)*64.)/85.;
 float entered=floor(bytes.a/4.)/63.;
#ifdef SURVEY_STRIKE
 nativeId=nativeId<149.?nativeId:nativeId+184.;
 vec3 size=vec3(1.);
 density=data.x;
#else
 nativeId=nativeId<449.?nativeId:nativeId+1584.;
 vec3 size=vec3(mod(data.x,64.)+1.,floor(data.x/64.)+1.,mod(data.y,64.)+1.);
#endif
 nativeCarrier(code);
 EXTRA_ACTOR_UNIFORM1=vec4(size,0.);
 EXTRA_ACTOR_UNIFORM2=vec4(0.);
 EXTRA_ACTOR_UNIFORM3=vec4(entered,brightness,theme+.1,orbit);
 EXTRA_ACTOR_UNIFORM4=vec4(-nativeOrigin,density);
 return true;
}
#endif
