"""CPO v15. Reference-specific automotive surfaces and cinematic urban scene.

Coordinates: metres, X across car, -Y front, Z up. Retains v14 and all
animated parent objects. Each stage owns a named collection/root.
"""
import bpy, bmesh, math, random, json, importlib.util
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from math import sin, cos, pi, sqrt, exp

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cpo_v14_helpers',ROOT/'tools/refine_v14.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

def set_collection(name):
    h.COL=h.collection(name)
    return h.COL

def remove_root(name):
    o=bpy.data.objects.get(name)
    if o:
        for child in list(o.children_recursive)[::-1]:bpy.data.objects.remove(child,do_unlink=True)
        bpy.data.objects.remove(o,do_unlink=True)

def normalise_mesh(o):
    if o.type!='MESH':return
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()

def smooth_value(points,x):
    """Shape-preserving cubic with continuous tangent at the stations."""
    n=len(points)
    if x<=points[0][0]:return points[0][1]
    if x>=points[-1][0]:return points[-1][1]
    ds=[(points[i+1][1]-points[i][1])/(points[i+1][0]-points[i][0]) for i in range(n-1)]
    slopes=[ds[0]]
    for i in range(1,n-1):
        a,b=ds[i-1],ds[i]
        if a*b<=0:slopes.append(0)
        else:
            ha=points[i][0]-points[i-1][0];hb=points[i+1][0]-points[i][0]
            w1=2*hb+ha;w2=hb+2*ha;slopes.append((w1+w2)/(w1/a+w2/b))
    slopes.append(ds[-1])
    for i in range(n-1):
        a,v=points[i];b,w=points[i+1]
        if x<=b:
            t=(x-a)/(b-a)
            return (2*t**3-3*t*t+1)*v+(t**3-2*t*t+t)*(b-a)*slopes[i]+(-2*t**3+3*t*t)*w+(t**3-t*t)*(b-a)*slopes[i+1]

def catmull(points,count=8,closed=False):
    p=[Vector(x) for x in points];result=[];n=len(p)
    for i in range(n if closed else n-1):
        a=p[(i-1)%n] if closed or i else p[0]
        b=p[i];c=p[(i+1)%n];d=p[(i+2)%n] if closed or i+2<n else p[-1]
        for j in range(count):
            t=j/count
            result.append(tuple(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t**3)))
    if not closed:result.append(tuple(p[-1]))
    return result

def path(name,points,r,mat,parent=None,closed=False):
    return h.curve(name,catmull(points,8,closed),r,mat,parent,closed)

def cut_polygon(name,points,front,back,parent,body):
    # XZ contour, extruded along Y; rounded contours can be pre-sampled.
    n=len(points);verts=[(x,y,z) for y in [front,back] for x,z in points]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    cutter=h.mesh(name,verts,faces,None,parent,False);normalise_mesh(cutter)
    boolean=body.modifiers.new(name,'BOOLEAN');boolean.operation='DIFFERENCE';boolean.solver='EXACT';boolean.object=cutter
    bpy.context.view_layer.objects.active=body
    bpy.ops.object.modifier_apply(modifier=boolean.name)
    bpy.data.objects.remove(cutter,do_unlink=True)

def surface_polygon(name,points,mat,parent=None,thickness=0):
    o=h.mesh(name,points,[tuple(range(len(points)))],mat,parent,False)
    if thickness:
        m=o.modifiers.new('Physical thickness','SOLIDIFY');m.thickness=thickness
        b=o.modifiers.new('Soft manufactured edges','BEVEL');b.width=min(.002,thickness*.25);b.segments=3
    return o

def material_set():
    m={}
    m['paint_blue']=h.material('V15 Prelude sapphire blue',(.012,.065,.19),.215,.50,1)
    m['paint_black']=h.material('V15 Vezel crystal black pearl',(.007,.008,.010),.22,.35,1)
    for key,color in [('paint_blue',(.004,.014,.043)),('paint_black',(.004,.005,.006))]:
        shader=m[key].node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(*color,1)
        shader.inputs['Metallic'].default_value=.23 if key=='paint_blue' else .10
        shader.inputs['Roughness'].default_value=.29;shader.inputs['Coat Roughness'].default_value=.17
    for key in ['paint_blue','paint_black']:
        nt=m[key].node_tree
        if not nt.nodes.get('V15 fine metallic flake'):
            n=nt.nodes.new('ShaderNodeTexNoise');n.name='V15 fine metallic flake';n.inputs['Scale'].default_value=2300;n.inputs['Detail'].default_value=2
            bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.055;bump.inputs['Distance'].default_value=.000025
            nt.links.new(n.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],nt.nodes.get('Principled BSDF').inputs['Normal'])
    m['rubber']=h.material('V15 tyre charcoal',(.008,.009,.010),.68)
    m['black']=h.material('V15 injection moulded satin',(.008,.009,.011),.36)
    m['piano']=h.material('V15 gloss black trim',(.004,.005,.006),.18,.08,.6)
    m['gun']=h.material('V15 forged wheel graphite',(.033,.039,.047),.30,.80,.25)
    m['machined']=h.material('V15 diamond cut aluminium',(.19,.22,.25),.27,.92)
    m['chrome']=h.material('V15 satin chrome accents',(.40,.43,.47),.20,.94)
    m['glass']=h.material('V15 laminated clear glass',(.94,.97,.97),.035,0,0,0,1)
    m['privacy']=h.material('V15 privacy glass',(.34,.42,.42),.045,0,0,0,1)
    m['lens']=h.material('V15 lamp clear cover',(.985,.99,1),.035,0,0,0,1)
    m['light']=h.material('V15 LED white diffuser',(.70,.79,.91),.27,0,0,.6)
    m['red']=h.material('V15 red light guide',(.38,.003,.008),.20,.05,.7,.35)
    m['red_dark']=h.material('V15 red smoked housing',(.045,.001,.002),.22,.12,.5)
    m['brake']=h.material('V15 brake disc brushed iron',(.14,.16,.18),.43,.87)
    m['caliper']=h.material('V15 Prelude blue calipers',(.008,.055,.30),.30,.30,.5)
    m['leather']=h.material('V15 graphite upholstery',(.025,.028,.031),.57)
    m['ivory']=h.material('V15 Prelude ivory upholstery',(.40,.42,.41),.62)
    m['stitch']=h.material('V15 upholstery stitching',(.23,.25,.27),.76)
    return m

