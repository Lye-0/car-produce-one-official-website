"""Binary GLB editing and closed-solid construction utilities for CPO v06.
No Blender required. Original embedded textures and unaffected meshes are retained.
Imported by revise_v05_to_v06.py; do not execute as a standalone generator.
Dependencies: numpy, shapely. All dimensions are metres, reconstruction estimates.
"""
from __future__ import annotations
import sys,json,struct,copy,math,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,LineString,box
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
def triangulate(poly):
    return list(constrained_delaunay_triangles(poly).geoms)
from shapely.geometry.polygon import orient

class GLB:
    def __init__(self,path):
        b=Path(path).read_bytes();self.sha=hashlib.sha256(b).hexdigest()
        magic,ver,size=struct.unpack_from('<III',b)
        assert magic==0x46546c67 and ver==2 and size==len(b)
        jl,jt=struct.unpack_from('<II',b,12);self.j=json.loads(b[20:20+jl]);bl,bt=struct.unpack_from('<II',b,20+jl)
        self.data=bytearray(b[28+jl:28+jl+bl]);self.changes=[]
        self.parent={c:i for i,n in enumerate(self.j['nodes']) for c in n.get('children',[])}
        self.ids={n['name']:i for i,n in enumerate(self.j['nodes'])}
    def acc(self,i):
        a=self.j['accessors'][i];v=self.j['bufferViews'][a['bufferView']]
        dtype=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1',5122:'<i2'}[a['componentType']])
        sz={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        return np.ndarray((a['count'],sz),dtype=dtype,buffer=self.data,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',sz*dtype.itemsize),dtype.itemsize)).copy()
    def matrix(self,i):
        n=self.j['nodes'][i]
        if 'matrix' in n:return np.array(n['matrix']).reshape(4,4,order='F')
        t=np.eye(4);t[:3,3]=n.get('translation',[0,0,0]);t[:3,:3]=np.diag(n.get('scale',[1,1,1]));assert 'rotation' not in n
        return t
    def world(self,i):
        # Internal source frame: X right, Y towards back, Z up. Root converts to glTF.
        if i in (0,1):return np.eye(4)
        return self.world(self.parent[i])@self.matrix(i)
    def vertices(self,i):
        n=self.j['nodes'][i]
        if 'mesh' not in n:return np.zeros((0,3))
        vs=[];t=self.world(i)
        for p in self.j['meshes'][n['mesh']]['primitives']:
            v=self.acc(p['attributes']['POSITION']);vs.append(v@t[:3,:3].T+t[:3,3])
        return np.concatenate(vs)
    def descendants(self,i):
        for c in self.j['nodes'][i].get('children',[]):yield c;yield from self.descendants(c)
    def addacc(self,data,kind,component=5126,target=34962):
        dtype='<f4' if component==5126 else '<u4';ar=np.asarray(data,dtype=dtype)
        while len(self.data)%4:self.data+=b'\0'
        off=len(self.data);self.data+=ar.tobytes();vi=len(self.j['bufferViews'])
        self.j['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':ar.nbytes,'target':target})
        ai=len(self.j['accessors']);a={'bufferView':vi,'componentType':component,'count':len(ar),'type':kind}
        if kind in ('VEC3','SCALAR'):a.update(min=ar.reshape(len(ar),-1).min(0).tolist(),max=ar.reshape(len(ar),-1).max(0).tolist())
        self.j['accessors'].append(a);return ai
    def bake(self,i,t):
        n=self.j['nodes'][i];assert 'mesh' in n
        # Retain local UVs; bake the world affine transform into position + normals.
        m=copy.deepcopy(self.j['meshes'][n['mesh']]);W=t@self.world(i);P=np.linalg.inv(self.world(self.parent[i]));W=P@W
        for p in m['primitives']:
            at=p['attributes'];v=self.acc(at['POSITION']);v=v@W[:3,:3].T+W[:3,3]
            at['POSITION']=self.addacc(v,'VEC3')
            if 'NORMAL' in at:
                no=self.acc(at['NORMAL'])@np.linalg.inv(W[:3,:3]);no/=np.linalg.norm(no,axis=1)[:,None];at['NORMAL']=self.addacc(no,'VEC3')
            at.pop('TANGENT',None)
        self.j['meshes'][n['mesh']]=m
        for key in ['matrix','translation','rotation','scale']:n.pop(key,None)
        n.setdefault('extras',{})['v06']='PHOTO_CORRECTED_TRANSFORM'
        self.changes.append(n['name'])
    def replace(self,name,verts,faces,material,parent=None,uv_scale=1.0,uv_mode=None):
        # Face-separated vertices give dependable hard edges, flat normals and UV seams.
        v=np.asarray(verts,float);f=np.asarray(faces,int);v=v[f.reshape(-1)].reshape(-1,3,3)
        n=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);length=np.linalg.norm(n,axis=1)
        mask=length>1e-11;v=v[mask];n=n[mask]/length[mask,None];flat=v.reshape(-1,3)
        no=np.repeat(n,3,axis=0);uv=np.zeros((len(v),3,2));axes=np.argmax(np.abs(n),axis=1)
        for a in range(3):
            use=axes==a;xy=([1,2] if a==0 else [0,2] if a==1 else [0,1]);uv[use]=v[use][:,:,xy]/uv_scale
        uv[:,:,1]=1-uv[:,:,1]
        mi=None
        if name in self.ids:
            ni=self.ids[name];node=self.j['nodes'][ni];mi=node.get('mesh')
        else:
            ni=len(self.j['nodes']);node={'name':name};self.j['nodes'].append(node);self.ids[name]=ni
            assert parent is not None;self.j['nodes'][parent].setdefault('children',[]).append(ni);self.parent[ni]=parent
        # Generated coordinates are source-world; generated/replaced targets have identity parents.
        assert np.allclose(self.world(self.parent[ni]),np.eye(4))
        p={'attributes':{'POSITION':self.addacc(flat,'VEC3'),'NORMAL':self.addacc(no,'VEC3'),'TEXCOORD_0':self.addacc(uv.reshape(-1,2),'VEC2')},'indices':self.addacc(np.arange(len(flat)).reshape(-1,1),'SCALAR',5125,34963),'material':material,'mode':4}
        mesh={'name':name,'primitives':[p]}
        if mi is None:mi=len(self.j['meshes']);self.j['meshes'].append(mesh)
        else:self.j['meshes'][mi]=mesh
        node['mesh']=mi
        for key in ['matrix','translation','rotation','scale']:node.pop(key,None)
        node.setdefault('extras',{}).update(v06='REBUILT_PHOTO_CORRECTION',dimension_status='ESTIMATED_NOT_MEASURED')
        self.changes.append(name);return ni
    def remove(self,name):
        ni=self.ids.get(name)
        if ni is not None:self.j['nodes'][ni].pop('mesh',None);self.changes.append(name+' [removed]')
    def save(self,path):
        # v07.1 compatibility: never rely on an omitted texture sampler.
        from fix_texture_samplers import ensure_explicit_samplers
        ensure_explicit_samplers(self.j)
        while len(self.data)%4:self.data+=b'\0'
        self.j['buffers']=[{'byteLength':len(self.data)}]
        self.j['asset']['generator']='CAR PRODUCE ONE v12 / facade joinery, display proportion and workshop detail'
        jb=json.dumps(self.j,ensure_ascii=False,separators=(',',':')).encode();jb+=b' '*((-len(jb))%4)
        raw=struct.pack('<III',0x46546c67,2,12+8+len(jb)+8+len(self.data))+struct.pack('<II',len(jb),0x4e4f534a)+jb+struct.pack('<II',len(self.data),0x004e4942)+self.data
        Path(path).write_bytes(raw)

