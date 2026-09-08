"""Reusable mesh helpers. They build actual editable solids, not generated illustrations."""
import io,math,copy
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import box as sbox,Polygon
from glb_edit import prism,beveled_prism,T
g=None
changes=[]
newgroups={}
original_nodes=0
def setup(model):
    global g,changes,newgroups,original_nodes
    g=model;changes=[];newgroups={};original_nodes=len(g.j['nodes'])
def group(name,parent=1,note=''):
    if name in g.ids:return g.ids[name]
    n=len(g.j['nodes']);g.j['nodes'].append({'name':name,'children':[],'extras':{'scope':'v13 animated vehicle/city/camera additions','note':note,'dimensions':'approximate, not surveyed'}})
    g.j['nodes'][parent].setdefault('children',[]).append(n);g.parent[n]=parent;g.ids[name]=n;newgroups[name]=n;return n

def remove_prefix(prefix):
    for n in g.j['nodes'][:original_nodes]:
        if 'mesh' in n and n['name'].startswith(prefix):
            g.remove(n['name']);changes.append(n['name'])

def material(name,color,rough=.5,metal=0,emission=None):
    m={'name':name,'pbrMetallicRoughness':{'baseColorFactor':[*color,1.0],'metallicFactor':metal,'roughnessFactor':rough}}
    if emission is not None:m['emissiveFactor']=list(emission)
    g.j['materials'].append(m);return len(g.j['materials'])-1

def texture_material(name,image,rough=.5,metal=0):
    bio=io.BytesIO();image.save(bio,format='PNG');dat=bio.getvalue()
    while len(g.data)%4:g.data+=b'\0'
    off=len(g.data);g.data+=dat
    bi=len(g.j['bufferViews']);g.j['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':len(dat)})
    ii=len(g.j['images']);g.j['images'].append({'name':name,'bufferView':bi,'mimeType':'image/png'})
    ti=len(g.j['textures']);g.j['textures'].append({'source':ii})
    mi=material(name,(1,1,1),rough,metal);g.j['materials'][mi]['pbrMetallicRoughness']['baseColorTexture']={'index':ti}
    return mi

def mesh(name,m,mat,parent,uv=None,smooth=False):
    if not isinstance(m,trimesh.Trimesh):m=trimesh.Trimesh(*m,process=False)
    v=np.asarray(m.vertices,dtype=float);f=np.asarray(m.faces,int)
    if smooth:
        no=np.asarray(m.vertex_normals,dtype=float)
    else:
        v=v[f.ravel()];no=np.repeat(m.face_normals,3,axis=0);f=np.arange(len(v)).reshape(-1,3)
        if uv is not None:uv=np.asarray(uv)[np.asarray(m.faces).ravel()]
    if uv is None:
        # world-triplanar UVs, vertical Y texcoord to preserve wood grain on facades
        axis=np.argmax(np.abs(no),axis=1);uv=np.zeros((len(v),2))
        for a,xy in enumerate(([1,2],[0,2],[0,1])):
            mask=axis==a;uv[mask]=v[mask][:,xy]
        uv[:,1]=1-uv[:,1]
    attr={'POSITION':g.addacc(v,'VEC3'),'NORMAL':g.addacc(no,'VEC3'),'TEXCOORD_0':g.addacc(uv,'VEC2')}
    mm={'name':name,'primitives':[{'attributes':attr,'indices':g.addacc(f.ravel()[:,None],'SCALAR',5125,34963),'material':mat,'mode':4}]}
    if name in g.ids:
        ni=g.ids[name];node=g.j['nodes'][ni];mi=node.get('mesh')
        if mi is None:mi=len(g.j['meshes']);g.j['meshes'].append(mm)
        else:g.j['meshes'][mi]=mm
        for k in ('matrix','translation','rotation','scale'):node.pop(k,None)
        # Parents used for new geometry are identity in source coordinates.
        oldp=g.parent[ni]
        if oldp!=parent:
            g.j['nodes'][oldp]['children'].remove(ni);g.j['nodes'][parent].setdefault('children',[]).append(ni);g.parent[ni]=parent
        changes.append(name)
    else:
        mi=len(g.j['meshes']);g.j['meshes'].append(mm);ni=len(g.j['nodes']);node={'name':name};g.j['nodes'].append(node);g.ids[name]=ni;g.parent[ni]=parent;g.j['nodes'][parent].setdefault('children',[]).append(ni)
    node['mesh']=mi;node.setdefault('extras',{}).update(revision='v13',dimension_status='PHOTO_ESTIMATE',part='V13_AUTHORED')
    return ni