def h_emblem(name,position,size,mat,parent,back=False,hood=False):
    # Raised contour built as geometry, used on the vehicle and wheel centres.
    sx=size;sz=size*.80;x0,y0,z0=position
    def co(p):
        x,z=p
        return (x0+x*sx,y0+(-z*sz*.35 if hood else 0),z0+z*sz)
    outer=[(-.48,-.42),(-.54,.35),(-.37,.5),(.37,.5),(.54,.35),(.48,-.42),(.30,-.48),(-.30,-.48)]
    path(name+' surround',[co(p) for p in outer],size*.035,mat,parent,True)
    for side in [-1,1]:path(name+' upright'+str(side),[co((side*.34,.36)),co((side*.20,-.35))],size*.055,mat,parent)
    path(name+' crossbar',[co((-.25,-.02)),co((0,-.05)),co((.25,-.02))],size*.04,mat,parent)

class CarSurface:
    def __init__(self,suv):
        self.suv=suv
        self.L=4.385 if suv else 4.520;self.W=1.790 if suv else 1.880;self.H=1.545 if suv else 1.355
        self.half=self.L/2;self.r=.3411 if suv else .3353;self.wheels=[-1.305,1.305] if suv else [-1.3025,1.3025]
        self.front=-.90 if suv else -.80;self.rear=2.015 if suv else 1.86
        if suv:
            self.width_keys=[(-self.half,.805),(-1.98,.865),(-1.55,.890),(-1.05,.889),(-.2,.872),(.6,.875),(1.30,.890),(1.80,.873),(self.half,.798)]
            self.belt_keys=[(-self.half,.930),(-1.96,1.035),(-1.30,1.074),(-.70,1.065),(.25,1.059),(1.2,1.068),(1.8,1.056),(self.half,1.010)]
            self.top_keys=[(-self.half,.942),(-1.92,1.057),(-1.30,1.09),(-.90,1.077),(-.40,1.046),(1.5,1.05),(self.half,1.030)]
            self.roof_keys=[(-.90,1.073),(-.65,1.228),(-.39,1.420),(-.15,1.518),(.10,1.543),(.65,1.540),(1.1,1.520),(1.32,1.462),(1.60,1.290),(1.86,1.124),(2.015,1.052)]
            self.cw_keys=[(-.90,.775),(-.40,.716),(-.10,.674),(.65,.669),(1.18,.665),(1.60,.705),(2.015,.750)]
            self.window_keys=[(-.81,1.090),(-.57,1.266),(-.34,1.420),(-.06,1.466),(.64,1.464),(1.03,1.425),(1.30,1.315),(1.52,1.128)]
            self.win_start=-.81;self.win_end=1.52;self.window_pillars=[(.17,.235),(1.305,1.35)]
        else:
            self.width_keys=[(-self.half,.813),(-2.04,.88),(-1.58,.933),(-1.25,.936),(-.64,.906),(.0,.893),(.60,.916),(1.23,.936),(1.70,.919),(self.half,.81)]
            self.belt_keys=[(-self.half,.737),(-2.06,.798),(-1.63,.863),(-1.29,.888),(-.65,.925),(.15,.939),(.75,.965),(1.34,.969),(1.82,.942),(self.half,.869)]
            self.top_keys=[(-self.half,.735),(-2.08,.792),(-1.55,.855),(-.80,.958),(-.4,.925),(1.5,.954),(1.87,.960),(self.half,.903)]
            self.roof_keys=[(-.80,.958),(-.59,1.087),(-.32,1.229),(-.08,1.320),(.13,1.354),(.49,1.345),(.72,1.315),(1.05,1.220),(1.45,1.085),(1.86,.967)]
            self.cw_keys=[(-.80,.783),(-.30,.727),(-.05,.705),(.50,.688),(.82,.687),(1.35,.715),(1.86,.767)]
            self.window_keys=[(-.705,.966),(-.48,1.123),(-.21,1.250),(.08,1.284),(.45,1.272),(.80,1.194),(1.12,1.085),(1.48,.986)]
            self.win_start=-.705;self.win_end=1.48;self.window_pillars=[(.555,.612)]
    def width(self,y):return smooth_value(self.width_keys,y)
    def belt(self,y):return smooth_value(self.belt_keys,y)
    def top(self,y):return smooth_value(self.top_keys,y)
    def roof(self,y):return smooth_value(self.roof_keys,y)
    def cw(self,y):return smooth_value(self.cw_keys,y)
    def front_y(self,x):return -self.half+.19*(abs(x)/self.width(-self.half))**3
    def rear_y(self,x):return self.half-.10*(abs(x)/self.width(self.half))**3
    def upper_point(self,y,u):return (u*self.cw(y),y,self.roof(y)-.037*u*u)
    def side_point(self,y,z,side,out=0):
        low=self.belt(y);high=self.roof(y)-.037
        t=max(0,min(1,(z-low)/max(.01,high-low)))
        x=self.width(y)*.956*(1-t)+self.cw(y)*t+.006*sin(pi*t)
        return (side*(x+out),y,z)
    def flank_x(self,y,z):
        if hasattr(self,'bvh'):
            hit=self.bvh.ray_cast(Vector((1.4,y,z)),Vector((-1,0,0)))
            if hit[0] is not None:return hit[0].x
        low=.205 if self.suv else .160;edge=self.belt(y)
        t=max(0,min(1,(edge-z)/max(.01,edge-low)))
        # Shoulder is full, the lower door pulls in, and the sill returns outward.
        scale=smooth_value([(0,.945),(.10,.982),(.23,1),(.39,.994),(.67,.943),(.82,.949),(1,.962)],t)
        return self.width(y)*scale

