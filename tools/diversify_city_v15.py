"""Distinct street architecture and a real transverse intersection for v15."""
import bpy,math,random,importlib.util
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('city',ROOT/'tools/city_v15.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c);h=c.h;v=c.v

def disable_prefix(tile,prefix):
    for o in tile.objects:
        if o.name.startswith(prefix):o.hide_render=True

def rounded_hotel(parent):
    x=-29;cy=10.15;rx=9.1;ry=8.0;height=76;glass=bpy.data.materials['V15 city glass neutral'];metal=bpy.data.materials['V15 anodised city aluminium'];light=bpy.data.materials['V15 architectural white']
    mats=[bpy.data.materials[n] for n in ['V15 dark office','V15 occupied amber offices','V15 occupied white offices','V15 shaded office blinds']]
    rng=random.Random(327);rows=[];floors=24;segments=72
    def point(a,z,out=0):
        t=z/height;scale=1-.16*t;shift=.80*math.sin(math.pi*t)
        return (x+shift+(rx*scale+out)*math.cos(a),cy+(ry*scale+out)*math.sin(a),z)
    for floor in range(floors+1):rows.append([point(2*math.pi*k/segments,4+floor*(height-4)/floors) for k in range(segments+1)])
    h.patch('V15 oval hotel curved glass',rows,glass,parent)
    batches=[([],[]) for _ in mats]
    for floor in range(floors):
        z0=4.35+floor*(height-4)/floors;z1=z0+2.05
        for k in range(48):
            a0=2*math.pi*(k+.10)/48;a1=2*math.pi*(k+.90)/48;bucket=rng.choices(range(4),[.47,.27,.16,.10])[0];verts,faces=batches[bucket];n=len(verts)
            verts.extend([point(a0,z0,.025),point(a1,z0,.025),point(a1,z1,.025),point(a0,z1,.025)]);faces.append((n,n+1,n+2,n+3))
        ring=[point(2*math.pi*k/segments,z0-.15,.06) for k in range(segments)]
        h.curve('V15 oval hotel continuous floor edge',ring,.034,metal,parent,True)
        if floor in [0,5,11,17,23]:h.curve('V15 oval hotel illuminated ring',[point(2*math.pi*k/segments,z0-.12,.083) for k in range(segments)],.012,light,parent,True)
    for mat,(verts,faces) in zip(mats,batches):h.mesh('V15 oval hotel fitted windows',verts,faces,mat,parent,False)
    for k in range(24):
        a=2*math.pi*k/24;h.curve('V15 oval hotel curved mullion',[point(a,z,.063) for z in [4+i*72/48 for i in range(49)]],.025,metal,parent)
    # The curved ground floor has real glazed space between its columns.
    clear=bpy.data.materials['V15 retail clear glass'];warm=bpy.data.materials['V15 retail warm lighting']
    for k in range(24):
        a0=2*math.pi*k/24;a1=2*math.pi*(k+1)/24
        h.patch('V15 oval hotel lobby glazing',[[point(a,zz,.01) for a in [a0,a1]] for zz in [.15,3.65]],clear,parent,False,.014)
        px,py,_=point(a0,0);h.cylinder('V15 oval hotel lobby column',(px,py,0),(px,py,3.9),.085,metal,parent,16)
    h.cylinder('V15 oval hotel lobby ceiling',(x,cy,3.8),(x,cy,4.0),8.2,metal,parent,72)
    h.cylinder('V15 oval hotel lobby warm ceiling',(x,cy,3.72),(x,cy,3.75),7.1,warm,parent,64)
    h.text('V15 oval hotel understated name','HOTEL',(x,2.02,4.30),.42,light,parent)
    for xx in [x-3.0,x+3.0]:h.ellipsoid('V15 hotel lobby chair',(xx,5.0,.48),(.55,.48,.30),bpy.data.materials['V15 retail objects ochre'],parent)

def terraced_brick(parent):
    x=-29;front=-16.2;brick=h.material('V15 quiet district terracotta',(.105,.052,.033),.73)
    if not brick.node_tree.nodes.get('V15 masonry'):
        nt=brick.node_tree;n=nt.nodes.new('ShaderNodeTexBrick');n.name='V15 masonry';n.inputs['Color1'].default_value=(.12,.062,.040,1);n.inputs['Color2'].default_value=(.060,.035,.026,1);n.inputs['Mortar'].default_value=(.018,.020,.022,1);n.inputs['Scale'].default_value=3.5;n.inputs['Mortar Size'].default_value=.008
        coord=nt.nodes.new('ShaderNodeTexCoord');nt.links.new(coord.outputs['Object'],n.inputs['Vector']);n.inputs['Scale'].default_value=2.5
        nt.links.new(n.outputs['Color'],nt.nodes['Principled BSDF'].inputs['Base Color'])
    metal=bpy.data.materials['V15 anodised city aluminium'];warm=bpy.data.materials['V15 occupied amber offices'];dark=bpy.data.materials['V15 dark office'];clear=bpy.data.materials['V15 retail clear glass'];leaf=bpy.data.materials['V15 evergreen foliage']
    h.box('V15 terraced foundation',(x,-22.2,.04),(18.9,12,.08),brick,parent,.03)
    h.box('V15 terraced restaurant ceiling',(x,-22.2,3.8),(18.9,12,.25),brick,parent,.05)
    for xx in [x-9.35,x-3.1,x+3.1,x+9.35]:h.box('V15 terraced restaurant pier',(xx,front-.15,1.9),(.32,.50,3.8),brick,parent,.028)
    for b in range(3):
        xx=x+(b-1)*6.2
        h.box('V15 restaurant glazing',(xx,front+.015,1.92),(5.80,.015,3.55),clear,parent,.005)
        h.box('V15 restaurant interior',(xx,front-3.3,1.85),(5.95,.12,3.45),bpy.data.materials['V15 warm retail interior'],parent,.02)
        for j in range(3):
            cx=xx+(j-1)*1.6;h.cylinder('V15 restaurant table pedestal',(cx,front-1.4,.1),(cx,front-1.4,.77),.045,metal,parent,12);h.cylinder('V15 restaurant table',(cx,front-1.4,.77),(cx,front-1.4,.82),.42,brick,parent,36)
        h.box('V15 restaurant ceiling light',(xx,front-1.5,3.5),(4.9,.6,.04),bpy.data.materials['V15 retail warm lighting'],parent,.012)
    h.text('V15 quiet restaurant sign','CAFE  /  DINING',(x,front+.05,3.13),.36,bpy.data.materials['V15 architectural white'],parent,rot=(math.pi/2,0,math.pi))
    for floor in range(6):
        setback=max(0,floor-2)*1.10;w=18.9-2*max(0,floor-2)*1.5;z0=3.95+floor*3.15;face=front-setback
        h.box('V15 terraced masonry level',(x,face-5,z0+1.56),(w,10,3.12),brick,parent,.075)
        for k in range(5):
            xx=x+(k-2)*w/5.6
            h.box('V15 terraced window surround',(xx,face+.065,z0+1.60),(w/6.9,.15,1.86),metal,parent,.035)
            h.box('V15 terraced window',(xx,face+.146,z0+1.60),(w/7.8,.008,1.63),warm if (k+floor)%3 else dark,parent,.005)
        h.box('V15 terraced balcony slab',(x,face+.50,z0+.05),(w+.12,1.25,.13),metal,parent,.04)
        h.cylinder('V15 terraced handrail',(x-w/2,face+1.02,z0+.92),(x+w/2,face+1.02,z0+.92),.024,metal,parent,12)
        for k in range(14):h.cylinder('V15 terraced baluster',(x-w/2+k*w/13,face+1.02,z0+.13),(x-w/2+k*w/13,face+1.02,z0+.92),.012,metal,parent,8)
        if floor>=3:
            for xx in [x-w*.34,x+w*.34]:
                h.box('V15 terrace planter',(xx,face+.40,z0+.25),(1.4,.60,.50),metal,parent,.055)
                for j in [-.40,0,.40]:h.ellipsoid('V15 terrace shrubs',(xx+j,face+.40,z0+.62),(.32,.30,.30),leaf,parent)

def wedge_tower(parent):
    x=28;front=2.15;w=19.0;depth=14.0;bottom=4.5;top=78
    metal=bpy.data.materials['V15 anodised city aluminium'];glass=bpy.data.materials['V15 city glass blue'];light=bpy.data.materials['V15 architectural cyan'];warm=bpy.data.materials['V15 occupied amber offices'];cool=bpy.data.materials['V15 occupied white offices']
    def point(u,t,back=False):return (x+4*t+u*w*.5*(1-.18*t),front+2.4*t+(depth*(1-.25*t) if back else 0),bottom+(top-bottom)*t+u*6*t)
    verts=[point(u,t,back) for t in [0,1] for back in [False,True] for u in [-1,1]]
    faces=[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]
    body=h.mesh('V15 sloping glass blade',verts,faces,glass,parent,False);v.normalise_mesh(body)
    vs=[];fs=[];mats=[]
    for row in range(22):
        t0=(row+.14)/22;t1=(row+.83)/22
        for col in range(9):
            u0=-1+2*(col+.10)/9;u1=-1+2*(col+.90)/9;n=len(vs)
            pts=[point(u,t) for u,t in [(u0,t0),(u1,t0),(u1,t1),(u0,t1)]];vs.extend([(xx,yy-.025,zz) for xx,yy,zz in pts]);fs.append((n,n+1,n+2,n+3));mats.append((row+col)%4==0)
    windows=h.mesh('V15 sloping blade office grid',vs,fs,warm,parent,False);windows.data.materials.append(cool)
    for face,index in zip(windows.data.polygons,mats):face.material_index=int(index)
    for u in [-1,0,1]:h.curve('V15 sloping blade vertical edge',[(xx,yy-.06,zz) for xx,yy,zz in [point(u,t) for t in [i/40 for i in range(41)]]],.060,metal,parent)
    for t0,t1 in [(0,.33),(.33,.66),(.66,1)]:
        for sign in [-1,1]:
            a=Vector(point(sign,t0));b=Vector(point(-sign,t1));a.y-=.08;b.y-=.08;h.cylinder('V15 sloping blade diagonal structure',a,b,.105,metal,parent,12)
    h.curve('V15 sloping blade crown glow',[(xx,yy-.09,zz+.015) for xx,yy,zz in [point(-1+2*i/40,1) for i in range(41)]],.023,light,parent)
    for xx in [x-7,x+7]:h.cylinder('V15 blade atrium column',(xx,front+1,0),(xx,front+1,bottom),.16,metal,parent,20)
    h.box('V15 blade atrium ceiling',(x,front+6,4.37),(20,13,.22),metal,parent,.055)
    h.box('V15 blade atrium light',(x,front+3,4.22),(16,4,.045),bpy.data.materials['V15 retail warm lighting'],parent,.025)
    h.text('V15 blade building directory','DESIGN  /  STUDIO',(x,front-.08,3.5),.41,bpy.data.materials['V15 architectural white'],parent)

def intersection(tile,parent):
    road=bpy.data.materials['V15 rain-dark asphalt'];stone=bpy.data.materials['V15 granite pedestrian paving'];white=bpy.data.materials['V15 wet reflective lane paint'];yellow=bpy.data.materials['V15 amber road paint'];metal=bpy.data.materials['V15 anodised city aluminium']
    split_names=['V15 avenue granite kerb','V15 pedestrian pavement','V15 avenue centre line','V15 avenue edge line']
    for o in list(tile.objects):
        if any(o.name.startswith(name) for name in split_names):
            o.hide_render=True
            for a,b in [(-128,-21.9),(-6.1,128)]:
                dims=o.dimensions.copy();dims.x=b-a;loc=o.location.copy();loc.x=(a+b)/2
                h.box('V15 intersection split '+o.name,loc,dims,o.data.materials[0],parent,.005 if 'pavement' in o.name else 0)
        if o.name.startswith('V15 pavement joint') and -22<o.location.x<-6:o.hide_render=True
        if o.name.startswith('V15 skyline ') and -26<o.location.x<-2:o.location.x+=18
    # The north and south branches are genuine roads with their own kerbs,
    # lane markings and sightlines; the main carriageway is already present.
    for a,b in [(-60,-13.775),(-.775,60)]:
        mid=(a+b)/2;length=b-a
        h.box('V15 transverse street',(-14,mid,-.16),(10,length,.12),road,parent,0)
        h.box('V15 transverse centre line',(-14,mid,-.098),(.10,length,.002),yellow,parent,0)
        for xx in [-19.13,-8.87]:h.box('V15 transverse granite kerb',(xx,mid,-.037),(.23,length,.18),stone,parent,.015)
        for xx in [-20.12,-7.88]:h.box('V15 transverse pavement',(xx,mid,-.05),(1.75,length,.10),stone,parent,.005)
    for yy in [-15.4,.85]:
        for k in range(9):h.box('V15 transverse zebra',(-18.3+k*1.05,yy,-.096),(.53,2.55,.004),white,parent,0)
    for yy in [-17.2,2.65]:h.box('V15 transverse stop bar',(-14,yy,-.096),(9.6,.22,.004),white,parent,0)
    # Waiting cross-street traffic stays behind the red phase.
    template=bpy.data.collections.get('V15_TRAFFIC_REFINED_pearl')
    if template:
        car=h.obj('V15 intersection waiting car',None,parent);car.instance_type='COLLECTION';car.instance_collection=template;car.location=(-11.55,6.7,-.10)
        car=h.obj('V15 intersection second waiting car',None,parent);car.instance_type='COLLECTION';car.instance_collection=bpy.data.collections['V15_TRAFFIC_REFINED_graphite'];car.location=(-11.55,13.5,-.10)
    red=bpy.data.materials['V15 city red light']
    for xx,yy in [(-19.75,3.2),(-8.25,-17.8)]:
        h.cylinder('V15 transverse signal mast',(xx,yy,0),(xx,yy,4.8),.065,metal,parent,16)
        h.box('V15 transverse red signal',(xx,yy,4.5),(.26,.18,.65),metal,parent,.04)
        h.ellipsoid('V15 transverse red lens',(xx,yy+(.11 if yy>0 else -.11),4.7),(.073,.018,.073),red,parent)

def additional_ads(tile,parent):
    image=bpy.data.images.load(str(ROOT/'assets/textures/v15/urban-advertising-atlas-2.png'),check_existing=True);image.pack();new=[]
    for i in range(4):
        mat=h.material('V15 additional campaign '+str(i),(.20,.20,.20),.32)
        nt=mat.node_tree
        if not nt.nodes.get('V15 second atlas'):
            tex=nt.nodes.new('ShaderNodeTexImage');tex.name='V15 second atlas';tex.image=image;p=nt.nodes['Principled BSDF'];nt.links.new(tex.outputs['Color'],p.inputs['Base Color']);nt.links.new(tex.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=1.7
        new.append(mat)
    # Large billboards are deliberately absent on roughly half the blocks.
    screens=sorted([o for o in tile.objects if 'campaign screen' in o.name and not o.hide_render],key=lambda o:o.name)
    for k,o in enumerate(screens):
        prefix=o.name.split(' campaign')[0]
        if k%3==1:
            for part in tile.objects:
                if part.name.startswith(prefix) and ('campaign' in part.name or 'advertising spill' in part.name):part.hide_render=True
            continue
        if k%2==0:
            old=int(o.data.materials[0].name.rsplit(' ',1)[1]);index=(k//2)%4;o.data.materials[0]=new[index]
            old_u=.5*(old%2);old_v=.5 if old<2 else 0;new_u=.5*(index%2);new_v=.5 if index<2 else 0
            for uv in o.data.uv_layers.active.data:uv.uv.x+=new_u-old_u;uv.uv.y+=new_v-old_v
    # Small-format street advertising adds a different size and rhythm.
    metal=bpy.data.materials['V15 anodised city aluminium']
    for x,index in [(-35,0),(45,2),(92,1)]:
        y=-14.92
        h.box('V15 bus shelter roof',(x,y,2.75),(4.9,1.1,.12),metal,parent,.055)
        for xx in [x-2.2,x+2.2]:h.cylinder('V15 bus shelter support',(xx,y,0),(xx,y,2.7),.045,metal,parent,12)
        c.billboard('V15 shelter advertising',x+1.35,y,1.47,1.40,2.18,index,new[index],metal,parent,1)
        h.box('V15 bus shelter bench',(x-.65,y,.43),(2.25,.42,.08),metal,parent,.04)

def run():
    tile=bpy.data.collections['V15_CITY_256M_MODULE'];h.COL=tile;v.remove_root('V15_CITY_VARIATION');parent=h.obj('V15_CITY_VARIATION',None)
    for prefix in ['V15 block 3.N','V15 block 3.S','V15 block 5.N']:disable_prefix(tile,prefix)
    rounded_hotel(parent);terraced_brick(parent);wedge_tower(parent);intersection(tile,parent);additional_ads(tile,parent)
    for o in parent.children_recursive:
        if o.type=='LIGHT':o.visible_camera=False;o.visible_transmission=False
    bpy.context.scene['V15_city_variety']='Oval ad-free hotel, terraced brick midrise, sloping glass blade, fewer billboards, eight photographic campaigns and a transverse street intersection.'
    print('V15_CITY_DIVERSITY_READY',len(parent.children_recursive),flush=True)

def freeze_waiting_traffic():
    name='V15_TRAFFIC_WAITING_STATIC';col=bpy.data.collections.get(name)
    if not col:
        col=bpy.data.collections.new(name);scene=bpy.context.scene;frame=scene.frame_current;scene.frame_set(0)
        for source in bpy.data.collections['V15_TRAFFIC_REFINED_pearl'].objects:
            if source.type not in {'MESH','CURVE','FONT'}:continue
            clone=source.copy();clone.data=source.data;col.objects.link(clone);clone.parent=None;clone.matrix_world=source.matrix_world.copy();clone.animation_data_clear()
        scene.frame_set(frame)
    for o in bpy.data.collections['V15_CITY_256M_MODULE'].objects:
        if o.name in ['V15 intersection waiting car','V15 intersection second waiting car']:o.instance_collection=col
    print('V15_WAITING_TRAFFIC_STATIC',flush=True)

def fix_frontage():
    tile=bpy.data.collections['V15_CITY_256M_MODULE']
    if tile.get('V15_frontage_fixed'):return
    h.COL=tile;parent=h.obj('V15_FRONTAGE_CONNECTION',None);stone=bpy.data.materials['V15 granite pedestrian paving']
    # Keep city pavement outside the original shop/forecourt footprint.
    for o in list(tile.objects):
        if o.hide_render:continue
        if ('pedestrian pavement' in o.name or 'avenue granite kerb' in o.name) and o.location.y>-5:o.hide_render=True
        if o.name.startswith('V15 pavement joint') and o.location.y>-5:o.hide_render=True
        if o.name=='V15 avenue asphalt':o.dimensions.y=11.775;o.location.y=-7.8875
        if 'avenue edge line' in o.name and o.location.y>-5:o.location.y=-2.30
        if o.name.startswith(('V15 transverse street','V15 transverse granite kerb','V15 transverse pavement')) and o.location.y>0:o.dimensions.y=62.0;o.location.y=29.0
    for a,b in [(-128,-21.9),(-6.1,-2.9),(12.6,128)]:
        h.box('V15 frontage connected city kerb',((a+b)/2,-1.90,-.037),(b-a,.23,.18),stone,parent,.012)
        h.box('V15 frontage connected city pavement',((a+b)/2,.1825,-.05),(b-a,3.935,.10),stone,parent,.005)
    # The nearer strip is a forecourt/shoulder, not a through traffic lane.
    for index in [0,1,2]:
        car=bpy.data.objects['V15 traffic vehicle '+str(index)];car.location.y=-5.90
    follower=bpy.data.objects['V15 traffic vehicle 1'];follower.animation_data.drivers.find('location',index=0).driver.expression='((-93+(256/48)*frame/30+128)%256)-128'
    tile['V15_frontage_fixed']=True
    tile['V15_frontage_scope']='Original forecourt X -2.9..12.6 preserved; through cars remain south of its kerb.'
    print('V15_FRONTAGE_CONNECTED',flush=True)
