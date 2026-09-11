"""Street-facing reuse of the arrival district's architectural families."""
import bpy,math,random,json
from mathutils import Matrix,Vector
from bpy_extras.object_utils import world_to_camera_view

FACES=[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]

def mesh(name,points,faces,material,collection,transform=Matrix.Identity(4)):
    data=bpy.data.meshes.new(name);data.from_pydata([transform@Vector(p) for p in points],[],faces);data.materials.append(material)
    ob=bpy.data.objects.new(name,data);collection.objects.link(ob);return ob

def solid(name,lo,hi,material,collection,transform=Matrix.Identity(4)):
    ob=mesh(name,[(x,y,z) for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])],FACES,material,collection,transform)
    ob['JT_solid_ground']=True;return ob

def bounds(ob):
    points=[ob.matrix_world@Vector(p) for p in ob.bound_box]
    return [min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]

def closed_base(label,parts,anchor,transform,collection):
    stone=bpy.data.materials['V15 charcoal limestone'];metal=bpy.data.materials['V15 anodised city aluminium'];glass=bpy.data.materials['V15 retail clear glass']
    name='JT.Ground.'+label+'.';front=anchor[1];facing=-1 if front>0 else 1
    if label=='oval-west':
        # The original hotel had glass and a ceiling, but no closed rear lobby.
        cx,cy=-29,10.15;rx,ry=9.1,8.;segments=48
        ring=[(cx+rx*math.cos(2*math.pi*i/segments),cy+ry*math.sin(2*math.pi*i/segments),z) for z in [-.25,.08] for i in range(segments)]
        faces=[tuple(range(segments-1,-1,-1)),tuple(range(segments,segments*2))]+[(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
        floor=mesh(name+'elliptical foundation',ring,faces,stone,collection,transform);floor['JT_solid_ground']=True
        for i in range(24):
            a,b=math.pi*i/24,math.pi*(i+1)/24
            points=[(cx+r*math.cos(t),cy+s*math.sin(t),z) for z in [0,3.80] for r,s in [(rx-.30,ry-.30),(rx,ry)] for t in [a,b]]
            wall=mesh(name+'curved rear wall '+str(i),points,FACES,stone,collection,transform);wall['JT_solid_ground']=True
        solid(name+'lift and service core',(cx-3,cy-1,.05),(cx+3,cy+5.8,3.80),stone,collection,transform)
        for i in range(8):
            a=2*math.pi*i/8;px=cx+(rx-.5)*math.cos(a);py=cy+(ry-.5)*math.sin(a)
            solid(name+'structural pier '+str(i),(px-.22,py-.22,0),(px+.22,py+.22,3.81),metal,collection,transform)
        return
    if label=='blade-east':
        left,right,back,top=18.0,38.0,15.15,4.26
    else:
        foundation=next(o for o in parts if 'foundation' in o.name)
        lo,hi=bounds(foundation);left,right=lo[0],hi[0];back=hi[1] if facing<0 else lo[1]
        ceilings=[o for o in parts if 'retail roof slab' in o.name or 'restaurant ceiling' in o.name]
        assert ceilings,label
        top=min(bounds(o)[0][2] for o in ceilings)
    # Keep the first 2.2 m as a real shop interior. The remainder is solid mass.
    rear_start=front-facing*2.25;ya,yb=sorted([rear_start,back]);fronta,frontb=sorted([front,back])
    solid(name+'foundation footing',(left,fronta,-.25),(right,frontb,.04),stone,collection,transform)
    solid(name+'rear core',(left,ya,0),(right,yb,top),stone,collection,transform)
    for xx in [left,right-.32]:solid(name+'side wall '+str(xx),(xx,fronta,0),(xx+.32,frontb,top),stone,collection,transform)
    # Deep lintels close the empty band between shop glazing and the upper tower.
    if top>3.78:solid(name+'continuous lintel',(left,fronta,3.76),(right,frontb,top+.01),stone,collection,transform)
    bays=max(3,round((right-left)/4.5));centre=(left+right)/2
    for i in range(bays+1):
        xx=left+(right-left)*i/bays;py=front-facing*.30
        solid(name+'load-bearing pier '+str(i),(xx-.23,py-.24,0),(xx+.23,py+.24,top+.04),stone,collection,transform)
    if label=='blade-east':
        solid(name+'foundation',(left,fronta,-.25),(right,frontb,.10),stone,collection,transform)
        for i in range(bays):
            a=left+(right-left)*i/bays+.24;b=left+(right-left)*(i+1)/bays-.24
            solid(name+'shop glazing '+str(i),(a,front-.015,.12),(b,front+.015,3.75),glass,collection,transform)
        wall=bpy.data.materials['V15 warm retail interior']
        yy=front+1.9;solid(name+'interior finish',(left+.4,yy,0.10),(right-.4,yy+.08,3.70),wall,collection,transform)

def advertisement(name,cx,cy,z,width,height,index,collection,transform=Matrix.Identity(4),facing=-1,second=False):
    material=bpy.data.materials[('V15 additional campaign ' if second else 'V15 digital advertising ')+str(index)]
    metal=bpy.data.materials['V15 anodised city aluminium']
    solid(name+' housing',(cx-width/2-.1,cy-.10,z-height/2-.1),(cx+width/2+.1,cy+.10,z+height/2+.1),metal,collection,transform)
    yy=cy+facing*.112
    panel=mesh(name+' image',[(cx-width/2,yy,z-height/2),(cx+width/2,yy,z-height/2),(cx+width/2,yy,z+height/2),(cx-width/2,yy,z+height/2)],[(0,1,2,3)],material,collection,transform)
    u=.5*(index%2);v=.5 if index<2 else 0;uw=vh=.5
    if width>height:vh=.5*height/width;v+=(.5-vh)/2
    else:uw=.5*width/height;u+=(.5-uw)/2
    uv=panel.data.uv_layers.new(name='Campaign crop')
    coordinates=[(u,v),(u+uw,v),(u+uw,v+vh),(u,v+vh)]
    if facing>0:coordinates=[(2*u+uw-a,b) for a,b in coordinates]
    for loop,co in zip(uv.data,coordinates):loop.uv=co
    panel['JT_advertisement']=True;return panel

def backdrop(collection,x):
    # Real opaque volumes behind the shops, with separate occupied-window meshes.
    opaque=bpy.data.materials['V15 charcoal limestone'];dark=bpy.data.materials['V15 dark office'];warm=bpy.data.materials['V15 occupied amber offices'];cool=bpy.data.materials['V15 occupied white offices']
    plans=[(-1,38,-126,22,14,39),(-1,43,-89,24,15,52),(-1,39,-51,21,14,32),
           (-1,77,-129,26,20,86),(-1,87,-86,24,22,105),(-1,75,-44,23,18,68),
           (1,36,-125,22,12,42),(1,37,-87,23,12,56),(1,34,-49,19,12,37),
           (1,65,-103,23,15,91),(1,74,-80,21,16,112)]
    main=bpy.data.scenes['CPO_V18_SITE_MAIN'];old_size=(main.render.resolution_x,main.render.resolution_y);placed=[]
    def in_arrival_view(lo,hi):
        for profile,w,h in [('desktop',1920,1080),('mobile',1080,1920)]:
            main.render.resolution_x=w;main.render.resolution_y=h;camera=bpy.data.objects['V18_'+profile+'_Route']
            for offset in [-160,0,160]:
                points=[world_to_camera_view(main,camera,Vector((px,py+offset,pz))) for px in [lo[0],hi[0]] for py in [lo[1],hi[1]] for pz in [lo[2],hi[2]]]
                front=[p for p in points if p.z>0]
                if front and min(p.x for p in front)<1 and max(p.x for p in front)>0 and min(p.y for p in front)<1 and max(p.y for p in front)>0:return True
        return False
    for i,(side,distance,y,width,depth,height) in enumerate(plans):
        cx=x+side*distance;lo=(cx-depth/2,y-width/2,0);hi=(cx+depth/2,y+width/2,height)
        # Keep new masses outside the already accepted arrival camera's view.
        if in_arrival_view(lo,hi):
            cx=x+side*34;lo=(cx-depth/2,y-width/2,0);hi=(cx+depth/2,y+width/2,height)
            if in_arrival_view(lo,hi):continue
        label='JT.Backdrop.'+str(i)
        solid(label+' podium',(lo[0],lo[1],-.25),(hi[0],hi[1],5.2),opaque,collection)
        solid(label+' closed tower',(lo[0]+.55,lo[1]+.5,5.2),(hi[0]-.55,hi[1]-.5,height),dark,collection)
        # A stepped crown varies the skyline without a paper-thin silhouette.
        if i%3==0:solid(label+' roof setback',(lo[0]+2,lo[1]+2,height),(hi[0]-2,hi[1]-2,height+5),opaque,collection)
        rng=random.Random(530+i);batches=[([],[]) for _ in range(3)];levels=int((height-6)/3.2);columns=max(4,int(width/2.0));face=cx-side*(depth/2-.53)
        for floor in range(levels):
            for col in range(columns):
                bucket=rng.choices([0,1,2],[.53,.29,.18])[0];verts,faces=batches[bucket];n=len(verts);yy=y-width/2+1.2+(width-2.4)*(col+.5)/columns;zz=6+floor*3.2
                verts.extend([(face,yy-.55,zz),(face,yy+.55,zz),(face,yy+.55,zz+1.65),(face,yy-.55,zz+1.65)]);faces.append((n,n+1,n+2,n+3))
            # Occupied rooms continue around the sides and rear of each volume.
            back=cx+side*(depth/2-.53)
            for col in range(columns):
                bucket=rng.choices([0,1,2],[.66,.22,.12])[0];verts,faces=batches[bucket];n=len(verts);yy=y-width/2+1.2+(width-2.4)*(col+.5)/columns;zz=6+floor*3.2
                verts.extend([(back,yy-.55,zz),(back,yy+.55,zz),(back,yy+.55,zz+1.65),(back,yy-.55,zz+1.65)]);faces.append((n,n+1,n+2,n+3))
            for end in [-1,1]:
                yy=y+end*(width/2-.48);cross_columns=max(3,int(depth/2.0))
                for col in range(cross_columns):
                    bucket=rng.choices([0,1,2],[.62,.24,.14])[0];verts,faces=batches[bucket];n=len(verts);xx=cx-depth/2+1.2+(depth-2.4)*(col+.5)/cross_columns;zz=6+floor*3.2
                    verts.extend([(xx-.50,yy,zz),(xx+.50,yy,zz),(xx+.50,yy,zz+1.65),(xx-.50,yy,zz+1.65)]);faces.append((n,n+1,n+2,n+3))
        for material,(verts,faces) in zip([dark,warm,cool],batches):mesh(label+' windows '+material.name,verts,faces,material,collection)
        placed.append({'side':side,'centre':[cx,y],'height':height})
    main.render.resolution_x,main.render.resolution_y=old_size
    assert len(placed)>=8,placed
    collection['JT_backdrop_buildings']=json.dumps(placed)

def build(source,city,x,box,asphalt=None):
    # A continuous ground slab also supports the rear streets and background masses.
    box('JT.District ground',(-228,-140,-.45),(128,20,-.14),asphalt or bpy.data.materials['JT.Periodic northbound asphalt'],city)
    # Front anchors, not bounding-box centres: every lobby faces the carriageway.
    plans=[
        ('brick-west',('V15 terraced','V15 restaurant','V15 quiet restaurant'),(-29,-16.2),-1,-119),
        ('oval-west',('V15 oval hotel','V15 hotel lobby'),(-29,2.15),-1,-88),
        ('office-west',('V15 block 6.S',),(56,-16.2),-1,-57),
        ('blade-east',('V15 sloping','V15 blade'),(28,2.15),1,-123),
        ('retail-east',('V15 block 1.N',),(-84,2.15),1,-91),
        ('brick-east',('V15 terraced','V15 restaurant','V15 quiet restaurant'),(-29,-16.2),1,-57),
    ]
    stone=bpy.data.materials['V15 granite pedestrian paving'];metal=bpy.data.materials['V15 anodised city aluminium']
    for label,prefixes,anchor,side,y in plans:
        parts=[o for o in source.all_objects if o.name.startswith(prefixes) and not o.hide_render and o.type not in ('EMPTY','CAMERA')]
        assert len(parts)>8,(label,len(parts))
        # North facades face -Y, south facades +Y; map inward to +/-X.
        facing=-1 if anchor[1]>0 else 1
        angle=side*facing*math.pi/2
        transform=Matrix.Translation((x+side*10.5,y,0))@Matrix.Rotation(angle,4,'Z')@Matrix.Translation((-anchor[0],-anchor[1],0))
        for ob in parts:
            n=ob.copy();n.name='JT.Frontage.'+label+'.'+ob.name;n.animation_data_clear();n.constraints.clear();n.parent=None;n.matrix_parent_inverse=Matrix.Identity(4);city.objects.link(n);n.matrix_world=transform@ob.matrix_world
            if n.type=='LIGHT':n.data=ob.data.copy();n.visible_camera=False;n.visible_transmission=False;n.visible_glossy=False
            n['JT_frontage_family']=label
        closed_base(label,parts,anchor,transform,city)
        # Mix facade campaigns, shop-window posters and freestanding small formats.
        if label in ('office-west','retail-east'):
            advertisement('JT.Ad.'+label,anchor[0],anchor[1]+facing*.5,10.6,6.4,7.0,0 if side<0 else 2,city,transform,facing,True)
        elif label=='blade-east':
            advertisement('JT.Ad.'+label,anchor[0],anchor[1]+facing*.45,6.0,8.0,2.2,1,city,transform,facing,True)
        elif label.startswith('brick'):
            advertisement('JT.Ad.'+label,anchor[0]-5.5,anchor[1]+facing*.16,2.1,1.3,2.05,3 if side<0 else 0,city,transform,facing,True)
        # A continuous paved setback joins the inherited lobby to the sidewalk.
        a,b=sorted([x+side*8,x+side*10.7]);box('JT.Frontage apron '+label,(a,y-12,-.18),(b,y+12,-.025),stone,city)
        # Benches give the ground floor a human scale, using the native material.
        for yy in [y-11,y+11]:
            xx=x+side*8.6
            box('JT.Frontage bench '+label+str(yy),(xx-.22,yy-.85,.38),(xx+.22,yy+.85,.48),metal,city)
            for leg in [-.6,.6]:box('JT.Bench support '+label+str(yy)+str(leg),(xx-.16,yy+leg-.06,-.02),(xx+.16,yy+leg+.06,.39),metal,city)
        # A modest pavement display is physically supported by a weighted base.
        if label not in ('oval-west','blade-east'):
            xx=x+side*8.9;yy=y-8.4
            sign_transform=Matrix.Translation((xx,yy,0))@Matrix.Rotation(side*math.pi/2,4,'Z')
            advertisement('JT.Ad.pavement.'+label,0,0,1.45,1.05,1.80,2 if side<0 else 1,city,sign_transform,1)
            solid('JT.Ad.base.'+label,(-.7,-.35,-.02),(.7,.35,.18),metal,city,sign_transform)
            solid('JT.Ad.post.'+label,(-.07,-.07,.1),(.07,.07,.65),metal,city,sign_transform)
    backdrop(city,x)