def build_body(tag,p,s,m):
    paint=m['paint_black' if s.suv else 'paint_blue'];low=.205 if s.suv else .160
    rows=[]
    for j in range(181):
        y=-s.half+s.L*j/180;w=s.width(y);b=s.belt(y);t=s.top(y)
        # Half cross-section with an explicit shoulder and concave lower door.
        profile=[(0,t),(.30*w,t+.004),(.62*w,t+.010),(.81*w,b+.018),(.945*w,b),(.982*w,b-(b-low)*.10),(w,b-(b-low)*.23),(.994*w,b-(b-low)*.39),(.943*w,b-(b-low)*.67),(.949*w,b-(b-low)*.82),(.962*w,low),(.82*w,low-.018),(0,low-.020)]
        full=profile+[(-x,z) for x,z in profile[-2:0:-1]]
        profile3=catmull([(x,0,z) for x,z in full],4,True)
        row=[]
        for x,_,z in profile3:
            front_weight=max(0,1-(y+s.half)/.38)**2;rear_weight=max(0,1-(s.half-y)/.32)**2
            yy=y+front_weight*.19*(abs(x)/w)**3-rear_weight*.10*(abs(x)/w)**3
            yy+=front_weight*.065*((z-.56)/.45)**2-rear_weight*.065*((z-.61)/.47)**2
            row.append((x,yy,z))
        row.append(row[0]);rows.append(row)
    body=h.patch(tag+' body pressed panels',rows,paint,p,False)
    # Radial quad caps follow the curved nose/tail. Large non-planar n-gons
    # would create false reflections and unstable Boolean triangulation.
    verts=[tuple(v.co) for v in body.data.vertices];faces=[tuple(f.vertices) for f in body.data.polygons]
    nx=len(rows[0]);count=nx-1
    for end,row,indices in [(-1,rows[0],list(range(count))),(1,rows[-1],list(range((len(rows)-1)*nx,(len(rows)-1)*nx+count)))]:
        centre_z=(s.top(end*s.half)+low)/2;prev=indices
        for layer in range(1,11):
            t=1-layer/11;current=[]
            for i in range(count):
                x=row[i][0]*t;z=centre_z+(row[i][2]-centre_z)*t
                yy=(s.front_y(x)+.065*((z-.56)/.45)**2) if end<0 else (s.rear_y(x)-.065*((z-.61)/.47)**2)
                current.append(len(verts));verts.append((x,yy,z))
            for i in range(count):faces.append((prev[i],prev[(i+1)%count],current[(i+1)%count],current[i]))
            prev=current
        centre=len(verts);verts.append((0,(s.front_y(0)+.065*((centre_z-.56)/.45)**2) if end<0 else (s.rear_y(0)-.065*((centre_z-.61)/.47)**2),centre_z))
        for i in range(count):faces.append((prev[i],prev[(i+1)%count],centre))
    body.data.clear_geometry();body.data.from_pydata(verts,[],faces);body.data.update()
    for face in body.data.polygons:face.use_smooth=True
    # Merge shared seams to get a watertight shell before cutting apertures.
    bm=bmesh.new();bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
    for wy in s.wheels:
        cutter=h.cylinder(tag+' temporary wheel opening',(-1.6,wy,s.r),(1.6,wy,s.r),s.r+(.033 if s.suv else .030),None,p,128)
        normalise_mesh(cutter)
        mod=body.modifiers.new('Stamped wheel opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
        bpy.context.view_layer.objects.active=body;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    # Open the passenger compartment. A full-width body loft otherwise leaves
    # a painted deck through the seats, visible as a false white reflection.
    outline=[(-.69,s.front+.035),(.69,s.front+.035),(.81,-.50),(.82,.70),(.76,s.rear-.12),(-.76,s.rear-.12),(-.82,.70),(-.81,-.50)]
    n=len(outline);verts=[(x,y,z) for z in [.315,2.2] for x,y in outline]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    cutter=h.mesh(tag+' cabin cavity cutter',verts,faces,None,p,False);normalise_mesh(cutter)
    mod=body.modifiers.new('Actual passenger compartment','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.context.view_layer.objects.active=body;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    # Genuine lower grille recess, plus the Vezel RS upper grille recess.
    intake=[(-.63,.255),(-.73,.420),(-.65,.500),(.65,.500),(.73,.420),(.63,.255)] if not s.suv else [(-.68,.260),(-.77,.380),(-.71,.495),(.71,.495),(.77,.380),(.68,.260)]
    cut_polygon(tag+' lower grille opening',intake,-s.half-.2,-s.half+.29,p,body)
    if s.suv:
        upper=[(-.61,.636),(-.66,.70),(-.64,.900),(-.55,.963),(.55,.963),(.64,.900),(.66,.70),(.61,.636)]
        cut_polygon(tag+' RS upper grille opening',upper,-s.half-.2,-s.half+.28,p,body)
    s.bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons],all_triangles=False)
    bevel=body.modifiers.new('Fine panel edge radii','BEVEL');bevel.width=.0022;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=.60
    # Bonnet is a separate panel with a fine closed edge. Its station curves are
    # aligned with the underlying body, without independent flat spots.
    a=-s.half+.055;b=s.front-.012;rows=[]
    for j in range(81):
        y=a+(b-a)*j/80
        row=[]
        for i in range(49):
            u=-1+2*i/48;x=u*s.width(y)*.795
            yy=y+max(0,1-(y+s.half)/.38)**2*.19*(abs(x)/s.width(y))**3
            hit=s.bvh.ray_cast(Vector((x,yy,2.5)),Vector((0,0,-1)))
            z=(hit[0].z if hit[0] is not None else s.top(y))+.0018
            row.append((x,yy,z))
        rows.append(row)
    hood=h.patch(tag+' bonnet',rows,paint,p,False,.0014)
    boundary=rows[0]+[r[-1] for r in rows[1:]]+list(reversed(rows[-1][:-1]))+[r[0] for r in rows[-2:0:-1]]
    h.curve(tag+' bonnet perimeter gap',boundary,.00125,m['black'],p,True)
    for side in [-1,1]:
        # Door perimeter follows the body and has a rounded foot at the sill.
        outlines=([(-.81,1.06),(-.73,.49),(-.67,.26),(.16,.255),(.25,.34),(.26,1.059)],[(.265,1.059),(.265,.34),(.38,.27),(1.02,.30),(1.30,.55),(1.43,1.069)]) if s.suv else ([(-.73,.930),(-.67,.46),(-.54,.213),(.60,.202),(.72,.31),(.755,.965)],)
        for k,outline in enumerate(outlines):
            pts=[]
            for y,z in catmull(outline,12):pts.append((side*(s.flank_x(y,z)+.001),y,z))
            h.curve(tag+f' door shutline {side}.{k}',pts,.0012,m['black'],p)
        for wy in s.wheels:
            radius=s.r+(.035 if s.suv else .032)
            rows=[]
            for j in range(81):
                a=-.22+(pi+.44)*j/80;y=wy+radius*cos(a);z=s.r+radius*sin(a)
                lip=.038 if s.suv else .011
                rows.append([(side*(s.flank_x(wy+(radius+v)*cos(a),s.r+(radius+v)*sin(a))+.002),wy+(radius+v)*cos(a),s.r+(radius+v)*sin(a)) for v in [0,lip*.2,lip*.7,lip]])
            h.patch(tag+f' formed wheelarch {side}.{wy}',rows,m['piano'] if s.suv else paint,p,side<0,.0015)
            # Inner wheelhouse gives tyre recesses a real dark depth.
            rows=[]
            for j in range(61):
                a=pi*j/60
                rows.append([(side*x,wy+(radius+.002)*cos(a),s.r+(radius+.002)*sin(a)) for x in [.64,.71,.79,.85]])
            h.patch(tag+' wheelhouse liner',rows,m['black'],p,side<0)
        sill=[(side*(s.width(y)*.96+.001),y,low+.015) for y in [-.94,-.65,0,.60,.95]]
        path(tag+' lower rocker edge'+str(side),sill,.014,m['piano'],p)
        if s.suv:path(tag+' RS sill garnish'+str(side),[(side*.845,y,.277) for y in [-.87,-.50,0,.50,.91]],.006,m['chrome'],p)
    return body

