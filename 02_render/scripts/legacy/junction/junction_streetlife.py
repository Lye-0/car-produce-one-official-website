"""Mixed street-level uses, campaign formats and stationary street furniture."""
import bpy,math
from pathlib import Path
from mathutils import Matrix,Vector

def build(source,city,x,f,asphalt):
    stone=bpy.data.materials['V15 charcoal limestone'];metal=bpy.data.materials['V15 anodised city aluminium'];glass=bpy.data.materials['V15 retail clear glass'];light=bpy.data.materials['V15 architectural white']
    brick=bpy.data.materials['V15 quiet district terracotta']
    office=stone.copy();office.name='JT.Office limestone';office.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.24,.23,.20,1)
    shutter=metal.copy();shutter.name='JT.Shutter finish';shutter.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.16,.19,.20,1)
    def box(name,lo,hi,mat=metal,T=Matrix.Identity(4)):
        return f.solid('JT.Streetlife.'+name,lo,hi,mat,city,T)
    def text(name,body,cx,front,z,size,T,facing=-1):
        data=bpy.data.curves.new(name,'FONT');data.body=body;data.align_x='CENTER';data.size=size;data.extrude=.003;data.materials.append(light)
        ob=bpy.data.objects.new('JT.Streetlife.'+name,data);city.objects.link(ob)
        ob.matrix_world=T@Matrix.Translation((cx,front+facing*.04,z))@Matrix.Rotation(math.pi if facing>0 else 0,4,'Z')@Matrix.Rotation(math.pi/2,4,'X')
    plans=[('office-west','V15 block 6.S',(56,-16.2),-1,-57,'office'),('retail-east','V15 block 1.N',(-84,2.15),1,-91,'garage'),('brick-east','V15 terraced',(-29,-16.2),1,-57,'closed-shop'),('blade-east','V15 blade',(28,2.15),1,-123,'recessed-lobby')]
    uses={'brick-west':'cafe','oval-west':'hotel'}
    for label,prefix,anchor,side,y,kind in plans:
        facing=-1 if anchor[1]>0 else 1;T=Matrix.Translation((x+side*10.5,y,0))@Matrix.Rotation(side*facing*math.pi/2,4,'Z')@Matrix.Translation((-anchor[0],-anchor[1],0))
        old=[]
        for ob in list(city.objects):
            if ob.get('JT_frontage_family')==label:
                n=ob.name.lower()
                if ('shop' in n or 'retail canopy' in n or ('restaurant' in n and 'ceiling' not in n)):old.append(ob)
            elif ob.name.startswith('JT.Ground.'+label+'.shop glazing'):old.append(ob)
        bpy.data.batch_remove(old)
        if kind=='recessed-lobby':left,right=18.,38.
        else:
            foundation=next(o for o in source.all_objects if o.name.startswith(prefix) and 'foundation' in o.name);lo,hi=f.bounds(foundation);left,right=lo[0],hi[0]
        cx=anchor[0];front=anchor[1];height=3.74
        if kind=='office':slots=[(cx-5,1.1,1.0,2.7,'window'),(cx,1.8,.1,2.9,'door'),(cx+5,1.1,1.,2.7,'window')];mat=office;title='OFFICE'
        elif kind=='garage':slots=[(cx-3,4.4,.1,3.4,'shutter'),(cx+5,1.0,.1,2.8,'door')];mat=stone;title='P  /  SERVICE'
        elif kind=='closed-shop':slots=[(cx-5,4.6,.1,3.15,'shutter'),(cx,1.1,.1,2.7,'door'),(cx+5,3.2,.75,2.7,'window')];mat=brick;title='BAKERY'
        else:slots=[(cx,5.8,.1,3.25,'door')];mat=stone;title='LOBBY'
        last=left
        for j,(sx,w,z0,z1,opening) in enumerate(slots):
            a,b=sx-w/2,sx+w/2
            if a>last:box(label+' wall '+str(j),(last,front-.14,0),(a,front+.14,height),mat,T)
            if z0>0:box(label+' sill '+str(j),(a,front-.14,0),(b,front+.14,z0),mat,T)
            box(label+' lintel '+str(j),(a,front-.14,z1),(b,front+.14,height),mat,T)
            yy=front-facing*.24
            box(label+' opening '+str(j),(a,yy-.025,z0),(b,yy+.025,z1),shutter if opening=='shutter' else glass,T)
            for edge in [a,b]:box(label+' reveal '+str(j)+str(edge),(edge-.05,min(front,yy)-.05,z0),(edge+.05,max(front,yy)+.05,z1),metal,T)
            if opening=='shutter':
                for k in range(int((z1-z0)/.13)):
                    zz=z0+k*.13;box(label+' shutter rib '+str(k),(a,yy+facing*.045-.015,zz),(b,yy+facing*.045+.015,zz+.028),metal,T)
            else:
                box(label+' entry light '+str(j),(a,yy-.25,z1-.06),(b,yy+.25,z1-.02),bpy.data.materials['V15 retail warm lighting'],T)
            last=b
        if last<right:box(label+' wall end',(last,front-.14,0),(right,front+.14,height),mat,T)
        text(label+' directory',title,cx,front+facing*.17,3.86,.34,T,facing)
        uses[label]=kind
    city['JT_street_level_uses']=str(uses)
    # New atlas is packed into the .blend; nothing relies on a workstation-only path.
    image=bpy.data.images.load(str(Path(__file__).resolve().parents[3]/'textures/district-campaigns-v4.png'),check_existing=True);image.pack()
    campaign=bpy.data.materials.new('JT.Campaigns v4');campaign.use_nodes=True;nt=campaign.node_tree;p=nt.nodes.get('Principled BSDF');tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image
    nt.links.new(tex.outputs['Color'],p.inputs['Base Color']);nt.links.new(tex.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=1.8;p.inputs['Roughness'].default_value=.32
    def ad(name,xx,yy,z,w,h,index,side):
        T=Matrix.Translation((xx,yy,0))@Matrix.Rotation(side*math.pi/2,4,'Z')
        panel=f.advertisement('JT.Ad.new.'+name,0,0,z,w,h,0,city,T,1)
        panel.data.materials[0]=campaign;u=.25*(index%4);v=.5 if index<4 else 0;uw=.25;vh=.5
        # Preserve each complete campaign, including its headline, without stretching.
        size=min(w,h);px=(w-size)/2 if w>h*1.4 else 0;pz=z+(h-size)/2 if h>w*1.4 else z
        vertices=[(px-size/2,.112,pz-size/2),(px+size/2,.112,pz-size/2),(px+size/2,.112,pz+size/2),(px-size/2,.112,pz+size/2)]
        for vertex,co in zip(panel.data.vertices,vertices):vertex.co=T@Vector(co)
        coords=[(u+uw,v),(u,v),(u,v+vh),(u+uw,v+vh)]
        for uv,co in zip(panel.data.uv_layers.active.data,coords):uv.uv=co
        words=['RAMEN','CINEMA','RUN','BOOKS','TRAVEL','LIVE','WATCH','GREEN']
        if w>h*1.4:text('campaign caption '+name,words[index],-size/2,.115,z-h*.15,min(h*.38,(w-size)/len(words[index])*.95),T,1)
        elif h>w*1.4:text('campaign caption '+name,words[index],0,.115,z-h/2+(h-size)*.34,min(w*.18,(h-size)*.32),T,1)
        panel['JT_campaign_index']=index
    for i,(side,yy,z,w,h,index) in enumerate([(-1,-119,7.8,5.0,4.3,0),(-1,-105,2,1.3,2.0,3),(-1,-88,4.4,5.4,1.35,4),(-1,-73,2.0,1.3,2.,7),(-1,-57,17.,5.7,6.,1),(1,-123,13.,5.4,6.,2),(1,-91,7.1,5.8,3.2,6),(1,-57,6.8,4.2,3.2,3)]):
        ad(str(i),x+side*10.05,yy,z,w,h,index,side)
        xa,xb=sorted([x+side*10.05,x+side*11.0])
        for dy in [-w*.3,w*.3]:box('advertising bracket '+str(i)+str(dy),(xa,yy+dy-.05,z-.055),(xb,yy+dy+.05,z+.055))
    for i,(side,yy,index) in enumerate([(-1,-133,0),(1,-137,1),(-1,-96,5),(1,-77,2),(-1,-48,4),(1,-37,7)]):
        xx=x+side*8.7;ad('pole'+str(i),xx,yy,3.9,1.2,2.3,index,side)
        box('sign mast '+str(i),(xx-.065,yy-.065,-.1),(xx+.065,yy+.065,5.2))
    # Street trees are complete native models, including trunks and foliage.
    trunk=next(o for o in source.all_objects if o.name.startswith('V15 tree ') and o.name.endswith(' trunk') and not o.hide_render)
    prefix=trunk.name[:-6];lo,hi=f.bounds(trunk);origin=Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0))
    treeparts=[o for o in source.all_objects if o.name.startswith(prefix) and not o.hide_render]
    for i,(side,yy) in enumerate([(-1,-132),(1,-130),(-1,-101),(1,-96),(-1,-72),(1,-66),(-1,-40),(1,-33)]):
        destination=Vector((x+side*9.2,yy,0));T=Matrix.Translation(destination-origin)
        for ob in treeparts:
            n=ob.copy();n.name='JT.Streetlife.tree'+str(i)+'.'+ob.name;n.parent=None;n.animation_data_clear();n.matrix_parent_inverse=Matrix.Identity(4);city.objects.link(n);n.matrix_world=T@ob.matrix_world
        box('tree planter '+str(i),(destination.x-.65,yy-.65,-.08),(destination.x+.65,yy+.65,.12),stone)
    # A parking pocket with a separate pedestrian route behind it.
    collection=bpy.data.collections.get('V15_TRAFFIC_REFINED_pearl')
    assert collection
    car=bpy.data.objects.new('JT.Streetlife.parked car',None);car.instance_type='COLLECTION';car.instance_collection=collection;city.objects.link(car);car.location=(x+7.75,-107,-.1)
    # Bus shelter and utility equipment add structure at pavement height.
    for yy in [-84,-80]:box('shelter post '+str(yy),(x-9.1,yy-.05,-.05),(x-9.,yy+.05,2.8))
    box('shelter roof',(x-9.65,-84.4,2.8),(x-7.7,-79.6,2.96))
    box('shelter bench',(x-9.3,-83.5,.38),(x-8.8,-80.5,.49))
    for yy in [-83,-81]:box('shelter bench leg'+str(yy),(x-9.22,yy-.08,-.03),(x-8.88,yy+.08,.4))
    ad('bus shelter',x-7.9,-79.8,1.55,1.3,2.1,5,-1)
    for i,(side,yy) in enumerate([(-1,-112),(1,-118),(-1,-47),(1,-75)]):
        xx=x+side*8.6;box('utility cabinet'+str(i),(xx-.3,yy-.45,-.05),(xx+.3,yy+.45,1.2),stone)
        box('pavement bin'+str(i),(xx-.23,yy+1.,-.03),(xx+.23,yy+1.5,.75))
    city['JT_added_street_trees']=8;city['JT_added_parked_cars']=1;city['JT_new_campaigns']=8
