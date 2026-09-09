"""Eight requested v16 refinements. Run individual stages once from Blender MCP."""
import bpy,math,json,runpy
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(__file__).resolve().parents[1]
c=runpy.run_path(str(ROOT/'tools/city_v15.py'));h=c['h']
SHIFT=3.65

def parent_world(o,p):
    m=o.matrix_world.copy();o.parent=p;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_world=m

def storefront():
    s=bpy.context.scene
    assert not bpy.data.objects.get('V16_STORE_SETBACK')
    h.COL=h.collection('V16 / Store integration');p=h.obj('V16_STORE_SETBACK',None)
    exclude={'90_VEHICLES','91_NIGHT_CITY','92_CAMERA_AND_ROUTE','93_CINEMATIC_LIGHTING','95_EXTERIOR_CONTEXT'}
    members=[o for o in bpy.data.objects['CPO_F01_ROOT'].children if o.name not in exclude]
    members += [bpy.data.objects[n] for n in ['PRELUDE_SHOWROOM','VEZEL_SHOWROOM','V15_STORE_FACADE']]
    members += [o for o in s.objects if o.name.startswith('V14 Magazine ') and o.type=='EMPTY']
    members += [o for o in s.objects if o.type=='LIGHT' and (o.name.startswith('CINE.WarmFill') or o.name in ['V14 Shop ceiling bounce','V14 Prelude long highlight','V14 Vezel long highlight','V14 Front window blue bounce','V14 Toolboard soft key','V14 Magazine raking key','V14 Office ambient'])]
    for o in members:parent_world(o,p)
    p.location.y=SHIFT
    # Old private paving, tile strips and drains no longer own the street frontage.
    for name in ['109_LEVEL_SITE_AND_PAVING','95_EXTERIOR_CONTEXT']:
        root=bpy.data.objects[name]
        for o in [root,*root.children_recursive]:o.hide_render=True;o.hide_set(True)
    p['setback_m']=SHIFT;s['V16_store_setback_m']=SHIFT
    # Shared street surface and kerb continue uninterrupted in front of the shop.
    tile=bpy.data.collections['V15_CITY_256M_MODULE'];h.COL=tile;front=h.obj('V16_SHARED_PAVEMENT',None)
    stone=bpy.data.materials['V15 granite pedestrian paving'];black=bpy.data.materials['V15 anodised city aluminium']
    h.box('V16 continuous frontage paving',(4.85,.1825,-.05),(15.5,3.935,.10),stone,front,.005)
    h.box('V16 continuous frontage kerb',(4.85,-1.90,-.037),(15.5,.23,.18),stone,front,.012)
    for x in range(-2,13,2):h.box('V16 shared paving joint',(x,.1825,.002),(.005,3.92,.002),black,front,0)
    # Recover the old forecourt as asphalt at exactly the main carriageway level.
    # Existing continuous avenue asphalt already covers the former forecourt.
    for name in ['V14 Shop ceiling bounce','V14 Front window blue bounce','V14 Office ambient']:
        light=bpy.data.objects[name];light['V16_previous_energy']=light.data.energy;light.data.energy*=.87
    for o in s.objects:
        if o.type=='LIGHT' and o.name.startswith('CINE.WarmFill'):o.data.energy*=.87
    print('V16_STOREFRONT_DONE',len(members),flush=True)

def curves(action):
    return [fc for layer in action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]

def smooth(t):
    t=max(0,min(1,t));return t*t*t*(10+t*(-15+6*t))

