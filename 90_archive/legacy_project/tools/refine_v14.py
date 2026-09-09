"""CPO v14: reversible scene refinement. Run stages in Blender via MCP.
All modelling coordinates below are metres, X width, -Y front, Z up.
Original meshes are retained hidden; animated roots and storefront stay intact.
"""
import bpy, math, random, json
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
from math import sin, cos, pi, sqrt, exp

ROOT=Path('C:/Users/kawau/dev/car-produce-one-official-website')
COL=None

def collection(name):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
    return c

def obj(name,data,parent=None):
    o=bpy.data.objects.new(name,data);COL.objects.link(o)
    if parent:o.parent=parent
    o['CPO_version']='14'
    return o

def mesh(name,verts,faces,mat,parent=None,smooth=True,uv=None):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update()
    o=obj(name,m,parent)
    if mat:m.materials.append(mat)
    for p in m.polygons:p.use_smooth=smooth
    if uv:
        layer=m.uv_layers.new(name='UVMap')
        for p in m.polygons:
            for li,vi in zip(p.loop_indices,p.vertices):layer.data[li].uv=uv[vi]
    return o

def box(name,loc,size,mat,parent=None,bevel=.008):
    x,y,z=[v/2 for v in size]
    vs=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
    faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    o=mesh(name,vs,faces,mat,parent,False);o.location=loc
    if bevel:
        mod=o.modifiers.new('Manufactured edge radius','BEVEL');mod.width=min(bevel,min(size)*.45);mod.segments=3
        mod=o.modifiers.new('Corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    return o

def patch(name,rows,mat,parent=None,reverse=False,solid=0,uvrect=None):
    ny=len(rows);nx=len(rows[0]);verts=[p for row in rows for p in row];faces=[]
    for j in range(ny-1):
        for i in range(nx-1):
            k=j*nx+i;f=(k,k+1,k+1+nx,k+nx);faces.append(f[::-1] if reverse else f)
    uv=[(i/(nx-1),j/(ny-1)) for j in range(ny) for i in range(nx)]
    if uvrect:
        x,y,w,h=uvrect;uv=[(x+u*w,y+v*h) for u,v in uv]
    o=mesh(name,verts,faces,mat,parent,True,uv)
    if solid:
        m=o.modifiers.new('Actual shell thickness','SOLIDIFY');m.thickness=solid
    return o

def curve(name,pts,r,mat,parent=None,closed=False):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=2;c.bevel_resolution=2;c.bevel_depth=r
    sp=c.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts):p.co=(*co,1)
    sp.use_cyclic_u=closed
    o=obj(name,c,parent);c.materials.append(mat)
    return o

def ring(name,center,r,thick,mat,parent=None,axis='X',n=64):
    pts=[]
    for i in range(n):
        a=2*pi*i/n;delta=(0,r*cos(a),r*sin(a)) if axis=='X' else ((r*cos(a),r*sin(a),0) if axis=='Z' else (r*cos(a),0,r*sin(a)))
        pts.append(tuple(center[k]+delta[k] for k in range(3)))
    return curve(name,pts,thick,mat,parent,True)

def cylinder(name,a,b,r,mat,parent=None,n=48):
    av=Vector(a);bv=Vector(b);direction=bv-av;q=direction.to_track_quat('Z','Y');vs=[]
    for z in [0,direction.length]:
        for i in range(n):vs.append(tuple(av+q@Vector((r*cos(2*pi*i/n),r*sin(2*pi*i/n),z))))
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,vs,fs,mat,parent)

def ellipsoid(name,loc,size,mat,parent=None):
    rows=[]
    for j in range(25):
        v=pi*j/24
        rows.append([(loc[0]+size[0]*sin(v)*cos(2*pi*i/48),loc[1]+size[1]*sin(v)*sin(2*pi*i/48),loc[2]+size[2]*cos(v)) for i in range(49)])
    return patch(name,rows,mat,parent)

def text(name,body,loc,size,mat,parent=None,rot=(pi/2,0,0),align='CENTER'):
    c=bpy.data.curves.new(name,'FONT');c.body=body;c.size=size;c.align_x=align;c.extrude=.00015;c.space_character=1.15
    o=obj(name,c,parent);o.location=loc;o.rotation_euler=rot;c.materials.append(mat);return o

def material(name,color,rough=.4,metal=0,coat=0,emission=0,trans=0):
    m=bpy.data.materials.get(name)
    if m:return m
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    p.inputs['Coat Weight'].default_value=coat;p.inputs['Coat Roughness'].default_value=.12
    p.inputs['Transmission Weight'].default_value=trans;p.inputs['IOR'].default_value=1.48
    if emission:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    return m