def build_greenhouse(tag,p,s,m):
    paint=m['paint_black' if s.suv else 'paint_blue']
    roof_front=-.17 if s.suv else -.075;roof_rear=1.15 if s.suv else .72
    # Separate centre glazing and painted outer rails. The glass really is open
    # to the cabin: there is no opaque shell behind it.
    for a,b,label,mat in [(s.front,roof_front,'windscreen',m['glass']),(roof_front,roof_rear,'roof',paint),(roof_rear,s.rear,'rear window',m['privacy'] if s.suv else m['glass'])]:
        for strip,ua,ub in [('left rail',-1,-.943),('centre',-.943,.943),('right rail',.943,1)]:
            material=mat if strip=='centre' else paint
            rows=[[s.upper_point(a+(b-a)*j/64,ua+(ub-ua)*i/48) for i in range(49)] for j in range(65)]
            h.patch(tag+' '+label+' '+strip,rows,material,p,False,.0038 if material in [m['glass'],m['privacy']] else .004)
            if strip=='centre' and mat!=paint:
                edge=rows[0]+[r[-1] for r in rows[1:]]+list(reversed(rows[-1][:-1]))+[r[0] for r in rows[-2:0:-1]]
                h.curve(tag+' '+label+' ceramic border',edge,.0038,m['black'],p,True)
    for side in [-1,1]:
        intervals=[s.front,s.win_start]+[v for pair in s.window_pillars for v in pair]+[s.win_end,s.rear]
        for a,b in zip(intervals,intervals[1:]):
            middle=(a+b)/2
            glass=s.win_start<middle<s.win_end and not any(c<middle<d for c,d in s.window_pillars)
            rows_low=[];rows_mid=[];rows_high=[]
            for j in range(41):
                y=a+(b-a)*j/40;low=s.belt(y);high=s.roof(y)-.037
                gl=low+.017;gh=min(high-.020,smooth_value(s.window_keys,y))
                gl=min(gl,high);gh=max(gl,gh)
                for arr,z0,z1 in [(rows_low,low,gl),(rows_mid,gl,gh),(rows_high,gh,high)]:arr.append([s.side_point(y,z0+(z1-z0)*i/12,side) for i in range(13)])
            h.patch(tag+' side lower rail'+str(side)+str(a),rows_low,paint,p,side>0,.002)
            h.patch(tag+' side upper rail'+str(side)+str(a),rows_high,paint,p,side>0,.003)
            pillar_mat=m['piano'] if any(c<middle<d for c,d in s.window_pillars) else paint
            h.patch(tag+(' door glass' if glass else ' pillar')+str(side)+str(a),rows_mid,(m['privacy'] if s.suv and a>.20 else m['glass']) if glass else pillar_mat,p,side>0,.0038)
            if glass:
                edge=rows_mid[0]+[r[-1] for r in rows_mid[1:]]+list(reversed(rows_mid[-1][:-1]))+[r[0] for r in rows_mid[-2:0:-1]]
                h.curve(tag+' window gasket'+str(side)+str(a),edge,.003,m['black'],p,True)
        # Frit/bright lower strip is thin, instead of tubular chrome framing.
        pts=[s.side_point(y,s.belt(y)+.014,side,.0015) for y in [s.win_start+(s.win_end-s.win_start)*i/100 for i in range(101)]]
        h.curve(tag+' lower glass trim'+str(side),pts,.0035,m['chrome'] if s.suv else m['piano'],p)
        # Mirrors have a real blade mount, smooth shell and recessed rear mirror.
        my=-.69 if s.suv else -.56;mz=1.11 if s.suv else 1.025;mx=.95 if s.suv else 1.00
        path(tag+' mirror pedestal'+str(side),[(side*(s.W*.46),my,mz-.07),(side*(mx-.045),my+.018,mz-.01)],.024,m['piano'],p)
        h.ellipsoid(tag+' mirror sculpted shell'+str(side),(side*mx,my,mz),(.105,.143,.070),paint,p)
        h.ellipsoid(tag+' mirror reflective insert'+str(side),(side*mx,my+.12,mz),(.087,.012,.049),m['chrome'],p)
        path(tag+' mirror separation'+str(side),[(side*(mx-.08),my-.06,mz-.015),(side*mx,my-.143,mz-.015),(side*(mx+.092),my-.045,mz-.018)],.002,m['black'],p)
        # The Vezel rear handle is integrated into the rear window corner.
        handles=[(.025,s.belt(.025)-.085)] if s.suv else [(.57,s.belt(.57)-.12)]
        for y,z in handles:
            x=side*(s.flank_x(y,z)+.004)
            h.ellipsoid(tag+' door handle pocket'+str(side),(x,y,z),(.006,.105,.025),m['black'],p)
            h.box(tag+' door handle'+str(side),(x+side*.008,y,z),(.016,.185,.025),paint,p,.010)
        if s.suv:
            y=1.325;z=1.21
            h.box(tag+' concealed rear door handle'+str(side),s.side_point(y,z,side,.007),(.014,.033,.098),m['piano'],p,.009)
    # Rear demister filaments, and discrete wipers at the base of the glass.
    for j in range(12):
        y=roof_rear+.12+(s.rear-roof_rear-.22)*j/11
        pts=[s.upper_point(y,u) for u in [-.86+1.72*i/48 for i in range(49)]]
        h.curve(tag+' demister '+str(j),[(x,y,z+.0005) for x,y,z in pts],.00035,m['black'],p)
    for side in [-1,1]:
        pts=[s.upper_point(s.front+.035,u) for u in [side*.10,side*.38,side*.75]]
        path(tag+' front wiper'+str(side),[(x,y,z+.006) for x,y,z in pts],.007,m['black'],p)
    if s.suv:
        y=s.rear-.16;pts=[s.upper_point(y,u) for u in [-.33,0,.38]]
        path(tag+' rear wiper',[(x,y,z+.015) for x,y,z in pts],.006,m['black'],p)
        rows=[[s.upper_point(y,u) for u in [-1+2*i/48 for i in range(49)]] for y in [1.07,1.12,1.23,1.32]]
        rows=[[(x,y,z+.025) for x,y,z in row] for row in rows];h.patch(tag+' roof spoiler',rows,paint,p,False,.018)
    else:
        pts=[(u*.77,1.91-.025*u*u,.969-.022*u*u) for u in [-1+2*i/64 for i in range(65)]]
        h.curve(tag+' integrated tail lip',pts,.009,paint,p)