def prism(poly,z0,z1):
    vv=[];ff=[]
    def tri(a,b,c):
        k=len(vv);vv.extend([a,b,c]);ff.append([k,k+1,k+2])
    polys=list(poly.geoms) if hasattr(poly,'geoms') else [poly]
    for pol in polys:
        if pol.area<1e-10:continue
        pol=orient(pol.simplify(1e-9, preserve_topology=True),sign=1)
        for t in triangulate(pol):
            if t.difference(pol).area>1e-10:continue
            a,b,c=list(orient(t,1).exterior.coords)[:3]
            tri((*a,z1),(*b,z1),(*c,z1));tri((*c,z0),(*b,z0),(*a,z0))
        for ring in [pol.exterior,*pol.interiors]:
            coords=list(ring.coords)
            for a,b in zip(coords[:-1],coords[1:]):
                tri((*a,z0),(*b,z0),(*b,z1));tri((*a,z0),(*b,z1),(*a,z1))
    return np.array(vv),np.array(ff)

def beveled_prism(poly,z0,z1,bevel=.003):
    # Convex polygon with edge chamfers; bevelled cap reduces knife-like close-up edges.
    out=orient(poly,1);inside=out.buffer(-bevel,join_style=2)
    if not isinstance(inside,Polygon):return prism(poly,z0,z1)
    p=np.array(out.exterior.coords[:-1]);q=np.array(orient(inside,1).exterior.coords[:-1])
    if len(p)!=len(q):return prism(poly,z0,z1)
    # Align starting vertices after offset.
    q=np.roll(q,-np.argmin(np.linalg.norm(q-p[0],axis=1)),axis=0)
    vv=[];ff=[]
    def tri(a,b,c):k=len(vv);vv.extend([a,b,c]);ff.append([k,k+1,k+2])
    for t in triangulate(inside):
        if t.difference(inside).area<1e-10:
            a,b,c=list(orient(t,1).exterior.coords)[:3];tri((*a,z1),(*b,z1),(*c,z1));tri((*c,z0),(*b,z0),(*a,z0))
    rings=[(q,z0),(p,z0+bevel),(p,z1-bevel),(q,z1)]
    for (a,za),(b,zb) in zip(rings[:-1],rings[1:]):
        for k in range(len(p)):
            h=(k+1)%len(p);tri((*a[k],za),(*a[h],za),(*b[h],zb));tri((*a[k],za),(*b[h],zb),(*b[k],zb))
    return np.array(vv),np.array(ff)

def T(offset=(0,0,0)):
    m=np.eye(4);m[:3,3]=offset;return m