def surface_detail(m,scale,strength,distance,roughrange=None):
    nt=m.node_tree;n=nt.nodes;p=n.get('Principled BSDF')
    noise=n.new('ShaderNodeTexNoise');noise.name='V14 microstructure';noise.inputs['Scale'].default_value=scale;noise.inputs['Detail'].default_value=3
    tex=n.new('ShaderNodeTexCoord');nt.links.new(tex.outputs['Object'],noise.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=strength;bump.inputs['Distance'].default_value=distance
    nt.links.new(noise.outputs['Fac'],bump.inputs['Height'])
    if p.inputs['Normal'].is_linked:nt.links.new(p.inputs['Normal'].links[0].from_socket,bump.inputs['Normal'])
    nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    if roughrange:
        ramp=n.new('ShaderNodeMapRange');ramp.inputs['From Min'].default_value=.2;ramp.inputs['From Max'].default_value=.8
        ramp.inputs['To Min'].default_value=roughrange[0];ramp.inputs['To Max'].default_value=roughrange[1]
        nt.links.new(noise.outputs['Fac'],ramp.inputs['Value']);nt.links.new(ramp.outputs['Result'],p.inputs['Roughness'])

def interp(knots,y):
    for i in range(len(knots)-1):
        a,v=knots[i];b,w=knots[i+1]
        if y<=b:
            u=max(0,min(1,(y-a)/(b-a)));u=u*u*(3-2*u);return v+(w-v)*u
    return knots[-1][1]

def hide_tree(root):
    for o in root.children_recursive:
        o.hide_render=True;o.hide_set(True);o['CPO_archived_v13']=True

def new_source_root(name,old):
    o=obj(name,None,old);o.matrix_basis=Matrix.Rotation(pi/2,4,'X');return o

def materials():
    d={}
    d['blue']=material('V14 Midnight sapphire multi-coat',(.009,.032,.073),.21,.58,1)
    d['blackpaint']=material('V14 Obsidian pearl paint',(.007,.009,.012),.2,.48,1)
    for k in ['blue','blackpaint']:surface_detail(d[k],850,.10,.00008,(.18,.24))
    d['rubber']=material('V14 Tyre vulcanised rubber',(.013,.015,.017),.62)
    surface_detail(d['rubber'],180,.22,.00035,(.55,.7))
    d['trim']=material('V14 Satin moulded graphite',(.012,.016,.020),.35,.12)
    d['chrome']=material('V14 Machined bright aluminium',(.46,.51,.57),.19,.95)
    d['gun']=material('V14 Forged anthracite',(.045,.058,.075),.25,.85)
    d['glass']=material('V14 Automotive laminated glazing',(.91,.955,.98),.045,0,0,0,1)
    d['lens']=material('V14 Optical clear lens',(.98,.98,.98),.025,0,0,0,1)
    d['led']=material('V14 White LED phosphor',(.68,.85,1),.22,0,0,3)
    d['red']=material('V14 Ruby light lens',(.32,.006,.009),.16,.1,1,1.4)
    d['leather']=material('V14 Grained charcoal leather',(.017,.020,.024),.57)
    surface_detail(d['leather'],300,.20,.00025,(.49,.66))
    d['stitch']=material('V14 Warm grey stitching',(.25,.28,.29),.78)
    d['brake']=material('V14 Heat-treated brake steel',(.24,.27,.30),.4,.87)
    d['caliper']=material('V14 Blue brake caliper',(.012,.10,.40),.26,.35,1)
    return d

def car(tag,suv=False):
    global COL
    COL=collection('V14 / Vehicles');old=bpy.data.objects[tag]
    hide_tree(old);parent=new_source_root(tag+'.V14_SURFACES',old);m=materials();paint=m['blackpaint' if suv else 'blue']
    L,W,H=(4.34,1.79,1.59) if suv else (4.52,1.88,1.355);half=L/2;r=.346 if suv else .327;wheelYs=[-1.305,1.305] if suv else [-1.3,1.3]
    belt=1.055 if suv else .91
    wk=[(-half,.81),(-half+.17,.965),(-1.3,1),(-.2,.967),(.9,1),(1.6,.99),(half,.84)]
    hk=[(-half,.87 if suv else .73),(-half+.18,.95 if suv else .82),(-1.25,1.06 if suv else .93),(-.3,belt),(.9,belt),(1.65,1.035 if suv else .95),(half,.93 if suv else .79)]
    width=lambda y:W/2*interp(wk,y)
    top=lambda y:interp(hk,y)
    N=160;ys=[-half+L*i/N for i in range(N+1)]
    side_x=lambda y,t:width(y)*(.978+.029*sin(pi*t)-.022*t*t)
    for side in [-1,1]:
        rows=[]
        for y in ys:
            lower=.205 if not suv else .255
            for wy in wheelYs:
                if abs(y-wy)<r+.047:lower=max(lower,r+sqrt((r+.047)**2-(y-wy)**2))
            rows.append([(side*side_x(y,t),y,top(y)*(1-t)+lower*t) for t in [j/24 for j in range(25)]])
        patch(tag+'.V14.Sculpted flank'+str(side),rows,paint,parent,side<0,.002)
        curve(tag+'.V14.Belt crease'+str(side),[(side*width(y)*.984,y,top(y)-.023) for y in ys],.0018,m['trim'],parent)
        box(tag+'.V14.Sill'+str(side),(side*(W/2-.054),0,.205 if not suv else .254),(.07,1.98,.095),m['trim'],parent,.024)
        for wy in wheelYs:
            pts=[]
            for i in range(65):
                a=-.11+(pi+.22)*i/64;y=wy+(r+.051)*cos(a);pts.append((side*(width(y)*.976+.006),y,r+(r+.051)*sin(a)))
            curve(tag+'.V14.Wheelarch'+str(side)+str(wy),pts,.018 if suv else .009,m['trim'] if suv else paint,parent)
        for yy in ([.28,1.27] if suv else [1.05]):
            pts=[(side*side_x(yy,t)*1.0004,yy,top(yy)*(1-t)+.25*t) for t in [i/20 for i in range(20)]]
            curve(tag+'.V14.Panel gap'+str(side)+str(yy),pts,.0016,m['trim'],parent)
        for yy in ([.11,1.15] if suv else [.78]):
            box(tag+'.V14.Door recess'+str(side)+str(yy),(side*width(yy)*.99,yy,belt-.045),(.013,.19,.043),m['trim'],parent,.018)
            box(tag+'.V14.Flush handle'+str(side)+str(yy),(side*(width(yy)*.99+.008),yy,belt-.045),(.01,.151,.023),paint,parent,.009)
    # Gently domed hood, continuous shoulder surfaces and roof.
    cfront=-1.03 if suv else -.91;crear=1.72 if suv else 1.76
    for a,b,label in [(-half,cfront,'Hood'),(crear,half,'Rear deck')]:
        yy=[a+(b-a)*i/60 for i in range(61)]
        rows=[]
        for y in yy:
            rows.append([(u*width(y)*.978,y,top(y)+(.058 if label=='Hood' else .038)*(1-u*u)) for u in [-1+2*j/40 for j in range(41)]])
        patch(tag+'.V14.'+label,rows,paint,parent,False,.002)
        if label=='Hood':
            for side in [-1,1]:
                curve(tag+'.V14.Hood shutline'+str(side),[(side*.77*width(y),y,top(y)+.058*(1-.77**2)+.002) for y in yy[3:-2]],.0017,m['trim'],parent)
    # Front/rear panels wrap into side shoulders.
    for end in [-1,1]:
        yy=end*half;rows=[]
        for j in range(25):
            v=j/24;z=.22+(top(yy)-.22)*v
            rows.append([(u*width(yy),yy-end*(.16*u*u+.018*sin(pi*v)),z+.014*(1-u*u)*v) for u in [-1+2*i/64 for i in range(65)]])
        patch(tag+'.V14.Bumper skin'+str(end),rows,paint,parent,end<0,.0025)
        box(tag+'.V14.Splitter'+str(end),(0,yy-end*.005,.217),(W*.84,.10,.045),m['trim'],parent,.015)
    roofY0=-.20 if suv else -.25;roofY1=1.07 if suv else .72
    canH=[(cfront,top(cfront)+.015),(roofY0,H-.015),(roofY1,H-.02),(crear,top(crear)+.015)]
    canW=[(cfront,W*.43),(roofY0,W*.385),(roofY1,W*.385),(crear,W*.43)]
    high=lambda y:interp(canH,y)
    cw=lambda y:interp(canW,y)
    for a,b,label,mat in [(cfront,roofY0,'Windshield',m['glass']),(roofY0,roofY1,'Roof',paint),(roofY1,crear,'Rear glass',m['glass'])]:
        rows=[]
        for i in range(51):
            y=a+(b-a)*i/50
            rows.append([(u*cw(y),y,high(y)-.045*u*u) for u in [-1+2*j/40 for j in range(41)]])
        patch(tag+'.V14.'+label,rows,mat,parent,False,.004 if 'glass' in label.lower() or label=='Windshield' else .009)
    for side in [-1,1]:
        yy=[cfront+(crear-cfront)*i/90 for i in range(91)]
        rows=[[(side*(cw(y)*(1-t)+width(y)*.968*t),y,(high(y)-.045)*(1-t)+(top(y)+.013)*t) for t in [j/16 for j in range(17)]] for y in yy]
        patch(tag+'.V14.Side glazing'+str(side),rows,m['glass'],parent,side<0,.004)
        upper=[(side*cw(y),y,high(y)-.042) for y in yy]
        bottom=[(side*width(y)*.97,y,top(y)+.01) for y in yy]
        curve(tag+'.V14.Window upper seal'+str(side),upper,.014,paint,parent)
        curve(tag+'.V14.Window lower seal'+str(side),bottom,.010,m['chrome'] if suv else m['trim'],parent)
        for y in ([cfront,.35,1.26,crear] if suv else [cfront,.69,crear]):
            curve(tag+'.V14.Structural pillar'+str(side)+str(y),[(side*cw(y),y,high(y)-.041),(side*width(y)*.97,y,top(y)+.013)],.038 if y in [cfront,crear] else .034,m['trim'],parent)
        # Wide painted rear pillar gives each body its own silhouette.
        yy2=[roofY1+.04+(crear-roofY1-.04)*i/32 for i in range(33)]
        rows2=[[(side*(cw(y)*(1-t)+width(y)*.970*t),y,(high(y)-.04)*(1-t)+(top(y)+.012)*t) for t in [.0,.18,.36]] for y in yy2]
        patch(tag+'.V14.Rear pillar shoulder'+str(side),rows2,paint,parent,side<0,.009)
        cylinder(tag+'.V14.Mirror arm'+str(side),(side*.82,-.66,belt+.07),(side*(W/2+.055),-.60,belt+.12),.022,m['trim'],parent,24)
        ellipsoid(tag+'.V14.Mirror cap'+str(side),(side*(W/2+.047),-.55,belt+.14),(.092,.133,.058),paint,parent)
        box(tag+'.V14.Mirror reflective face'+str(side),(side*(W/2+.047),-.427,belt+.14),(.13,.005,.073),m['chrome'],parent,.025)
        curve(tag+'.V14.Mirror indicator'+str(side),[(side*(W/2+.115),-.63,belt+.135),(side*(W/2+.13),-.53,belt+.13)],.0035,m['led'],parent)
    # Recessed headlamp lenses, projectors and precise light guides.
    for side in [-1,1]:
        yc=-half-.006;z=.885 if suv else .775
        lamp=box(tag+'.V14.Headlamp housing'+str(side),(side*.58,yc,z),(.54,.065,.083),m['trim'],parent,.03);lamp.rotation_euler[2]=side*.11
        lens=box(tag+'.V14.Headlamp glass'+str(side),(side*.58,yc-.035,z),(.52,.013,.068),m['lens'],parent,.022);lens.rotation_euler[2]=side*.11
        for k in range(4):
            x=side*(.36+k*.12)
            cylinder(tag+'.V14.Optical projector'+str(side)+str(k),(x,yc-.032,z),(x,yc-.043,z),.022,m['chrome'],parent,32)
            cylinder(tag+'.V14.Projector lens'+str(side)+str(k),(x,yc-.044,z),(x,yc-.047,z),.017,m['led'],parent,32)
        curve(tag+'.V14.DRL'+str(side),[(side*.32,yc-.047,z+.035),(side*.77,yc+.018,z+.035),(side*.85,yc+.085,z+.02)],.0035,m['led'],parent)
        curve(tag+'.V14.Rear signature'+str(side),[(side*.05,half+.007,.90 if suv else .82),(side*.71,half-.027,.90 if suv else .82),(side*.83,half-.18,.94 if suv else .84)],.007,m['red'],parent)
    grilleZ=.67 if suv else .43;grilleH=.30 if suv else .24
    box(tag+'.V14.Deep intake',(0,-half-.016,grilleZ),(1.28,.034,grilleH),m['trim'],parent,.055)
    if suv:
        for j in range(6):box(tag+'.V14.Grille blade'+str(j),(0,-half-.038,grilleZ-grilleH*.4+j*.048),(1.20,.018,.018),paint,parent,.006)
    else:
        for j in range(4):
            for i in range(24):
                x=-.575+i*.05+(j%2)*.025;z=grilleZ-.083+j*.05
                pts=[(x+.027*cos(k*pi/3),-half-.037,z+.027*sin(k*pi/3)) for k in range(6)]
                curve(tag+'.V14.Honeycomb'+str(i)+'_'+str(j),pts,.002,m['gun'],parent,True)
        for side in [-1,1]:box(tag+'.V14.Brake inlet'+str(side),(side*.76,-half+.025,.48),(.19,.034,.18),m['trim'],parent,.045)
    box(tag+'.V14.Number plate',(0,-half-.060,.48 if suv else .65),(.32,.01,.145),m['trim'],parent,.008)
    text(tag+'.V14.Model plate','VEZEL' if suv else 'PRELUDE',(0,-half-.067,.47 if suv else .64),.042,m['stitch'],parent)
    # Torus-like tyre profiles, machined paired spokes and drilled brake discs.
    for side in [-1,1]:
        for wy in wheelYs:
            xc=side*(W/2-.093);outer=xc+side*.106
            profile=[(-.11,r*.75),(-.117,r*.84),(-.107,r*.93),(-.079,r*.994),(-.05,r),(.05,r),(.079,r*.994),(.107,r*.93),(.117,r*.84),(.11,r*.75)]
            rows=[[(xc+dx,wy+rr*cos(2*pi*i/96),r+rr*sin(2*pi*i/96)) for i in range(97)] for dx,rr in profile]
            patch(tag+'.V14.Tyre'+str(side)+str(wy),rows,m['rubber'],parent,side<0)
            for off in [-.048,-.016,.016,.048]:ring(tag+'.V14.Tread groove'+str(side)+str(wy)+str(off),(xc+off,wy,r),r+.0004,.0013,m['trim'],parent)
            for k in range(60):
                a=k*2*pi/60
                pts=[(xc+dx,wy+(r+.0007)*cos(a+dx*.45),r+(r+.0007)*sin(a+dx*.45)) for dx in [-.064,0,.064]]
                curve(tag+'.V14.Tread siping'+str(side)+str(wy)+str(k),pts,.0007,m['trim'],parent)
            ring(tag+'.V14.Rim lip'+str(side)+str(wy),(outer,wy,r),r*.762,.010,m['chrome'],parent)
            ring(tag+'.V14.Rim barrel'+str(side)+str(wy),(outer-side*.04,wy,r),r*.745,.025,m['gun'],parent)
            cylinder(tag+'.V14.Vented brake'+str(side)+str(wy),(outer-side*.048,wy,r),(outer-side*.04,wy,r),r*.645,m['brake'],parent,96)
            for k in range(24):
                a=2*pi*k/24
                for rr in [r*.51,r*.59]:
                    y=wy+rr*cos(a);z=r+rr*sin(a)
                    cylinder(tag+'.V14.Disc drilling'+str(side)+str(wy)+str(k)+str(rr),(outer-side*.039,y,z),(outer-side*.038,y,z),.0035,m['trim'],parent,8)
            box(tag+'.V14.Caliper'+str(side)+str(wy),(outer-side*.018,wy+.174,r+.04),(.061,.077,.18),m['caliper'] if not suv else m['gun'],parent,.018)
            for k in range(5):
                a=2*pi*k/5
                for delta in [-.065,.065]:
                    ps=[]
                    for rr,aa in [(.055,a-.07),(r*.735,a+delta+.10),(r*.75,a+delta+.17),(.065,a+.10)]:ps.append((outer,wy+rr*cos(aa),r+rr*sin(aa)))
                    o=mesh(tag+'.V14.Forged spoke'+str(side)+str(wy)+str(k)+str(delta),ps,[(0,1,2,3)],m['chrome'] if suv else m['gun'],parent)
                    so=o.modifiers.new('Spoke thickness','SOLIDIFY');so.thickness=.014
                    be=o.modifiers.new('Spoke edge','BEVEL');be.width=.004;be.segments=3
            cylinder(tag+'.V14.Hub'+str(side)+str(wy),(outer-side*.006,wy,r),(outer+side*.008,wy,r),.065,m['gun'],parent,48)
            for k in range(5):
                a=2*pi*k/5;y=wy+.046*cos(a);z=r+.046*sin(a)
                cylinder(tag+'.V14.Hex fastener'+str(side)+str(wy)+str(k),(outer,y,z),(outer+side*.012,y,z),.006,m['chrome'],parent,6)
    box(tag+'.V14.Cabin floor',(0,.18,.28),(1.55,2.30,.09),m['trim'],parent,.03)
    box(tag+'.V14.Dashboard',(0,-.74,.73 if not suv else .89),(1.56,.38,.18),m['leather'],parent,.07)
    for side in [-1,1]:
        box(tag+'.V14.Seat cushion'+str(side),(side*.39,.22,.47 if not suv else .59),(.47,.52,.14),m['leather'],parent,.065)
        back=box(tag+'.V14.Seat back'+str(side),(side*.39,.48,.78 if not suv else .93),(.45,.14,.59),m['leather'],parent,.06);back.rotation_euler[0]=-.12
        ellipsoid(tag+'.V14.Head restraint'+str(side),(side*.39,.51,1.10 if not suv else 1.25),(.17,.078,.105),m['leather'],parent)
        for xoff in [-.15,.15]:curve(tag+'.V14.Seat piping'+str(side)+str(xoff),[(side*.39+xoff,.396,.57),(side*.39+xoff,.437,1.02 if not suv else 1.17)],.0015,m['stitch'],parent)
    parent['vehicle_reference']='Honda Vezel reference photo' if suv else 'Honda Prelude reference photo'
    parent['status']='Original photo-guided reconstruction; not manufacturer CAD.'
    print('V14_CAR_DONE',tag,len(parent.children_recursive),flush=True)
    return parent

def magazines():
    global COL
    COL=collection('V14 / Editorial magazines')
    atlas=bpy.data.images.load(str(ROOT/'assets/textures/v14/editorial-covers-atlas.png'),check_existing=True);atlas.pack()
    paper=material('V14 Uncoated page edges',(.69,.665,.60),.86)
    surface_detail(paper,1200,.12,.00008)
    mats=[]
    for i in range(4):
        m=material('V14 Editorial cover '+str(i),(.8,.8,.8),.39,0,.22)
        nt=m.node_tree;n=nt.nodes.new('ShaderNodeTexImage');n.image=atlas;n.interpolation='Linear';n.extension='EXTEND'
        nt.links.new(n.outputs['Color'],nt.nodes.get('Principled BSDF').inputs['Base Color'])
        surface_detail(m,900,.12,.000055,(.32,.44));mats.append(m)
    for k in range(8):
        old=bpy.data.objects[f'F05.Magazine.{k:02d}.Cover'];pts=[old.matrix_world@Vector(p) for p in old.bound_box]
        center=sum(pts,Vector())/8
        for suffix in ['Cover','Pages','Spine']:
            o=bpy.data.objects.get(f'F05.Magazine.{k:02d}.{suffix}')
            if o:o.hide_render=True;o.hide_set(True);o['CPO_archived_v13']=True
        p=obj(f'V14 Magazine {k+1:02d}',None);p.location=(center.x+(.012 if k%2 else -.008),center.y,.71365)
        p.rotation_euler[2]=math.radians([-2.1,1.8,1.4,-2.8,-1.1,2.2,1.9,-1.2][k])
        width=.25;length=.347;thick=.0048+(k%3)*.0006
        box('V14 Page block '+str(k),(0,0,thick/2),(width-.0009,length-.0012,thick),paper,p,.0003)
        # Fine independent page edges, with a minute curvature towards the free edge.
        for j in range(16):
            z=.00025+j*thick/17
            curve(f'V14 Paper leaf {k}.{j}',[(width/2-.0002,-length/2+.001,z),(width/2+.0001,0,z+.00012),(width/2-.0003,length/2-.001,z+.00025)],.000045,paper,p)
        rows=[]
        for j in range(33):
            v=j/32;y=(v-.5)*length
            rows.append([((u-.5)*width,y,thick+.00012+.0008*u**4+.00025*sin(pi*v)*u) for u in [i/24 for i in range(25)]])
        issue=k%4;uvrect=((issue%2)*.5+.001,(1-issue//2)*.5+.001,.498,.498)
        patch('V14 Printed cover '+str(k),rows,mats[issue],p,False,.00019,uvrect)
        curve('V14 Folded spine '+str(k),[(-width/2,-length/2,thick*.45),(-width/2-.0004,0,thick*.45),(-width/2,length/2,thick*.45)],.0018,paper,p)
    glass=bpy.data.materials['M119_F05_Clear_Display_Glass'];principled=glass.node_tree.nodes.get('Principled BSDF')
    principled.inputs['Roughness'].default_value=.025;principled.inputs['Base Color'].default_value=(.96,.985,.975,1)
    principled.inputs['IOR'].default_value=1.51
    surface_detail(glass,170,.025,.000035,(.018,.038))
    print('V14_MAGAZINES_DONE',flush=True)

def detail_interior():
    global COL
    COL=collection('V14 / Workshop details');count=0
    for mat in list(bpy.data.materials):
        if mat.name.startswith('V14') or not mat.use_nodes:continue
        p=mat.node_tree.nodes.get('Principled BSDF')
        if not p:continue
        name=mat.name.lower()
        if any(k in name for k in ['chrome','steel','nickel','metal','aluminium','socket']):
            surface_detail(mat,350,.11,.00010);count+=1
        elif any(k in name for k in ['wood','walnut','charcoal_wall','black_wall','wall_finish']):
            surface_detail(mat,190,.13,.00022);count+=1
        elif any(k in name for k in ['rubber','grip','plastic']):
            surface_detail(mat,320,.12,.00017);count+=1
    refined=0
    for o in list(bpy.data.objects):
        if o.type!='MESH' or o.hide_render or not o.name.startswith('V12.'):continue
        if any(k in o.name for k in ['Wrench','Spanner','Hammer','Socket','Ratchet','Plier','Screwdriver','Board']):
            mod=o.modifiers.new('V14 Precision edge highlights','BEVEL');mod.width=.00065;mod.segments=3;mod.limit_method='ANGLE'
            refined+=1
    # Folded microfiber cloth: dense curved surface, subtle woven normal detail.
    fabric=material('V14 Woven slate microfiber',(.045,.061,.073),.89)
    surface_detail(fabric,850,.32,.00018)
    # Use the existing cloth's actual location, never invent a position on the bench.
    candidates=[o for o in bpy.data.objects if 'Cloth' in o.name and o.type=='MESH' and 'V12' in o.name]
    if candidates:
        old=candidates[0];pts=[old.matrix_world@Vector(p) for p in old.bound_box];lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
        old.hide_render=True;old.hide_set(True)
        rows=[]
        for j in range(35):
            v=j/34
            rows.append([(lo[0]+(hi[0]-lo[0])*u,lo[1]+(hi[1]-lo[1])*v,lo[2]+.003+.003*sin(pi*u)**2+.0008*sin(u*24+v*4)) for u in [i/34 for i in range(35)]])
        patch('V14 Folded microfiber',rows,fabric,solid=.002)
    print('V14_INTERIOR_DONE',count,refined,flush=True)

def cabin():
    global COL
    COL=collection('V14 / Driving cabin');m=materials();old=bpy.data.objects['ARRIVAL_CAR'];p=new_source_root('ARRIVAL_CAR.V14_CABIN',old)
    for o in old.children_recursive:
        if any(k in o.name for k in ['Dashboard','SteeringWheel','SteeringSpokes','WheelHub','SeatCushion','SeatBack','HeadRest','DashLight']):
            o.hide_render=True;o.hide_set(True)
    box('V14 Cabin dashboard',(0,-.77,.745),(1.58,.40,.15),m['leather'],p,.065)
    box('V14 Floating fascia',(0,-.565,.727),(1.53,.065,.12),m['trim'],p,.025)
    # Long but restrained ventilation fascia, physically separated blades.
    for i in range(45):
        x=-.70+i*.032
        box('V14 Cabin vent '+str(i),(x,-.528,.728),(.014,.014,.038),m['gun'],p,.003)
    curve('V14 Dashboard contrast seam',[(-.73,-.56,.81),(-.40,-.54,.818),(.1,-.54,.818),(.73,-.56,.81)],.0013,m['stitch'],p)
    screen=material('V14 Instrument OLED',(.010,.025,.032),.27,.1,0,.5)
    box('V14 Driver binnacle',(.40,-.604,.855),(.36,.054,.13),m['trim'],p,.025)
    box('V14 Driver display',(.40,-.573,.852),(.32,.006,.09),screen,p,.012)
    text('V14 Instrument readout','48',(.40,-.568,.834),.045,m['led'],p,(pi/2,0,pi))
    # Central screen deliberately small enough not to block the car-window view.
    box('V14 Centre display frame',(-.03,-.605,.875),(.30,.037,.14),m['trim'],p,.015)
    box('V14 Centre display',(-.03,-.584,.878),(.27,.005,.111),screen,p,.010)
    text('V14 Navigation display','NIGHT DRIVE',(-.03,-.58,.885),.016,m['stitch'],p,(pi/2,0,pi))
    box('V14 Centre console',(0,.14,.50),(.19,.64,.21),m['trim'],p,.06)
    for y in [.12,.30]:ring('V14 Cup holder '+str(y),(0,y,.61),.053,.009,m['gun'],p,'Z')
    # Steering wheel and real flattened spokes, controls, and leather rim.
    ring('V14 Leather steering wheel',(.42,-.39,.78),.162,.018,m['leather'],p,'Y',96)
    box('V14 Steering airbag',(.42,-.39,.77),(.17,.049,.108),m['leather'],p,.04)
    for sign in [-1,1]:
        box('V14 Steering switch '+str(sign),(.42+sign*.109,-.381,.78),(.064,.026,.033),m['gun'],p,.008)
        for j in range(3):box('V14 Wheel key'+str(sign)+str(j),(.42+sign*.109+j*.013-.013,-.363,.78),(.008,.003,.008),m['trim'],p,.001)
    curve('V14 Lower wheel spoke',[(.42,-.39,.73),(.42,-.39,.63)],.015,m['gun'],p)
    for side in [-1,1]:
        box('V14 Driving seat cushion'+str(side),(side*.39,.19,.49),(.46,.53,.13),m['leather'],p,.06)
        back=box('V14 Driving seat back'+str(side),(side*.39,.47,.79),(.46,.145,.57),m['leather'],p,.055);back.rotation_euler[0]=-.12
        for off in [-.18,.18]:
            ellipsoid('V14 Seat bolster'+str(side)+str(off),(side*.39+off,.365,.78),(.062,.095,.235),m['leather'],p)
        ellipsoid('V14 Driving headrest'+str(side),(side*.39,.50,1.10),(.165,.072,.11),m['leather'],p)
    print('V14_CABIN_DONE',flush=True)

def city():
    global COL
    COL=collection('V14 / Night city');rng=random.Random(1426)
    old=bpy.data.objects['CITY_PERIODIC_STREET'];hide_tree(old)
    # Replace skyline and portal blockouts, retain road/sidewalk and stationary shop-side lamps.
    for o in bpy.data.objects:
        if o.name.startswith('CITY.Skyline'):o.hide_render=True;o.hide_set(True)
    parent=new_source_root('V14_CITY_PERIODIC_STRUCTURE',old)
    concrete=material('V14 City dark architectural stone',(.036,.048,.064),.64)
    surface_detail(concrete,7,.22,.0014,(.49,.72))
    glazing=material('V14 City blue reflective glass',(.015,.035,.055),.20,.65,.4)
    metal=material('V14 City brushed aluminium fins',(.052,.065,.080),.28,.83)
    amber=material('V14 City warm occupied windows',(.65,.40,.20),.35,0,0,2.8)
    warmwhite=material('V14 City occupied neutral windows',(.50,.62,.72),.3,0,0,1.7)
    cyan=material('V14 City cyan architectural light',(.04,.36,.50),.28,0,0,4)
    darkwin=material('V14 City unlit windows',(.006,.013,.020),.22,.40)
    # Same 32m macro-period as the retained idle action; near detail varies within each module.
    for bi,x in enumerate(range(-128,129,16)):
        for side,y in enumerate([-22,20]):
            seed=random.Random(431+(bi%2)*27+side*73);h=seed.choice([21,28,34,42]);w=seed.uniform(9,12);depth=seed.uniform(8,11)
            building=obj(f'V14 City block {bi}.{side}',None,parent)
            front=y+depth/2 if side==0 else y-depth/2
            box(f'V14 Tower podium {bi}.{side}',(x,y,2.2),(w+1,depth+.8,4.4),concrete,building,.10)
            box(f'V14 Tower glazing {bi}.{side}',(x,y,4.4+(h-4.4)/2),(w,depth,h-4.4),glazing,building,.16)
            box(f'V14 Tower crown {bi}.{side}',(x,y,h+.10),(w-.25,depth-.25,.35),metal,building,.07)
            # Facade panels are batched into meshes by material, with interior setbacks.
            verts=[[],[],[]];faces=[[],[],[]]
            cols=int(w/1.1);floors=int((h-5)/2.8)
            for floor in range(floors):
                for col in range(cols):
                    bucket=seed.choices([0,1,2],[.55,.25,.20])[0];xx=x-w/2+.65+col*(w-1.3)/max(cols-1,1);zz=5.3+floor*2.8
                    a=len(verts[bucket]);fw=.72;fh=1.8
                    verts[bucket]+= [(xx-fw/2,front+(-.035 if side else .035),zz-fh/2),(xx+fw/2,front+(-.035 if side else .035),zz-fh/2),(xx+fw/2,front+(-.035 if side else .035),zz+fh/2),(xx-fw/2,front+(-.035 if side else .035),zz+fh/2)]
                    faces[bucket].append((a,a+1,a+2,a+3))
            for k,mat in enumerate([darkwin,amber,warmwhite]):
                if verts[k]:mesh(f'V14 Recessed lit offices {bi}.{side}.{k}',verts[k],faces[k],mat,building,False)
            for j in range(cols+1):
                xx=x-w/2+j*w/cols
                box(f'V14 Facade fin {bi}.{side}.{j}',(xx,front,4.4+(h-4.4)/2),(.048,.23,h-4.4),metal,building,.013)
            for floor in range(floors+1):
                box(f'V14 Floor slab {bi}.{side}.{floor}',(x,front,4.5+floor*2.8),(w+.10,.24,.08),metal,building,.018)
            # Luminous reveals only on selected edges, not a full neon outline.
            for xx in [x-w/2+.1,x+w/2-.1]:
                box(f'V14 Light reveal {bi}.{side}.{xx}',(xx,front+(-.13 if side else .13),h*.63),(.022,.018,h*.62),cyan,building,.004)
            for j in range(3):
                xx=x+(j-1)*w*.24
                box(f'V14 Ground retail window {bi}.{side}.{j}',(xx,front+(-.43 if side else .43),1.8),(w*.21,.025,2.5),darkwin,building,.02)
            box(f'V14 Retail canopy {bi}.{side}',(x,front,3.5),(w+.5,1.5,.13),metal,building,.04)
    far=collection('V14 / Distant skyline');COL=far
    for k in range(28):
        x=rng.uniform(-105,150);y=rng.choice([-1,1])*rng.uniform(50,85);h=rng.uniform(35,90);w=rng.uniform(5,11)
        box(f'V14 Distant tower {k}',(x,y,h/2),(w,w*.85,h),glazing,None,.20)
        for q in range(3):box(f'V14 Distant illuminated band {k}.{q}',(x,y-w*.426,h*(.45+.17*q)),(w*.8,.02,.10),warmwhite,None,.01)
    COL=collection('V14 / Street foreground')
    asphalt=bpy.data.materials.get('CITY.Asphalt')
    if asphalt:surface_detail(asphalt,42,.32,.0008,(.19,.45))
    paving=bpy.data.materials.get('CITY.Paving')
    if paving:surface_detail(paving,65,.24,.0008,(.47,.65))
    # Roadside furniture stays away from the entrance and the recorded walking corridor.
    for x in range(-64,81,8):
        for y in [-15.1,-1.90]:
            if -2<x<15 and y>-8:continue
            box(f'V14 Curb {x}.{y}',(x,y,-.035),(7.95,.20,.23),concrete,None,.022)
            if x%16==0:
                cylinder(f'V14 Bollard {x}.{y}',(x,y,.05),(x,y,.72),.055,metal,None,24)
                ring(f'V14 Bollard reflector {x}.{y}',(x,y,.61),.056,.006,warmwhite,None,'Z')
    for x in [-30,-14,22,38]:
        box(f'V14 Linear planter {x}',(x,-16.2,.36),(2.8,.7,.72),concrete,None,.06)
        for j in range(18):
            xx=x+rng.uniform(-1.2,1.2);yy=-16.2+rng.uniform(-.24,.24)
            curve(f'V14 Grasses {x}.{j}',[(xx,yy,.71),(xx+.05,yy,.95),(xx+.10,yy,1.18+rng.random()*.20)],.009,material('V14 Grass silver green',(.085,.13,.10),.82))
    print('V14_CITY_DONE',flush=True)

def lighting_camera():
    global COL
    COL=collection('V14 / Lighting and optics');s=bpy.context.scene
    for name in ['Street_Sky','Prelude_Softbox','Vezel_Softbox','Tool_Warm','Magazine_Fill','Office_Fill']:
        o=bpy.data.objects.get(name)
        if o:o.hide_render=True;o.hide_set(True)
    def area(name,pos,target,power,size,color,size_y=None):
        d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='RECTANGLE';d.size=size;d.size_y=size_y or size
        o=obj(name,d);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
    area('V14 Shop ceiling bounce',(5,1.8,2.97),(5,2,0),330,7,(.89,.85,.78),2.0)
    area('V14 Prelude long highlight',(.5,1.2,2.83),(1.5,1.3,.8),185,.40,(.69,.81,1),3.8)
    area('V14 Vezel long highlight',(10,1.2,2.83),(8.9,1.3,.8),195,.40,(.93,.85,.72),3.8)
    area('V14 Front window blue bounce',(5,-2.8,2.9),(5,1.8,1),320,7,(.43,.62,1),2)
    area('V14 Toolboard soft key',(7.0,3.8,2.7),(7.6,4.9,1.3),100,1.35,(1,.78,.55),.6)
    area('V14 Magazine raking key',(.4,5.6,2.6),(1.15,6.2,.73),80,.48,(1,.88,.74),1.2)
    area('V14 Office ambient',(3.2,6.8,2.8),(2.4,6.6,1.2),68,1,(.76,.87,1),1)
    area('V14 Urban moon',(-22,-28,35),(0,-4,0),2800,22,(.39,.54,1),22)
    for x in [-48,-16,16,48,80]:area('V14 Avenue light '+str(x),(x,-10,7),(x,-6,0),230,3,(.45,.72,1),1)
    world=bpy.data.worlds.new('V14 Deep blue night');world.use_nodes=True;s.world=world
    bg=world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.018,.030,.055,1);bg.inputs['Strength'].default_value=.22
    s.render.engine='CYCLES';s.cycles.samples=128;s.cycles.preview_samples=24;s.cycles.use_denoising=True
    s.cycles.max_bounces=10;s.cycles.transmission_bounces=8;s.cycles.glossy_bounces=6
    s.view_settings.view_transform='AgX';s.view_settings.exposure=.35
    # Keep the entire baked camera and animate only a separate local micro-motion camera.
    base=bpy.data.objects.get('CPO_CINEMATIC_CAMERA');base.name='CPO_BASE_CAMERA_v13'
    c=base.data.copy();c.name='V14 Cinematic optics';camera=obj('CPO_CINEMATIC_CAMERA',c,base);camera.matrix_basis=Matrix.Identity(4);s.camera=camera
    camera['CPO_motion']='Local breathing and body sway; original route remains on CPO_BASE_CAMERA_v13.'
    c.dof.use_dof=True;c.dof.aperture_fstop=5.6;c.dof.aperture_blades=9
    def driver(path,index,expression):
        f=camera.driver_add(path,index);f.driver.type='SCRIPTED';f.driver.expression=expression
    # All motion is smooth and sub-centimetre; positive local Z points away from the subject.
    driver('location',0,'0.0018*sin(frame/30*0.91)+0.0006*sin(frame/30*1.73+0.8)')
    driver('location',1,'0.0012*sin(frame/30*1.31)+0.0004*sin(frame/30*0.43)')
    driver('location',2,'0.0007*sin(frame/30*1.08+0.4)')
    driver('rotation_euler',0,'0.0007*sin(frame/30*0.71+0.9)')
    driver('rotation_euler',1,'0.0009*sin(frame/30*0.63)')
    driver('rotation_euler',2,'0.0005*sin(frame/30*0.49+0.2)')
    for frame,distance in [(0,30),(378,14),(648,7),(1026,1.65),(1296,1.65),(1550,2.8),(1701,1.00),(2025,1.00),(2200,2.0),(2430,.85),(2520,.56),(2700,.275)]:
        c.dof.focus_distance=distance;c.dof.keyframe_insert('focus_distance',frame=frame)
    s.frame_set(1080)
    s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
    s['CPO_refinement']='v14 integrated model, materials, city, lighting and micro-motion; final loop segmentation remains a later decision.'
    print('V14_LIGHTING_CAMERA_DONE',flush=True)

def save():
    bpy.ops.file.pack_all()
    for a in bpy.data.actions:a.use_fake_user=True
    path=ROOT/'assets/blender/CPO_v14_refined.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    print('V14_SAVED',str(path),flush=True)

def finish_from_review():
    global COL
    COL=collection('V14 / Lighting and optics');s=bpy.context.scene
    m=bpy.data.materials.get('ARRIVAL_CAR.SmokedGlass')
    if m:
        p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.96,.98,.99,1)
        p.inputs['Metallic'].default_value=0;p.inputs['Roughness'].default_value=.025;p.inputs['Transmission Weight'].default_value=1;p.inputs['IOR'].default_value=1.46
    for name,power in [('V14 Shop ceiling bounce',145),('V14 Front window blue bounce',150),('V14 Toolboard soft key',68),('V14 Magazine raking key',65),('V14 Office ambient',42),('V14 Prelude long highlight',125),('V14 Vezel long highlight',125)]:
        bpy.data.objects[name].data.energy=power
    key=bpy.data.objects['V14 Magazine raking key'];key.location=(2.8,5.3,2.6);key.rotation_euler=(Vector((1.1,6.15,.73))-key.location).to_track_quat('-Z','Y').to_euler()
    for o in bpy.data.objects:
        if o.name.startswith('V14 Avenue light '):o.data.energy=700
    s.view_settings.exposure=.45
    # Night horizon, with the volume confined to the avenue rather than the shop.
    nt=s.world.node_tree;coord=nt.nodes.new('ShaderNodeTexCoord');sep=nt.nodes.new('ShaderNodeSeparateXYZ');ramp=nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(coord.outputs['Normal'],sep.inputs[0]);nt.links.new(sep.outputs['Z'],ramp.inputs[0])
    ramp.color_ramp.elements[0].position=0;ramp.color_ramp.elements[0].color=(.07,.10,.18,1)
    ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.002,.005,.016,1)
    nt.links.new(ramp.outputs[0],nt.nodes.get('Background').inputs['Color']);nt.nodes.get('Background').inputs['Strength'].default_value=.3
    volume=bpy.data.materials.new('V14 Avenue atmospheric depth');volume.use_nodes=True
    nodes=volume.node_tree.nodes;nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');v=nodes.new('ShaderNodeVolumePrincipled');v.inputs['Density'].default_value=.0007;v.inputs['Color'].default_value=(.46,.56,.70,1);v.inputs['Anisotropy'].default_value=.25
    volume.node_tree.links.new(v.outputs['Volume'],output.inputs['Volume'])
    fog=box('V14 Avenue haze',(0,-44,35),(320,80,70),volume,bevel=0);fog.display_type='WIRE'
    # Reversible view-direction correction through the rear turn.
    # The original root position remains unchanged; the new node holds only relative rotation.
    import numpy as np
    samples=np.load(ROOT/'assets/source/v13/animation/camera_samples.npz')
    base=bpy.data.objects['CPO_BASE_CAMERA_v13'];camera=s.camera
    correction=obj('CPO_REAR_TURN_GAZE',None,base);correction.rotation_mode='QUATERNION'
    camera.parent=correction
    correction.rotation_quaternion=(1,0,0,0);correction.keyframe_insert('rotation_quaternion',frame=0)
    for f in range(2025,2431,5):
        p=Vector(samples['source_position'][f]);a=samples['source_quaternion'][f];q=Quaternion((a[3],a[0],a[1],a[2]))
        t=(f-2025)/(2430-2025);weight=sin(pi*t)**2
        target=Vector((3.55-1.0*t,6.65,1.24))
        desired=(target-p).to_track_quat('-Z','Y');angle=q.rotation_difference(desired).angle
        weight=min(weight,math.radians(105)/max(angle,.001))
        rel=q.inverted()@q.slerp(desired,weight);correction.rotation_quaternion=rel;correction.keyframe_insert('rotation_quaternion',frame=f)
    correction.rotation_quaternion=(1,0,0,0);correction.keyframe_insert('rotation_quaternion',frame=2430);correction.keyframe_insert('rotation_quaternion',frame=2700)
    correction['CPO_role']='Gaze correction only, no path position changes. Inspect from 67.5–81 seconds.'
    # Keep the maximum blur modest when reading printed covers and small tools.
    camera.data.dof.aperture_fstop=6.3
    s.frame_set(1080)
    print('V14_FINISH_REVIEW_DONE',flush=True)

def fix_laminated_glass():
    # Legacy cabin panes were open single surfaces. Real transmission requires
    # an exit interface as well as an entry interface, otherwise refraction bends
    # the entire view into the interior instead of through a laminated pane.
    for name in ['ARRIVAL_CAR.Windshield','ARRIVAL_CAR.RearGlass','ARRIVAL_CAR.DoorGlass']:
        o=bpy.data.objects.get(name)
        if o and not o.modifiers.get('V14 Laminated glass thickness'):
            m=o.modifiers.new('V14 Laminated glass thickness','SOLIDIFY');m.thickness=.0038;m.offset=0;m.use_quality_normals=True
    fog=bpy.data.objects.get('V14 Avenue haze')
    if fog:fog['CPO_nonphysical']=True
    print('V14_LAMINATED_GLASS_DONE',flush=True)
