"""A 256 m night-city module with a separate arrival scene and loop scene."""
import bpy,math,random,importlib.util,json
from pathlib import Path
from mathutils import Vector,Matrix
from math import sin,cos,pi
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v15',ROOT/'tools/refine_v15.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);h=v.h
P=256.0

def area(name,pos,target,power,size,size_y,color,parent=None):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='RECTANGLE';d.size=size;d.size_y=size_y;d.color=color
    o=h.obj(name,d,parent);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o

def emission(name,color,strength):
    return h.material(name,color,.35,0,0,strength)

def wet_road():
    m=h.material('V15 rain-dark asphalt',(.018,.021,.027),.22,.04)
    nt=m.node_tree;n=nt.nodes;p=n['Principled BSDF']
    if n.get('256m periodic world coordinates'):return m
    geometry=n.new('ShaderNodeNewGeometry');sep=n.new('ShaderNodeSeparateXYZ');nt.links.new(geometry.outputs['Position'],sep.inputs[0])
    phase=n.new('ShaderNodeMath');phase.operation='MULTIPLY';phase.inputs[1].default_value=2*pi/P;nt.links.new(sep.outputs['X'],phase.inputs[0])
    trig=[]
    for operation in ['COSINE','SINE']:
        f=n.new('ShaderNodeMath');f.operation=operation;nt.links.new(phase.outputs[0],f.inputs[0]);scale=n.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=P/(2*pi);nt.links.new(f.outputs[0],scale.inputs[0]);trig.append(scale)
    coord=n.new('ShaderNodeCombineXYZ');coord.name='256m periodic world coordinates'
    nt.links.new(trig[0].outputs[0],coord.inputs['X']);nt.links.new(trig[1].outputs[0],coord.inputs['Y']);nt.links.new(sep.outputs['Y'],coord.inputs['Z'])
    puddle=n.new('ShaderNodeTexNoise');puddle.inputs['Scale'].default_value=.25;puddle.inputs['Detail'].default_value=3;puddle.inputs['Roughness'].default_value=.62;nt.links.new(coord.outputs[0],puddle.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.32;ramp.color_ramp.elements[0].color=(.12,.12,.12,1);ramp.color_ramp.elements[1].position=.68;ramp.color_ramp.elements[1].color=(.30,.30,.30,1);nt.links.new(puddle.outputs['Fac'],ramp.inputs[0]);nt.links.new(ramp.outputs[0],p.inputs['Roughness'])
    colour=n.new('ShaderNodeValToRGB');colour.color_ramp.elements[0].color=(.009,.012,.016,1);colour.color_ramp.elements[1].color=(.038,.043,.048,1);nt.links.new(puddle.outputs['Fac'],colour.inputs[0]);nt.links.new(colour.outputs[0],p.inputs['Base Color'])
    grain=n.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=180;grain.inputs['Detail'].default_value=2;nt.links.new(coord.outputs[0],grain.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.25;bump.inputs['Distance'].default_value=.00035;nt.links.new(grain.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    p.inputs['Coat Weight'].default_value=.26;p.inputs['Coat Roughness'].default_value=.08
    return m

def billboard_materials():
    image=bpy.data.images.load(str(ROOT/'assets/textures/v15/urban-advertising-atlas.png'),check_existing=True);image.pack()
    mats=[]
    for i in range(4):
        mat=h.material('V15 digital advertising '+str(i),(.2,.2,.2),.28)
        nt=mat.node_tree
        if not nt.nodes.get('V15 original campaign atlas'):
            tex=nt.nodes.new('ShaderNodeTexImage');tex.name='V15 original campaign atlas';tex.image=image;tex.interpolation='Linear'
            shader=nt.nodes['Principled BSDF'];nt.links.new(tex.outputs['Color'],shader.inputs['Base Color']);nt.links.new(tex.outputs['Color'],shader.inputs['Emission Color']);shader.inputs['Emission Strength'].default_value=2.2
        mats.append(mat)
    return mats

def billboard(name,x,y,z,w,ht,index,mat,frame,parent,facing):
    h.box(name+' housing',(x,y,z),(w+.18,.18,ht+.18),frame,parent,.055)
    yy=y+facing*.105
    # Crop the square quadrant instead of distorting the artwork.
    u0=.5*(index%2);v0=.5 if index<2 else 0;uw=vh=.5
    if w>ht:vh=.5*ht/w;v0+=(.5-vh)/2
    else:uw=.5*w/ht;u0+=(.5-uw)/2
    rows=[[(x-w/2,yy,z-ht/2),(x+w/2,yy,z-ht/2)],[(x-w/2,yy,z+ht/2),(x+w/2,yy,z+ht/2)]]
    h.patch(name+' screen',rows,mat,parent,facing>0,uvrect=(u0,v0,uw,vh))

def tree(name,x,y,parent,m,rng):
    trunk=m['trunk'];leaf=m['leaf'];h.cylinder(name+' trunk',(x,y,.04),(x,y,2.55),.09,trunk,parent,12)
    # Branches and clustered leaf cards are batched into one foliage mesh.
    verts=[];faces=[]
    for b in range(7):
        a=2*pi*b/7;end=(x+.65*cos(a),y+.65*sin(a),2.6+rng.uniform(-.3,.4));h.cylinder(name+' branch',(x,y,1.7),end,.035,trunk,parent,8)
    for j in range(190):
        a=rng.random()*2*pi;rr=rng.random()**.5*1.2;zz=rng.uniform(2.3,4.0)
        cx=x+rr*cos(a);cy=y+rr*sin(a);size=rng.uniform(.10,.23);ang=rng.random()*pi
        for tilt in [0,pi/2]:
            dx=size*cos(ang+tilt);dy=size*sin(ang+tilt);n=len(verts)
            verts.extend([(cx-dx,cy-dy,zz-.04),(cx+dx,cy+dy,zz-.04),(cx+dx*.7,cy+dy*.7,zz+.13),(cx-dx*.7,cy-dy*.7,zz+.13)]);faces.append((n,n+1,n+2,n+3))
    h.mesh(name+' foliage',verts,faces,leaf,parent,False)
    h.box(name+' tree grate',(x,y,.005),(1.15,1.15,.025),m['metal'],parent,.035)
    for j in range(7):h.box(name+' grate slots',(x-.45+j*.15,y,.022),(.035,.95,.008),m['black'],parent,.002)

def tower(name,x,front,w,depth,height,style,parent,m,ads,rng,facing):
    centre_y=front-facing*depth/2
    podium=5.3+rng.choice([0,.6,1.2]);glass=m['glass'+str(style%3)]
    h.box(name+' retail foundation',(x,centre_y,.05),(w,depth,.10),m['stone'],parent,.03)
    h.box(name+' retail roof slab',(x,centre_y,podium-.25),(w,depth,.50),m['stone'],parent,.06)
    # Chamfered/curved upper tower footprint, with several silhouette families.
    sides=48 if style in [1,4] else 12;rows=[];levels=max(12,int((height-podium)/3.15))
    for j in range(levels+1):
        t=j/levels;z=podium+(height-podium)*t
        taper=1-.15*t if style==1 else 1-.10*max(0,(t-.70)/.30)
        shift=.07*w*sin(pi*t) if style==4 else 0
        row=[]
        for k in range(sides+1):
            a=2*pi*k/sides
            if style in [1,4]:xx=cos(a)*w*.47*taper;yy=sin(a)*depth*.47*taper
            else:
                # Superellipse offers a rounded rectangular plan.
                xx=math.copysign(abs(cos(a))**.32,cos(a))*w*.47*taper;yy=math.copysign(abs(sin(a))**.32,sin(a))*depth*.47*taper
            row.append((x+xx+shift,centre_y+yy,z))
        rows.append(row)
    h.patch(name+' curtain wall',rows,glass,parent,True)
    # Floor edges provide real depth; four facade families vary in both rhythm
    # and light occupancy. Lit windows are single batches by material.
    batches=[([],[]) for _ in range(4)]
    cols=max(4,int(w/1.15))
    for floor in range(levels):
        z=podium+1.20+floor*(height-podium)/levels
        # Main street facade remains planar at close range, on a podium setback.
        setback=.25+(.12*w*floor/levels if style==1 else .08*w*max(0,(floor/levels-.7)/.3))
        yf=front-facing*.16
        facade_w=w-1.3-2*setback
        for col in range(cols):
            xx=x-facade_w/2+(col+.5)*facade_w/cols
            bucket=rng.choices(range(4),[.50,.25,.17,.08])[0];verts,faces=batches[bucket]
            ww=facade_w/cols*.79;hh=1.75 if style%2 else 2.05;n=len(verts)
            verts.extend([(xx-ww/2,yf,z-hh/2),(xx+ww/2,yf,z-hh/2),(xx+ww/2,yf,z+hh/2),(xx-ww/2,yf,z+hh/2)]);faces.append((n,n+1,n+2,n+3))
        if floor%2==0 or style==2:h.box(name+' floor shadow band',(x,yf+facing*.05,z-1.22),(facade_w+.25,.18,.11),m['metal'],parent,.014)
        if floor%5==0 and style in [1,4]:
            index=min(floor,len(rows)-1);h.curve(name+' luminous curved floor',[(xx,yy,zz+.05) for xx,yy,zz in rows[index]],.018,m['white_strip'],parent,True)
    for i,(verts,faces) in enumerate(batches):
        if verts:h.mesh(name+' office windows '+str(i),verts,faces,[m['dark_window'],m['warm_window'],m['cool_window'],m['blinds']][i],parent,False)
    for col in range(0,cols+1,2):
        xx=x-(w-1.6)/2+col*(w-1.6)/cols
        h.box(name+' vertical mullion',(xx,front-facing*.12,podium+(height-podium)*.46),(.075,.22,(height-podium)*.92),m['metal'],parent,.009)
    if style in [0,3]:
        for sign in [-1,1]:
            h.box(name+' architectural light',(x+sign*w*.448,front-facing*.60,podium+(height-podium)*.47),(.026,.05,(height-podium)*.90),m['cyan_strip'],parent,.008)
    h.box(name+' crown',(x,centre_y,height+.12),(w*.89,depth*.89,.24),m['metal'],parent,.07)
    if style==4:
        h.cylinder(name+' antenna',(x,centre_y,height),(x,centre_y,height+6),.055,m['metal'],parent,12)
        h.ellipsoid(name+' aviation lamp',(x,centre_y,height+6),(.08,.08,.08),m['red'],parent)
    # Ground-floor rooms: actual setback, floor, shelves, shop glazing and signs.
    bays=max(2,int(w/4.0));bay_width=(w-.70)/bays
    for b in range(bays):
        xx=x-w/2+.35+(b+.5)*bay_width;room_front=front+facing*.045
        h.box(name+' shop interior back',(xx,front-facing*1.8,1.85),(bay_width-.20,.10,3.50),m['warm_wall'],parent,.01)
        h.box(name+' shop interior floor',(xx,front-facing*.8,.11),(bay_width-.22,2.0,.10),m['retail_floor'],parent,.01)
        for shelf in range(3):
            h.box(name+' shop display shelf',(xx,front-facing*1.43,.7+shelf*.65),(bay_width-.60,.38,.055),m['metal'],parent,.007)
            for product in range(4):h.box(name+' shop merchandise',(xx-bay_width*.30+product*bay_width*.20,front-facing*1.43,.88+shelf*.65),(.22,.17,.29),m['merch'+str((product+b)%3)],parent,.025)
        h.box(name+' shop glass',(xx,room_front,1.92),(bay_width-.22,.010,3.50),m['retail_glass'],parent,.006)
        h.box(name+' shop jamb',(xx-bay_width/2,room_front,2.0),(.08,.12,4.0),m['metal'],parent,.008)
        h.box(name+' shop soffit light',(xx,front-facing*.70,3.80),(bay_width-.55,1.35,.035),m['warm_strip'],parent,.012)
        word=['CAFE','STUDIO','GALLERY','24H','HOTEL'][(b+style)%5]
        text=h.text(name+' shop sign',word,(xx,front+facing*.08,4.20),.33,m['white_strip'],parent,rot=(pi/2,0,pi if facing>0 else 0))
    h.box(name+' retail canopy',(x,front+facing*.28,4.98),(w+.25,1.0,.15),m['metal'],parent,.04)
    # One strong advertising plane per selected block; photography carries a
    # different type of detail from the structural facade.
    if style!=2:
        index=(style+(2 if facing<0 else 0))%4;bw=min(w-1.8,10.5);bh=7.5 if style%2 else 9.0
        billboard(name+' campaign',x,front+facing*.22,9.7,bw,bh,index,ads[index],m['metal'],parent,facing)
        area(name+' advertising spill',(x,front+facing*.47,8.5),(x,front+facing*6,.05),180,5,4,[(.30,.50,1),(.35,.66,1),(1,.54,.24),(.20,.65,1)][index],parent)

def traffic_template(name,tag):
    old=bpy.data.collections.get(name)
    if old:return old
    col=bpy.data.collections.new(name);source=bpy.data.objects[tag+'.V15_BODY']
    for obj in source.children_recursive:
        clone=obj.copy();clone.data=obj.data;col.objects.link(clone);clone.parent=None;clone.matrix_world=obj.matrix_local.copy();clone.hide_render=False;clone.hide_set(False)
    return col

def make_city():
    scene=bpy.context.scene
    for o in list(bpy.data.objects):
        if o.name.startswith('V15 City tile instance '):bpy.data.objects.remove(o,do_unlink=True)
    existing=bpy.data.collections.get('V15_CITY_256M_MODULE')
    if existing:
        for o in list(existing.objects):bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.collections.remove(existing)
    # Preserve all previous city geometry in the file, hidden for comparison.
    for o in bpy.data.objects:
        if o.name.startswith(('CITY.','V14 City','V14 Tower','V14 Distant','V14 Facade','V14 Floor slab','V14 Light reveal','V14 Ground retail','V14 Retail canopy','V14 Recessed','V14 Curb','V14 Bollard','V14 Linear planter','V14 Grasses','V14 Avenue light')) or o.name=='EXT.Site.RoadBase':o.hide_render=True;o.hide_set(True)
    for cname in ['V14 / Distant skyline','V14 / Street foreground']:
        col=bpy.data.collections.get(cname)
        if col:
            for o in col.objects:o.hide_render=True;o.hide_set(True)
    tile=bpy.data.collections.new('V15_CITY_256M_MODULE');h.COL=tile;parent=None
    m={
        'stone':h.material('V15 charcoal limestone',(.055,.061,.068),.66),
        'metal':h.material('V15 anodised city aluminium',(.028,.035,.043),.31,.65),
        'black':h.material('V15 city recess',(.006,.009,.014),.55),
        'glass0':h.material('V15 city glass blue',(.020,.037,.056),.20,.47,.25),
        'glass1':h.material('V15 city glass neutral',(.036,.045,.051),.24,.53,.25),
        'glass2':h.material('V15 city glass bronze',(.060,.044,.030),.24,.53,.25),
        'dark_window':h.material('V15 dark office',(.011,.019,.025),.25,.30),
        'warm_window':emission('V15 occupied amber offices',(.48,.31,.16),1.5),
        'cool_window':emission('V15 occupied white offices',(.33,.43,.53),1.1),
        'blinds':emission('V15 shaded office blinds',(.22,.20,.15),.65),
        'cyan_strip':emission('V15 architectural cyan',(.10,.38,.54),3.0),
        'white_strip':emission('V15 architectural white',(.52,.66,.77),2.8),
        'warm_strip':emission('V15 retail warm lighting',(.65,.39,.18),3.5),
        'red':emission('V15 city red light',(.5,.002,.003),3),
        'warm_wall':emission('V15 warm retail interior',(.29,.17,.085),.55),
        'retail_floor':h.material('V15 retail floor',(.18,.14,.10),.45),
        'retail_glass':h.material('V15 retail clear glass',(.95,.98,1),.045,0,0,0,1),
        'merch0':h.material('V15 retail objects ivory',(.47,.44,.36),.48),
        'merch1':h.material('V15 retail objects ochre',(.24,.13,.04),.48),
        'merch2':h.material('V15 retail objects dark',(.02,.025,.031),.48),
        'trunk':h.material('V15 street tree bark',(.075,.051,.032),.85),
        'leaf':h.material('V15 evergreen foliage',(.025,.065,.038),.75),
    }
    ads=billboard_materials();road=wet_road();paving=h.material('V15 granite pedestrian paving',(.11,.12,.14),.47)
    white=h.material('V15 wet reflective lane paint',(.43,.46,.47),.27);yellow=h.material('V15 amber road paint',(.50,.27,.06),.28)
    h.box('V15 avenue asphalt',(0,-7.275,-.16),(256,13,.12),road,parent,0)
    for y in [-.66,-13.89]:
        h.box('V15 avenue granite kerb',(0,y,-.037),(256,.23,.18),paving,parent,.015)
        py=y+(1 if y> -5 else -1)*1.15
        h.box('V15 pedestrian pavement',(0,py,-.05),(256,2.05,.10),paving,parent,.005)
        for x in range(-128,128,2):h.box('V15 pavement joint',(x,py,.002),(.005,2.04,.003),m['black'],parent,0)
    for y in [-4.025,-10.525]:
        for k in range(40):
            x=-126.4+k*6.4
            if -21<x<-7:continue
            h.box('V15 broken lane marking',(x,y,-.098),(2.7,.105,.002),white,parent,0)
    for y in [-7.23,-7.32]:h.box('V15 avenue centre line',(0,y,-.098),(256,.075,.002),yellow,parent,0)
    for y in [-1.03,-13.52]:h.box('V15 avenue edge line',(0,y,-.098),(256,.12,.002),white,parent,0)
    # A recognisable crossing before the shop, with a high pedestrian bridge.
    for xx in [-20.5,-7.5]:
        for k in range(12):h.box('V15 zebra crossing',(xx,-13.1+k*1.0,-.096),(2.6,.50,.004),white,parent,0)
    for x in [-112,-80,-48,-16,16,48,80,112]:
        for y,facing in [(.45,-1),(-15.0,1)]:
            if y>.0 and -8<x<19:continue
            h.cylinder('V15 avenue lamp mast',(x,y,0),(x,y,7.2),.080,m['metal'],parent,16)
            arm=[(x,y,6.9),(x,y+facing*.20,7.4),(x,y+facing*1.8,7.4)]
            v.path('V15 avenue lamp arm',arm,.055,m['metal'],parent)
            h.box('V15 avenue luminaire',(x,y+facing*1.8,7.34),(.75,.32,.12),m['metal'],parent,.04)
            h.box('V15 avenue LED lens',(x,y+facing*1.8,7.265),(.59,.23,.028),m['white_strip'],parent,.012)
            area('V15 avenue pool of light',(x,y+facing*1.8,7.24),(x,y+facing*3,-.1),175,1.1,.50,(.68,.77,1),parent)
    rng=random.Random(1515)
    for i,x in enumerate([-112,-84,-56,-29,0,28,56,84,112]):
        for north in [False,True]:
            if north and x==0:continue
            front=2.15 if north else -16.20;facing=-1 if north else 1
            width=rng.uniform(17.5,23.0);depth=rng.uniform(10,16);height=rng.choice([28,36,45,58,72,86]);style=(i+(2 if north else 0))%5
            tower('V15 block '+str(i)+('.N' if north else '.S'),x,front,width,depth,height,style,parent,m,ads,rng,facing)
    # Far silhouettes repeat with the same full module, preventing a skyline jump.
    for k in range(18):
        x=-120+k*14+rng.uniform(-3,3);y=rng.choice([-1,1])*rng.uniform(35,60);ht=rng.uniform(55,118);w=rng.uniform(7,12)
        h.box('V15 skyline tower',(x,y,ht/2),(w,w*.85,ht),m['glass'+str(k%3)],parent,.40)
        for floor in range(6,int(ht/3.3)):
            if rng.random()<.26:continue
            h.box('V15 skyline occupied floor',(x,y+(w*.43 if y<0 else -w*.43),floor*3.3),(w*.85,.022,.10),m['warm_window'] if k%3 else m['cool_window'],parent,.008)
    # Elevated walkway: thin structure, glazed sides, real columns and soffit.
    bridge_x=-14.0;bridge_y=-7.3
    h.box('V15 elevated walkway deck',(bridge_x,bridge_y,6.10),(4.0,26,.42),m['metal'],parent,.11)
    h.box('V15 elevated walkway ceiling',(bridge_x,bridge_y,8.18),(4.2,26,.18),m['metal'],parent,.09)
    for side in [-1,1]:
        h.box('V15 walkway glazing',(bridge_x+side*1.90,bridge_y,7.16),(.018,25.8,1.86),m['retail_glass'],parent,.006)
        h.box('V15 walkway light edge',(bridge_x+side*2.01,bridge_y,6.34),(.025,26,.035),m['white_strip'],parent,.008)
        for yy in [-18,3.4]:
            h.cylinder('V15 bridge support',(bridge_x+side*1.25,yy,0),(bridge_x+side*1.25,yy,6.08),.22,m['stone'],parent,24)
        for yy in range(-20,7,3):h.box('V15 walkway mullion',(bridge_x+side*1.93,yy,7.18),(.045,.07,2.0),m['metal'],parent,.008)
    # Signal arms and traffic lights give the street a useful scale reference.
    green=emission('V15 traffic green',(.012,.43,.20),5)
    for xx,yy in [(-22,.35),(-6,-14.9)]:
        h.cylinder('V15 signal pole',(xx,yy,0),(xx,yy,5.4),.066,m['metal'],parent,16)
        h.cylinder('V15 signal arm',(xx,yy,5.4),(xx,-7.1,5.4),.052,m['metal'],parent,16)
        h.box('V15 signal enclosure',(xx,-5.65 if yy> -5 else -8.9,5.29),(.19,.72,.26),m['black'],parent,.06)
        facing=-1 if yy> -5 else 1
        for j in range(3):h.cylinder('V15 signal lens',(xx+facing*.1,(-5.65 if yy> -5 else -8.9)-.23+j*.23,5.29),(xx+facing*.117,(-5.65 if yy> -5 else -8.9)-.23+j*.23,5.29),.071,green if j==0 else m['black'],parent,24)
    for k,x in enumerate(range(-120,128,16)):
        for y in [1.15,-15.05]:
            if y>0 and -8<x<20:continue
            tree('V15 tree '+str(k)+str(y),x,y,parent,m,rng)
            h.cylinder('V15 sidewalk bollard',(x+1.4,y-.60 if y>0 else y+.60,.0),(x+1.4,y-.60 if y>0 else y+.60,.74),.05,m['metal'],parent,16)
        h.cylinder('V15 road manhole',(x+4,-9.8,-.10),(x+4,-9.8,-.095),.30,m['metal'],parent,48)
        for k2 in range(5):h.box('V15 manhole grooves',(x+4-.18+k2*.09,-9.8,-.091),(.022,.45,.003),m['black'],parent,0)
    # A few human-scale silhouettes stay on sidewalks, away from the camera path.
    coat=h.material('V15 pedestrians coats',(.017,.022,.034),.79);skin=h.material('V15 pedestrians skin',(.25,.14,.09),.69)
    for i in range(18):
        xx=rng.uniform(-120,120);yy=rng.choice([.7,-14.8])
        if yy>0 and -8<xx<20:continue
        ht=rng.uniform(1.58,1.82);h.ellipsoid('V15 pedestrian torso',(xx,yy,ht*.62),(.17,.12,.31),coat,parent);h.ellipsoid('V15 pedestrian head',(xx,yy,ht-.12),(.10,.10,.13),skin,parent)
        for sign in [-1,1]:
            h.cylinder('V15 pedestrian leg',(xx+sign*.08,yy,.06),(xx+sign*.08,yy,ht*.51),.060,coat,parent,10)
            h.cylinder('V15 pedestrian arm',(xx+sign*.21,yy,.69),(xx+sign*.18,yy,ht*.78),.043,coat,parent,10)
    # Real geometry instances; traffic repeats after the 48 s camera circuit.
    template=traffic_template('V15_TRAFFIC_COUPE','PRELUDE_SHOWROOM')
    for i,(xx,yy,velocity) in enumerate([(-9,-5.65,P/48),(-67,-2.4,P/24),(31,-2.4,P/48),(15,-8.9,-P/48),(81,-12.15,-P/48),(-89,-12.15,-P/24)]):
        car=h.obj('V15 traffic vehicle '+str(i),None,parent);car.instance_type='COLLECTION';car.instance_collection=template;car.location=(xx,yy,-.10);car.rotation_euler[2]=pi/2 if velocity>0 else -pi/2
        driver=car.driver_add('location',0);driver.driver.type='SCRIPTED';driver.driver.expression=f'(({xx}+({velocity})*frame/30+128)%256)-128'
        for side in [-1,1]:
            # Subtle running lamps and tail illumination remain attached.
            lamp=h.obj('V15 traffic illumination',bpy.data.lights.new('V15 vehicle headlight','SPOT'),car);lamp.location=(side*.62,-2.1,.72);lamp.rotation_euler=(pi/2,0,0);lamp.data.energy=12;lamp.data.color=(.67,.79,1);lamp.data.spot_size=.65;lamp.data.spot_blend=.5
    # Instantiate whole blocks. The module source is not linked as loose objects.
    inst_col=h.collection('V15 / City instances')
    for tile_index in [-2,-1,0,1,2]:
        o=bpy.data.objects.new('V15 City tile instance '+str(tile_index),None);inst_col.objects.link(o);o.instance_type='COLLECTION';o.instance_collection=tile;o.location.x=tile_index*P
    scene['V15_city_period_m']=P;scene['V15_city_loop_seconds']=48
    # Less ambient sky; actual shop windows and luminaires now define the night.
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.15
    fog=bpy.data.objects.get('V14 Avenue haze')
    if fog:
        fog.hide_render=True;fog.hide_set(True)
    h.COL=inst_col
    volume=bpy.data.materials.get('V15 urban atmospheric depth') or bpy.data.materials.new('V15 urban atmospheric depth');volume.use_nodes=True
    nt=volume.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');vol=nt.nodes.new('ShaderNodeVolumePrincipled');vol.inputs['Density'].default_value=.0012;vol.inputs['Color'].default_value=(.43,.52,.65,1);vol.inputs['Anisotropy'].default_value=.3;nt.links.new(vol.outputs['Volume'],out.inputs['Volume'])
    fog=h.box('V15 avenue atmosphere',(0,-47,65),(1500,91,130),volume,None,0);fog.display_type='WIRE';fog['CPO_nonphysical']=True
    print('V15_CITY_READY',len(tile.objects),'module objects',flush=True)

def lighting():
    for name,power in [('V14 Shop ceiling bounce',28),('V14 Front window blue bounce',22),('V14 Toolboard soft key',25),('V14 Magazine raking key',24),('V14 Office ambient',13),('V14 Prelude long highlight',62),('V14 Vezel long highlight',70)]:
        o=bpy.data.objects.get(name)
        if o:o.data.energy=power
    for name in ['V14 Prelude long highlight','V14 Vezel long highlight']:
        o=bpy.data.objects.get(name)
        if o:o.data.color=(.80,.86,1) if 'Prelude' in name else (1,.85,.67);o.data.size=.24
    bpy.context.scene.view_settings.exposure=.15
    bpy.context.scene['V15_lighting']='Lower ambient illumination, selective long vehicle reflections and warm local task lighting.'
    print('V15_SHOP_LIGHTING_READY',flush=True)

def exterior():
    h.COL=h.collection('V15 / Store exterior');v.remove_root('V15_STORE_FACADE')
    parent=h.obj('V15_STORE_FACADE',None)
    stone=h.material('V15 storefront charcoal stone',(.023,.029,.036),.57,.04)
    if not stone.node_tree.nodes.get('V14 microstructure'):h.surface_detail(stone,95,.19,.00065,(.48,.62))
    metal=h.material('V15 storefront satin bronze graphite',(.065,.058,.048),.31,.72)
    panel=h.material('V15 storefront deep blue enamel',(.005,.012,.022),.29,.22,.4)
    letters=emission('V15 storefront ivory lettering',(.62,.54,.39),.9)
    warm=emission('V15 storefront warm reveal',(.68,.45,.23),2.0)
    cool=emission('V15 storefront cool edge',(.33,.49,.61),1.65)
    for o in bpy.context.scene.objects:
        if o.type!='MESH' or not o.name.startswith('EXT.'):continue
        for i,mat in enumerate(o.data.materials):
            if mat and mat.name=='EXT_Greige_Ceramic_80x40mm':o.data.materials[i]=stone
            elif mat and mat.name in ['EXT_Sign_Clean_Muted_Blue','EXT_Sign_Edge_Blue']:o.data.materials[i]=panel
            elif o.name.startswith('EXT.Sign.Letter.'):o.data.materials[i]=letters
    for x in [-.20,.45,2.32,3.96,6.29,9.16,10.50]:
        h.box('V15 facade vertical metal fin',(x,-1.765,6.365),(.045,.25,5.65),metal,parent,.012)
    for x in [-.16,6.33,10.54]:
        h.box('V15 facade vertical light reveal',(x,-1.704,6.365),(.011,.016,5.58),cool,parent,.003)
    for z in [3.53,5.96,9.245]:
        h.box('V15 facade horizontal shadow line',(5.22,-1.71,z),(11.08,.15,.065),metal,parent,.012)
    h.box('V15 canopy concealed warm strip',(5.20,-1.81,2.700),(10.90,.035,.018),warm,parent,.005)
    h.box('V15 canopy upper fine edge',(5.20,-1.945,3.495),(11.12,.025,.018),metal,parent,.004)
    for x in [.30,3.0,7.1,10.15]:
        light=area('V15 facade low wall wash',(x,-2.03,3.58),(x,-1.65,6.5),18,.30,.18,(.74,.82,1),parent)
        light.visible_camera=False;light.visible_transmission=False
    light=area('V15 entrance canopy glow',(5.30,-1.56,2.69),(5.30,-2.30,0),22,3.4,.30,(1,.73,.43),parent);light.visible_camera=False;light.visible_transmission=False
    # A couple of softly occupied upper windows give the facade depth at night.
    glow=emission('V15 upper office soft curtain',(.29,.19,.10),.32)
    for name in ['EXT.Window.Front.02.Curtain','EXT.Window.Front.05.Curtain']:
        o=bpy.data.objects.get(name)
        if o and o.type=='MESH':o.data.materials[0]=glow
    bpy.context.scene['V15_exterior']='Charcoal stone, bronze graphite fins, subtle light reveals, original raised shop lettering.'
    print('V15_EXTERIOR_READY',flush=True)
