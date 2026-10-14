"""Shared hinged book geometry, expressed in the native 64x32 atlas layout.

The two page blocks rotate about the binding, with their covers attached to
opposite ends of the spine. Renderer poses are separate from that construction.
Dimensions and pose references are recorded in the R17 book evidence notes.
"""
import math

GEOMETRY_VERSION=4


def turn(point,axis,angle):
    """Right-handed rotation, retaining the same convention on all axes."""
    a,b=((1,2),(2,0),(0,1))[axis]
    result=list(point);c,s=math.cos(angle),math.sin(angle)
    result[a]=point[a]*c-point[b]*s
    result[b]=point[a]*s+point[b]*c
    return result


def components(opening):
    """Pixel-space boxes and local hinge transforms; no world offsets."""
    hinge=math.sin(opening)
    return (
        ('cover_left',(-6.,-5.,-.005),(6.,10.,.005),(0.,0.),math.pi+opening,(0.,0.,-1.)),
        ('cover_right',(0.,-5.,-.005),(6.,10.,.005),(16.,0.),-opening,(0.,0.,1.)),
        ('spine',(-1.,-5.,0.),(2.,10.,.005),(12.,0.),math.pi/2.,(0.,0.,0.)),
        ('pages_left',(0.,-4.,-.99),(5.,8.,1.),(0.,10.),opening,(hinge,0.,0.)),
        ('pages_right',(0.,-4.,-.01),(5.,8.,1.),(12.,10.),-opening,(hinge,0.,0.)),
    )+(() if opening==0. else (
        ('page_turn_left',(0.,-4.,0.),(5.,8.,.005),(24.,10.),opening*.8,(hinge,0.,0.)),
        ('page_turn_right',(0.,-4.,0.),(5.,8.,.005),(24.,10.),-opening*.8,(hinge,0.,0.)),
    ))


def _texels(start,length):
    """Sample complete artwork texels, including subpixel-thickness edges."""
    lo,hi=sorted((start,start+length))
    first=math.floor(lo+.5)+.5
    last=max(first,math.floor(hi+.5)-.5)
    return (last,first) if length<0. else (first,last)


def _faces(origin,size,uv):
    """Box net as six independent planar mappings (origin, u-axis, v-axis)."""
    x,y,z=origin;w,h,d=size;u,v=uv
    # Geometry uses model Y; texture V increases from the model's low-Y edge.
    return (
        ((x,y+h,z),(w,0,0),(0,0,d),(0,1,0),(u+d+w,v+d,w,-d)),
        ((x+w,y,z),(-w,0,0),(0,0,d),(0,-1,0),(u+d+w,v,-w,d)),
        ((x,y,z),(w,0,0),(0,h,0),(0,0,-1),(u+d,v+d,w,h)),
        ((x+w,y,z+d),(-w,0,0),(0,h,0),(0,0,1),(u+w+2*d,v+d,w,h)),
        ((x,y,z+d),(0,0,-d),(0,h,0),(-1,0,0),(u,v+d,d,h)),
        ((x+w,y,z),(0,0,d),(0,h,0),(1,0,0),(u+d+w,v+d,d,h)),
    )


def shape(family,material_path):
    if family not in ('enchanting_table','lectern'):
        raise ValueError('Unknown book pose: '+str(family))
    opened=family=='lectern'
    opening=1.5 if opened else 0.
    tilt=math.radians(67.5 if opened else 80.)
    pivot_y=1.0625 if opened else .85
    vertices,indices=[],[]
    for name,origin,size,uv,yaw,offset in components(opening):
        for start,across,down,normal,rect in _faces(origin,size,uv):
            us=_texels(rect[0],rect[2]);vs=_texels(rect[1],rect[3])
            transformed_normal=turn(turn(normal,1,yaw),2,tilt)
            if opened:transformed_normal=turn(transformed_normal,1,-math.pi/2.)
            for slot in range(4):
                index=len(vertices)
                for a,b in ((0,0),(1,0),(1,1),(0,1)):
                    point=[start[i]+a*across[i]+b*down[i] for i in range(3)]
                    point=turn(point,1,yaw)
                    point=[(point[i]+offset[i])/16. for i in range(3)]
                    if opened:point[1]-=.125
                    point=turn(point,2,tilt)
                    if opened:point=turn(point,1,-math.pi/2.)
                    point[1]+=pivot_y
                    point[2]+=slot*4.+1.
                    vertices.append({'pos':point,'normal':transformed_normal,
                                     'uvcoord':(us[a]/64.,vs[b]/32.),'weight':[['root',1.]]})
                indices.extend(((index,index+2,index+1),(index,index+3,index+2)))
    return {'mesh':[{'material':material_path,'vertices':vertices,'indices':indices}]}