def roundedrect(x0,y0,x1,y1,r=.006,n=8):
    r=min(r,(x1-x0)/2-.00001,(y1-y0)/2-.00001)
    pts=[]
    for cx,cy,start in [(x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180),(x1-r,y0+r,270)]:
        for a in np.linspace(start,start+90,n+1):
            ar=np.deg2rad(a);pts.append([cx+r*math.cos(ar),cy+r*math.sin(ar)])
    return Polygon(pts)

def solid_box(name,lo,hi,mat,parent,bevel=.0015):
    lo=np.array(lo,float);hi=np.array(hi,float);b=min(bevel,float((hi-lo).min())*.22)
    # chamfered convex solid; modest round corners for clean close-up silhouettes
    p=roundedrect(lo[0],lo[1],hi[0],hi[1],max(b,.0001),3)
    v,f=beveled_prism(p,lo[2],hi[2],bevel=b*.5) if b else prism(sbox(*lo[:2],*hi[:2]),lo[2],hi[2])
    return mesh(name,trimesh.Trimesh(v,f,process=False),mat,parent)

def transformed_box(name,center,dims,mat,parent,R=None,bevel=.0015):
    d=np.array(dims);p=roundedrect(-d[0]/2,-d[1]/2,d[0]/2,d[1]/2,min(bevel,d.min()*.2),3)
    v,f=beveled_prism(p,-d[2]/2,d[2]/2,min(bevel,d.min()*.19)*.5)
    if R is not None:v=v@R.T
    v+=np.array(center);return mesh(name,trimesh.Trimesh(v,f,process=False),mat,parent)

def tube_mesh(points,r=.008,n=16):
    p=np.asarray(points,float);rings=[];prev=None
    for i,c in enumerate(p):
        t=(p[min(i+1,len(p)-1)]-p[max(0,i-1)]);t/=np.linalg.norm(t)
        ref=np.array([0.,0.,1.]) if abs(t[2])<.92 else np.array([1.,0.,0.])
        a=np.cross(t,ref);a/=np.linalg.norm(a)
        if prev is not None and a@prev<0:a=-a
        prev=a;b=np.cross(t,a)
        rings.append(c+r*(np.cos(np.arange(n)*2*np.pi/n)[:,None]*a+np.sin(np.arange(n)*2*np.pi/n)[:,None]*b))
    vv=np.concatenate(rings);ff=[]
    for i in range(len(p)-1):
        for k in range(n):h=(k+1)%n;a=i*n+k;b=i*n+h;c=(i+1)*n+h;d=(i+1)*n+k;ff.extend([(a,b,c),(a,c,d)])
    vv=np.r_[vv,p[:1],p[-1:]];a=len(vv)-2;b=a+1
    for k in range(n):ff.extend([(a,(k+1)%n,k),(b,(len(p)-1)*n+k,(len(p)-1)*n+(k+1)%n)])
    m=trimesh.Trimesh(vv,ff,process=False);m.fix_normals();return m

def pipe(name,points,r,mat,parent,n=18):return mesh(name,tube_mesh(points,r,n),mat,parent,smooth=True)
def cyl(name,a,b,r,mat,parent,n=32):return pipe(name,[a,b],r,mat,parent,n)
def ball(name,center,scale,mat,parent):
    m=trimesh.creation.uv_sphere(count=[16,24]);m.vertices*=np.array(scale);m.vertices+=np.array(center);return mesh(name,m,mat,parent,smooth=True)
def ring(name,center,major,minor,mat,parent,axis='z',segments=48):
    theta=np.linspace(0,2*np.pi,segments+1)
    v=np.array([major*np.cos(theta),major*np.sin(theta),np.zeros(len(theta))]).T
    if axis=='x':v=v[:,[2,0,1]]
    if axis=='y':v=v[:,[0,2,1]]
    return pipe(name,v+center,minor,mat,parent,n=12)

def font(size,bold=False):
    from pathlib import Path
    candidates=['/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',
                'C:/Windows/Fonts/'+('arialbd.ttf' if bold else 'arial.ttf'),
                '/System/Library/Fonts/Supplemental/Arial'+(' Bold' if bold else '')+'.ttf']
    for path in candidates:
        if Path(path).exists():
            try:return ImageFont.truetype(path,size)
            except OSError:pass
    return ImageFont.load_default(size=size)