def camera():
    main=bpy.context.scene;old=main.frame_current;base=bpy.data.objects['CPO_BASE_CAMERA_v13']
    assert not base.get('V16_baked')
    # Evaluate the unchanged base action alone, keeping city evaluation out of sampling.
    qa=bpy.data.scenes.new('V16 camera sampling');anchor=bpy.data.objects.new('V16 sampling parent',None);qa.collection.objects.link(anchor);anchor.matrix_world=base.parent.matrix_world.copy();n=base.copy();qa.collection.objects.link(n);n.parent=anchor;n.matrix_parent_inverse=base.matrix_parent_inverse.copy();n.matrix_basis=base.matrix_basis.copy()
    bpy.context.window.scene=qa;poses=[]
    for f in range(2701):
        qa.frame_set(f);poses.append((n.matrix_world.translation.copy(),n.matrix_world.to_quaternion().normalized()))
    bpy.context.window.scene=main;bpy.data.objects.remove(n,do_unlink=True);bpy.data.objects.remove(anchor,do_unlink=True);bpy.data.scenes.remove(qa)
    start,end=1296,1515;p0,q0=poses[start];p1,q1=poses[end]
    # Turn towards the magazine aisle first; remove the former simultaneous wallward drift.
    look=poses[1430][1]@Vector((0,0,-1));turnq=look.to_track_quat('-Z','Y')
    if q0.dot(turnq)<0:turnq.negate()
    velocity=(poses[end+1][0]-poses[end-1][0])/2
    for f in range(start,end+1):
        if f<=1341:p=p0.copy()
        else:
            u=(f-1341)/(end-1341);dt=end-1341
            p=(2*u**3-3*u**2+1)*p0+(-2*u**3+3*u**2)*p1+(u**3-u**2)*velocity*dt
        if f<=1386:q=q0.slerp(turnq,smooth((f-start)/90))
        else:q=turnq.slerp(q1,smooth((f-1386)/(end-1386)))
        poses[f]=(p,q.normalized())
    action=base.animation_data.action;action.use_fake_user=True;base.animation_data_clear();base.rotation_mode='QUATERNION'
    previous=None;previous_local=None
    for f,(p,q) in enumerate(poses):
        p=p+Vector((0,SHIFT*smooth((f-378)/270),0))
        if previous and previous.dot(q)<0:q.negate()
        previous=q.copy();local=(base.parent.matrix_world@base.matrix_parent_inverse).inverted()@Matrix.LocRotScale(p,q,Vector((1,1,1)));base.location=local.translation;base.rotation_quaternion=local.to_quaternion()
        if previous_local and previous_local.dot(base.rotation_quaternion)<0:base.rotation_quaternion.negate()
        previous_local=base.rotation_quaternion.copy()
        base.keyframe_insert('location',frame=f);base.keyframe_insert('rotation_quaternion',frame=f)
    base.animation_data.action.name='V16_ARRIVAL_AND_DIRECTED_WALK'
    for fc in curves(base.animation_data.action):
        for k in fc.keyframe_points:k.interpolation='LINEAR'
    base['V16_baked']=True
    cam=main.camera
    runpy.run_path(str(ROOT/'tools/idle_v16.py'))['apply']()
    cam['V16_idle_gain']=1.8;main.frame_set(old)
    print('V16_CAMERA_DONE',flush=True)

def loop():
    main=bpy.context.scene;loop=bpy.data.scenes['CPO_V15_DRIVE_LOOP']
    # Remove the actual shop and all its frozen contents from the loop's dependency graph.
    for o in list(loop.objects):
        if o.instance_collection and o.instance_collection.name=='V15_LOOP_STOREFRONT_STATIC':
            loop.collection.objects.unlink(o)
    h.COL=bpy.data.collections.new('V16_LOOP_URBAN_INFILL');p=h.obj('V16_GENERIC_URBAN_INFILL',None)
    stone=h.material('V16 infill warm limestone',(.11,.095,.080),.66);metal=bpy.data.materials['V15 anodised city aluminium'];glass=bpy.data.materials['V15 city glass neutral'];lit=bpy.data.materials['V15 occupied amber offices']
    # An ordinary residential frontage occupies the unique destination plot only in the loop.
    h.box('V16 infill residential mass',(4.85,7.65,11.8),(15.5,11,23.6),stone,p,.08)
    for z in [1.8,5.4,9,12.6,16.2,19.8]:
        for x in [-.9,2.9,6.7,10.5]:
            h.box('V16 infill recessed window',(x,2.11,z),(2.4,.12,2.6),metal,p,.025)
            h.box('V16 infill warm window',(x,2.03,z),(2.18,.018,2.33),lit if int(x+z)%3 else glass,p,.005)
    for z in [3.6,7.2,10.8,14.4,18,21.6]:h.box('V16 infill stone floor band',(4.85,2.0,z),(15.5,.3,.18),stone,p,.02)
    infill=h.COL
    for index in [-2,-1,0,1,2]:
        o=bpy.data.objects.new('V16 loop residential infill '+str(index),None);loop.collection.objects.link(o);o.instance_type='COLLECTION';o.instance_collection=infill;o.location.x=index*256
    loop['V16_no_company']=True;loop['V16_infill']='Residential block with no company mesh, lettering, interior or company lighting.'
    print('V16_LOOP_DONE',flush=True)