def build_wheels(tag,p,s,m):
    for side in [-1,1]:
        for wi,wy in enumerate(s.wheels):
            r=s.r;xc=side*((.7675 if wi==0 else .770) if s.suv else (.8125 if wi==0 else .8075));tw=.225 if s.suv else .235;outer=xc+side*(tw/2-.003)
            rim=.2286 if s.suv else .2413
            # Smooth revolved tyre profile, with a real shoulder and short sidewall.
            pr=[(-tw*.47,rim*.985),(-tw*.51,rim+.025),(-tw*.50,r-.020),(-tw*.42,r-.004),(-tw*.29,r),(.29*tw,r),(.42*tw,r-.004),(.50*tw,r-.020),(.51*tw,rim+.025),(.47*tw,rim*.985)]
            pr=catmull(pr,4)
            rows=[[(xc+dx,wy+rr*cos(2*pi*i/128),r+rr*sin(2*pi*i/128)) for i in range(129)] for dx,rr in pr]
            h.patch(tag+f' tyre {side}.{wi}',rows,m['rubber'],p,side<0)
            for off in [-.061,-.021,.021,.061]:h.ring(tag+' tread water channel',(xc+off,wy,r),r+.0003,.0014,m['black'],p)
            for k in range(80):
                a=k*2*pi/80
                for sign in [-1,1]:
                    pts=[(xc+sign*dx,wy+(r-.001)*cos(a+.09*(dx/.095)),r+(r-.001)*sin(a+.09*(dx/.095))) for dx in [.035,.065,.095]]
                    h.curve(tag+' tread shoulder siping',pts,.0008,m['black'],p)
            h.ring(tag+' sidewall rim protector',(outer+side*.005,wy,r),rim+.014,.002,m['rubber'],p)
            h.ring(tag+' wheel outer lip',(outer,wy,r),rim,.004,m['gun'],p)
            # Rim barrel is a surface rather than a fat torus.
            rows=[[(outer-side*d,wy+rim*.985*cos(2*pi*i/96),r+rim*.985*sin(2*pi*i/96)) for i in range(97)] for d in [0,.02,.08,.17]]
            h.patch(tag+' wheel inner barrel',rows,m['gun'],p,side<0)
            disc=(.150 if wi==0 else .140) if s.suv else (.175 if wi==0 else .155)
            h.cylinder(tag+' brake rotor',(outer-side*.066,wy,r),(outer-side*.055,wy,r),disc,m['brake'],p,96)
            h.cylinder(tag+' brake rotor hat',(outer-side*.053,wy,r),(outer-side*.041,wy,r),.082,m['gun'],p,64)
            for rr in [disc*.72,disc*.88]:
                for k in range(28):
                    a=2*pi*k/28+rr
                    h.cylinder(tag+' rotor perforation',(outer-side*.054,wy+rr*cos(a),r+rr*sin(a)),(outer-side*.053,wy+rr*cos(a),r+rr*sin(a)),.0023,m['black'],p,8)
            h.box(tag+' brake caliper',(outer-side*.052,wy+disc*.87,r+.015),(.050,.066,.125),m['gun'] if s.suv else m['caliper'],p,.017)
            # Vezel: broad split-spoke RS wheels. Prelude: narrow layered Y spokes.
            count=5
            for k in range(count):
                a=2*pi*k/count
                for branch in [-1,1]:
                    outline=[(.050,-.115),(.125,branch*.15-.05),(rim*.96,branch*.25-.035),(rim*.99,branch*.25+.027),(.133,branch*.15+.03),(.060,.12)] if not s.suv else [(.05,-.18),(.11,branch*.16-.09),(rim*.96,branch*.27-.075),(rim*.98,branch*.27+.075),(.108,branch*.16+.025),(.050,.16)]
                    pts=[]
                    for rr,aa in outline:
                        xx=outer-side*(.022*(1-rr/rim))
                        pts.append((xx,wy+rr*cos(a+aa),r+rr*sin(a+aa)))
                    o=surface_polygon(tag+' sculpted wheel spoke',pts,m['gun'],p,.012)
                    if s.suv:
                        pts2=[]
                        for rr,aa in [(rim*.30,branch*.17),(rim*.94,branch*.27-.046),(rim*.96,branch*.27+.025),(rim*.45,branch*.17+.015)]:pts2.append((outer+side*.002,wy+rr*cos(a+aa),r+rr*sin(a+aa)))
                        surface_polygon(tag+' RS diamond cut spoke face',pts2,m['machined'],p,.001)
                if not s.suv:
                    aa=a+pi/5
                    pts=[(outer-side*.018,wy+rr*cos(aa+offset),r+rr*sin(aa+offset)) for rr,offset in [(.065,-.06),(rim*.97,-.026),(rim*.97,.026),(.065,.06)]]
                    surface_polygon(tag+' recessed secondary spoke',pts,m['gun'],p,.009)
            h.cylinder(tag+' wheel centre cap',(outer-side*.009,wy,r),(outer+side*.007,wy,r),.042,m['piano'],p,64)
            for k in range(5):
                a=2*pi*k/5
                h.cylinder(tag+' wheel hex nut',(outer,wy+.052*cos(a),r+.052*sin(a)),(outer+side*.009,wy+.052*cos(a),r+.052*sin(a)),.006,m['chrome'],p,6)
            # Small H lettering, physically raised above the centre cap.
            text=h.text(tag+' wheel H','H',(outer+side*.009,wy,r-.010),.026,m['chrome'],p,rot=(pi/2,0,pi/2 if side>0 else -pi/2))
            # Tyre sizing, kept subtle so the tread carries the close-up.
            text=h.text(tag+' tyre size','225/50 R18' if s.suv else '235/40 R19',(outer+side*.008,wy,r+.282),.010,m['black'],p,rot=(pi/2,0,pi/2 if side>0 else -pi/2))

def build_faces(tag,p,s,m):
    paint=m['paint_black' if s.suv else 'paint_blue']
    def fy(x,z=.60):
        hit=s.bvh.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
        return hit[0].y if hit[0] is not None and hit[0].y<-s.half+.85 else s.front_y(x)
    def ry(x,z=.60):
        hit=s.bvh.ray_cast(Vector((x,3,z)),Vector((0,-1,0)))
        return hit[0].y if hit[0] is not None and hit[0].y>s.half-.85 else s.rear_y(x)
    def mapped_panel(name,outline,mat,offset,fn):
        centre=Vector((sum(x for x,z in outline)/len(outline),sum(z for x,z in outline)/len(outline)))
        edge=[]
        for i in range(len(outline)):
            a=Vector(outline[i]);b=Vector(outline[(i+1)%len(outline)])
            for j in range(6):edge.append(a.lerp(b,j/6))
        verts=[];faces=[];n=len(edge)
        for layer in range(1,9):
            for point in edge:
                x,z=centre.lerp(point,layer/8);verts.append((x,fn(x,z)+offset,z))
        for layer in range(7):
            for i in range(n):faces.append((layer*n+i,layer*n+(i+1)%n,(layer+1)*n+(i+1)%n,(layer+1)*n+i))
        centre_id=len(verts);x,z=centre;verts.append((x,fn(x,z)+offset,z))
        for i in range(n):faces.append((centre_id,i,(i+1)%n))
        o=h.mesh(tag+' '+name,verts,faces,mat,p,True)
        mod=o.modifiers.new('Actual lens or trim thickness','SOLIDIFY');mod.thickness=.0015
        return o
    def front_poly(name,outline,mat,offset=-.006):
        return mapped_panel(name,outline,mat,offset,fy)
    def rear_poly(name,outline,mat,offset=.005):
        return mapped_panel(name,outline,mat,offset,ry)
    # Lower grille back and deep hex cells.
    front_poly('lower grille dark cavity',[(-.69,.26),(-.73,.45),(-.62,.51),(.62,.51),(.73,.45),(.69,.26)],m['black'],.095)
    for row in range(5 if not s.suv else 4):
        z=.280+row*.045
        for col in range(24):
            x=-.615+col*.054+(row%2)*.027
            if abs(x)>.65-(.03 if row==0 else 0):continue
            pts=[(x+.030*cos(k*pi/3),fy(x)+.014,z+.021*sin(k*pi/3)) for k in range(6)]
            h.curve(tag+' lower grille honeycomb',pts,.0022,m['black'],p,True)
    if s.suv:
        front_poly('RS upper grille backing',[(-.61,.64),(-.66,.7),(-.64,.9),(-.54,.96),(.54,.96),(.64,.9),(.66,.7),(.61,.64)],m['black'],.13)
        outline=[(-.61,.638),(-.66,.705),(-.64,.900),(-.55,.960),(.55,.960),(.64,.900),(.66,.705),(.61,.638)]
        path(tag+' RS grille bright surround',[(x,fy(x)-.001,z) for x,z in outline],.005,m['gun'],p,True)
        for row in range(5):
            for col in range(12):
                x=-.565+col*.100+(row%2)*.05;z=.688+row*.052
                if abs(x)>.595:continue
                pts=[(x+.052*cos(k*pi/3),fy(x)+.009,z+.029*sin(k*pi/3)) for k in range(6)]
                h.curve(tag+' RS hexagonal grille',pts,.005,m['black'],p,True)
        h_emblem(tag+' front emblem',(0,fy(0)-.010,.839),.105,m['chrome'],p)
        h.text(tag+' RS front badge','RS',(.40,fy(.40)-.019,.770),.044,m['red'],p)
    else:
        pts=[(x,fy(x)-.008,.699+.027*(abs(x)/.72)**2) for x in [-.72+1.44*i/64 for i in range(65)]]
        h.curve(tag+' upper grille shadow',pts,.017,m['piano'],p)
        h.curve(tag+' nose bright blade',[(x,y-.003,z+.001) for x,y,z in pts],.0035,m['chrome'],p)
        h_emblem(tag+' bonnet emblem',(0,-s.half+.08,.764),.061,m['chrome'],p,hood=True)
    for side in [-1,1]:
        # Tapered headlamps wrap backwards into the front wings.
        if s.suv:outline=[(.31,.932),(.82,1.004),(.847,.970),(.803,.882),(.59,.868),(.37,.901)]
        else:outline=[(.38,.760),(.842,.850),(.866,.819),(.83,.716),(.56,.696),(.405,.716)]
        pts=[(side*x,z) for x,z in outline]
        front_poly('headlamp dark enclosure'+str(side),pts,m['piano'],-.009)
        # Lens is inset over a stepped reflector, leaving a visible black seal.
        cx=sum(x for x,z in pts)/len(pts);cz=sum(z for x,z in pts)/len(pts)
        inner=[(cx+(x-cx)*.956,cz+(z-cz)*.88) for x,z in pts]
        for k in range(4):
            x=side*(.465+.086*k);z=(.910 if s.suv else .748)+.060*k/3
            y=fy(x,z)-.012
            h.box(tag+' lamp reflector '+str(side)+str(k),(x,y,z),(.061,.016,.039),m['chrome'],p,.008)
            h.box(tag+' projector aperture '+str(side)+str(k),(x,y-.010,z),(.043,.008,.026),m['piano'],p,.006)
        front_poly('clear optical lens'+str(side),inner,m['lens'],-.034)
        drl=[(.33,.942),(.58,.976),(.80,1.003),(.835,1.020)] if s.suv else [(.385,.774),(.58,.810),(.785,.841),(.838,.861)]
        path(tag+' LED signature'+str(side),[(side*x,fy(side*x,z)-.040,z) for x,z in drl],.006,m['light'],p)
        # Sculpted lower corner fins and side reflectors.
        lower=[(.665,.250),(.835,.268),(.805,.405),(.742,.471),(.662,.375)] if not s.suv else [(.665,.270),(.814,.295),(.840,.397),(.727,.430),(.663,.380)]
        front_poly('lower corner aero blade'+str(side),[(side*x,z) for x,z in lower],paint,-.014)
        if s.suv:path(tag+' RS bumper silver wing'+str(side),[(side*.03,fy(.03)-.026,.264),(side*.55,fy(.55)-.028,.266),(side*.80,fy(.80)-.02,.302)],.010,m['chrome'],p)
        else:path(tag+' bumper lower lip'+str(side),[(side*.03,fy(.03)-.016,.193),(side*.59,fy(.59)-.023,.197),(side*.83,fy(.83)-.021,.221)],.006,m['piano'],p)
        # Tail lamp enclosures with two internal guides and clear lower segments.
        zbase=1.00 if s.suv else .865
        outline=[(.015,zbase+.04),(.73,zbase+.046),(.823,zbase+.075),(.837,zbase-.012),(.742,zbase-.064),(.57,zbase-.064),(.49,zbase-.02),(.015,zbase-.02)]
        rear_poly('tail lamp enclosure'+str(side),[(side*x,z) for x,z in outline],m['piano'],.013)
        for line in [0,1]:
            xs=[.025,.45,.70,.80];zs=[zbase+.027,zbase+.027,zbase+.032,zbase+.062]
            if line:xs=[.57,.70,.80];zs=[zbase-.030,zbase-.030,zbase-.002]
            path(tag+' tail light guide'+str(side)+str(line),[(side*x,ry(side*x,z)+.021,z) for x,z in zip(xs,zs)],.0055,m['red'],p)
        rear_poly('tail clear reversing lens'+str(side),[(side*.58,zbase-.043),(side*.73,zbase-.043),(side*.80,zbase-.016),(side*.78,zbase-.025),(side*.70,zbase-.058),(side*.59,zbase-.058)],m['chrome'],.025)
        path(tag+' rear bumper reflector'+str(side),[(side*.53,ry(.53)+.005,.322),(side*.73,ry(.73)+.004,.34)],.007,m['red'],p)
    # Number plates and a recessed rear diffuser.
    plate_z=.560 if s.suv else .570
    h.box(tag+' front number plate',(0,fy(0)-.036,plate_z),(.335,.012,.160),m['piano'],p,.006)
    h.text(tag+' front model lettering','VEZEL' if s.suv else 'Prelude',(0,fy(0)-.043,plate_z-.007),.049,m['chrome'],p)
    if s.suv:h.text(tag+' front grade lettering','e:HEV RS',(0,fy(0)-.044,plate_z-.044),.022,m['machined'],p)
    rear_poly('rear diffuser',[(-.70,.240),(-.59,.390),(-.26,.446),(.26,.446),(.59,.390),(.70,.240)],m['piano'],.015)
    h.box(tag+' rear number plate',(0,ry(0)+.039,.524 if s.suv else .371),(.335,.012,.160),m['piano'],p,.006)
    h.text(tag+' rear model lettering','VEZEL' if s.suv else 'Prelude',(0,ry(0)+.047,.51 if s.suv else .358),.047,m['chrome'],p,rot=(pi/2,0,pi))
    if s.suv:
        h_emblem(tag+' rear emblem',(0,ry(0)+.024,1.00),.080,m['chrome'],p,True)
        h.text(tag+' RS rear badge','RS',(-.60,ry(.6)+.011,.620),.033,m['red'],p,rot=(pi/2,0,pi))
    else:h.text(tag+' rear HONDA','H  O  N  D  A',(0,ry(0)+.026,.829),.028,m['chrome'],p,rot=(pi/2,0,pi))
    for side in [-1,1]:
        for x,z in [(.39,.55),(.77,.52)]:
            h.cylinder(tag+' parking sensor',(side*x,fy(x)-.003,z),(side*x,fy(x)-.006,z),.008,m['piano'],p,32)
    # Tailgate separation is a closed, curved cut line.
    rearline=[(-.60,.42),(-.74,.64),(-.73,1.02 if s.suv else .90),(.73,1.02 if s.suv else .90),(.74,.64),(.60,.42)]
    path(tag+' tailgate lower seam',[(x,ry(x)+.001,z) for x,z in rearline],.0015,m['black'],p)