def art():
    tile=bpy.data.collections['V15_CITY_256M_MODULE'];h.COL=tile;parent=h.obj('V16_ADDITIONAL_ADVERTISING',None);mats=[]
    for i in range(9,17):
        mat=h.material('V16 campaign '+str(i),(.2,.2,.2),.32);im=bpy.data.images.load(str(ROOT/f'assets/textures/v16/ad{i:02d}.png'),check_existing=True);im.pack()
        nt=mat.node_tree;tex=nt.nodes.new('ShaderNodeTexImage');tex.image=im;sh=nt.nodes['Principled BSDF'];nt.links.new(tex.outputs['Color'],sh.inputs['Base Color']);nt.links.new(tex.outputs['Color'],sh.inputs['Emission Color']);sh.inputs['Emission Strength'].default_value=1.7;mats.append(mat)
    metal=bpy.data.materials['V15 anodised city aluminium']
    for i,(x,y,z,w,ht,facing) in enumerate([(-112,-16.0,9,3.3,4.7,1),(-84,-16.0,9,3,4.3,1),(-56,2.02,8.6,3,4.3,-1),(28,-16.0,8.9,3.1,4.4,1),(56,2.02,9.1,3.2,4.55,-1),(84,2.02,8.8,3.0,4.3,-1),(112,2.02,8.8,3.0,4.3,-1),(-73,-14.9,1.6,1.35,1.91,1)]):
        if i<7:x+=7.2
        h.box(f'V16 advertising {i+9} frame',(x,y,z),(w+.15,.14,ht+.15),metal,parent,.035)
        yy=y+facing*.09;rows=[[(x-w/2,yy,z-ht/2),(x+w/2,yy,z-ht/2)],[(x-w/2,yy,z+ht/2),(x+w/2,yy,z+ht/2)]]
        im=next(n.image for n in mats[i].node_tree.nodes if n.type=='TEX_IMAGE');ratio=im.size[0]/im.size[1];uw=min(1,(w/ht)/ratio);vh=min(1,ratio/(w/ht))
        o=h.patch(f'V16 advertising {i+9} screen',rows,mats[i],parent,facing>0,uvrect=((1-uw)/2,(1-vh)/2,uw,vh));o['campaign_id']=i+9
    # Ensure all eight original campaigns are represented by visible, distinct screens.
    oldm=[bpy.data.materials['V15 digital advertising '+str(i)] for i in range(4)]+[bpy.data.materials['V15 additional campaign '+str(i)] for i in range(4)]
    screens=sorted([o for o in tile.objects if o.type=='MESH' and not o.hide_render and 'screen' in o.name and o.name.startswith('V15')],key=lambda o:o.name)
    for k,o in enumerate(screens):
        i=k%8;o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(oldm[i]);o['campaign_id']=i+1
        uv=o.data.uv_layers.active.data;us=[u.uv.x for u in uv];vs=[u.uv.y for u in uv];lo,hi=min(us),max(us);bot,top=min(vs),max(vs)
        ps=[o.matrix_world@Vector(v) for v in o.bound_box];ratio=(max(p.x for p in ps)-min(p.x for p in ps))/(max(p.z for p in ps)-min(p.z for p in ps));uw=.498*min(1,ratio);vh=.498*min(1,1/ratio)
        for u in uv:u.uv=((i%4%2)*.5+(.5-uw)/2+uw*(u.uv.x-lo)/(hi-lo),(1-(i%4)//2)*.5+(.5-vh)/2+vh*(u.uv.y-bot)/(top-bot))
    for k in range(4,8):
        o=bpy.data.objects['V14 Printed cover '+str(k)];o.data=o.data.copy();mat=h.material('V16 magazine issue '+str(k+1),(.5,.5,.5),.39,0,.22)
        im=bpy.data.images.load(str(ROOT/f'assets/textures/v16/mag{k+1:02d}.png'),check_existing=True);im.pack();nt=mat.node_tree;tex=nt.nodes.new('ShaderNodeTexImage');tex.image=im;nt.links.new(tex.outputs['Color'],nt.nodes['Principled BSDF'].inputs['Base Color'])
        o.data.materials.clear();o.data.materials.append(mat);uv=o.data.uv_layers.active.data;us=[u.uv.x for u in uv];vs=[u.uv.y for u in uv];lo,hi=min(us),max(us);bot,top=min(vs),max(vs)
        for u in uv:u.uv=((u.uv.x-lo)/(hi-lo),(u.uv.y-bot)/(top-bot))
        o['issue_id']=k+1
        o.parent.scale.z=1.025+.015*(k-4)
    print('V16_ART_DONE',flush=True)

def save():
    s=bpy.context.scene;s.name='CPO_V16_MAIN';bpy.data.scenes['CPO_V15_DRIVE_LOOP'].name='CPO_V16_DRIVE_LOOP';s.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/blender/CPO_v16_refined.blend'))