def build_interior(tag,p,s,m):
    seat=m['leather'] if s.suv else m['ivory'];base=.60 if s.suv else .47
    h.box(tag+' enclosed cabin floor',(0,.2,.28),(1.51,2.32,.07),m['black'],p,.02)
    h.box(tag+' dashboard',(0,-.68,.98 if s.suv else .86),(1.43,.30,.145),m['leather'],p,.047)
    for side in [-1,1]:
        h.box(tag+' seat cushion',(side*.37,.14,base),(.44,.47,.13),seat,p,.059)
        back=h.box(tag+' seat back',(side*.37,.38,base+.27),(.42,.13,.47),seat,p,.050);back.rotation_euler[0]=-.12
        h.ellipsoid(tag+' headrest',(side*.37,.44,base+.55),(.13,.06,.098),seat,p)
        for off in [-.17,.17]:
            h.ellipsoid(tag+' seat bolster',(side*.37+off,.30,base+.22),(.053,.12,.21),seat,p)
        for off in [-.11,.11]:path(tag+' stitched seat panel',[(side*.37+off,.298,base+.11),(side*.37+off,.324,base+.34),(side*.37+off,.355,base+.44)],.001,m['stitch'],p)
        h.box(tag+' door inner trim',(side*.74,.08,.68 if s.suv else .60),(.045,1.0,.25),m['leather'],p,.029)
    h.box(tag+' rear seat cushion',(0,1.10,base-.015),(1.24,.40,.13),seat,p,.050)
    h.box(tag+' rear seat back',(0,1.36,base+.19),(1.22,.13,.42),seat,p,.044)
    # Right-hand-drive steering wheel and console, visible through actual glass.
    center=Vector((.38,-.56,.94 if s.suv else .84));q=Quaternion((1,0,0),math.radians(17))
    pts=[tuple(center+q@Vector((.17*cos(a),0,.17*sin(a)))) for a in [2*pi*i/64 for i in range(65)]]
    h.curve(tag+' steering rim',pts,.015,m['leather'],p,True)
    h.box(tag+' steering hub',center,(.16,.055,.09),m['black'],p,.028)
    for side in [-1,1]:path(tag+' steering spoke',[(center.x+side*.055,center.y,center.z),(center.x+side*.15,center.y,center.z+.015)],.013,m['black'],p)
    h.box(tag+' console',(0,.02,base-.025),(.22,.87,.18),m['leather'],p,.028)
    h.box(tag+' infotainment screen',(0,-.71,1.13 if s.suv else 1.00),(.25,.020,.12),m['piano'],p,.008)

def vehicle(tag,suv=False):
    set_collection('V15 / Vehicles');root_name=tag+'.V15_BODY';remove_root(root_name)
    old=bpy.data.objects[tag];h.hide_tree(old);p=h.new_source_root(root_name,old)
    s=CarSurface(suv);m=material_set()
    build_body(tag,p,s,m);build_greenhouse(tag,p,s,m);build_wheels(tag,p,s,m);build_faces(tag,p,s,m);build_interior(tag,p,s,m)
    for o in p.children_recursive:
        o['CPO_version']='15'
        if o.type=='MESH':
            if 'brake rotor' in o.name or 'rotor perforation' in o.name or 'brake caliper' in o.name:o.data['V15_brake_scaled']=True
            # Recalculate the closed glass volume, not an ambiguously oriented
            # open sheet. This preserves correct air/glass interfaces.
            for modifier in list(o.modifiers):
                if modifier.type=='SOLIDIFY' and any(mat and mat.use_nodes and mat.node_tree.nodes.get('Principled BSDF') and mat.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value>0 for mat in o.data.materials):
                    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=modifier.name)
            normalise_mesh(o)
    p['reference']='User video 5: Vezel e:HEV RS' if suv else 'User video 6: Prelude, custom sapphire blue'
    p['nominal_dimensions_m']=[s.L,s.W,s.H];p['wheelbase_m']=s.wheels[1]-s.wheels[0]
    print('V15_VEHICLE_READY',tag,len(p.children_recursive),flush=True)
    return p

def save():
    bpy.ops.file.pack_all();bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/blender/CPO_v15_refined.blend'),compress=True)
    print('V15_SAVED',flush=True)

def finish_grilles():
    set_collection('V15 / Vehicles')
    dark=h.material('V15 recessed radiator black',(.002,.003,.004),.88)
    dark.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.16
    rib=h.material('V15 grille moulded ribs',(.009,.011,.014),.49)
    rib.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.28
    for tag,suv in [('PRELUDE_SHOWROOM',False),('VEZEL_SHOWROOM',True)]:
        root=bpy.data.objects[tag+'.V15_BODY'];s=CarSurface(suv)
        for o in list(root.children_recursive):
            if any(term in o.name for term in ['lower grille dark cavity','RS upper grille backing']):o.hide_render=True;o.hide_set(True)
            if 'V15 radiator insert' in o.name or 'V15 deep cell grille' in o.name:bpy.data.objects.remove(o,do_unlink=True)
        h.box(tag+' V15 radiator insert lower',(0,-s.half+.165,.380),(1.45,.026,.28),dark,root,.009)
        if suv:h.box(tag+' V15 radiator insert upper',(0,-s.half+.165,.801),(1.35,.026,.36),dark,root,.010)
        for term in ['lower grille honeycomb','RS hexagonal grille']:
            cells=[o for o in root.children_recursive if term in o.name and o.type=='CURVE'];verts=[];faces=[]
            for o in cells:
                pts=[Vector(p.co[:3]) for p in o.data.splines[0].points];centre=sum(pts,Vector())/len(pts);n=len(pts);base=len(verts)
                for depth,scale in [(0,1),(0,.76),(.026,1),(.026,.76)]:
                    for pt in pts:
                        vtx=centre+(pt-centre)*scale;vtx.y+=depth;verts.append(tuple(vtx))
                for i in range(n):
                    j=(i+1)%n
                    faces.extend([(base+i,base+j,base+n+j,base+n+i),(base+i,base+2*n+i,base+2*n+j,base+j),(base+n+i,base+n+j,base+3*n+j,base+3*n+i),(base+2*n+i,base+3*n+i,base+3*n+j,base+2*n+j)])
                o.hide_render=True;o.hide_set(True)
            if verts:
                mesh=h.mesh(tag+' V15 deep cell grille '+term,verts,faces,rib,root,False);normalise_mesh(mesh)
    print('V15_DEEP_GRILLES_READY',flush=True)

def correct_brake_proportions():
    for tag,suv in [('PRELUDE_SHOWROOM',False),('VEZEL_SHOWROOM',True)]:
        s=CarSurface(suv);root=bpy.data.objects[tag+'.V15_BODY'];seen=set()
        for o in root.children_recursive:
            if o.type!='MESH' or o.data in seen or o.data.get('V15_brake_scaled'):continue
            if ('brake rotor' in o.name and 'hat' not in o.name) or 'rotor perforation' in o.name:
                centre_y=sum(v.co.y for v in o.data.vertices)/len(o.data.vertices);wi=0 if centre_y<0 else 1;wy=s.wheels[wi]
                desired=(.150 if wi==0 else .140) if suv else (.175 if wi==0 else .155);factor=desired/(s.r*(.61 if suv else .65))
                for vert in o.data.vertices:vert.co.y=wy+(vert.co.y-wy)*factor;vert.co.z=s.r+(vert.co.z-s.r)*factor
                o.data['V15_brake_scaled']=True;seen.add(o.data);o.data.update()
            elif 'brake caliper' in o.name:
                wi=0 if o.location.y<0 else 1;desired=(.150 if wi==0 else .140) if suv else (.175 if wi==0 else .155)
                for vert in o.data.vertices:vert.co.y=vert.co.y*.88+desired*.87-.166;vert.co.z*=.86
                o.data['V15_brake_scaled']=True;seen.add(o.data);o.data.update()
    print('V15_BRAKE_PROPORTIONS_CORRECTED',flush=True)
