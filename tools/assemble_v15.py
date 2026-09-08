"""v15 camera validation and a distinct 48 s drive-loop scene."""
import bpy,math,json,importlib.util
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]

def fix_camera():
    scene=bpy.context.scene;old=scene.frame_current;o=bpy.data.objects['CPO_REAR_TURN_GAZE']
    legacy=bpy.data.actions.get('CPO_REAR_TURN_GAZEAction')
    if not legacy:raise RuntimeError('The original v14 gaze action is required.')
    o.animation_data_create();o.animation_data.action=legacy;legacy.use_fake_user=True
    samples=[]
    for f in range(2025,2431,5):
        scene.frame_set(f);q=o.rotation_quaternion.copy().normalized()
        if samples and samples[-1][1].dot(q)<0:q.negate()
        samples.append((f,q))
    o.animation_data_clear();o.rotation_quaternion=samples[0][1];o.keyframe_insert('rotation_quaternion',frame=0)
    for i in range(len(samples)-1):
        f,q=samples[i];nf,nq=samples[i+1]
        for frame in range(f,nf):o.rotation_quaternion=q.slerp(nq,(frame-f)/(nf-f)).normalized();o.keyframe_insert('rotation_quaternion',frame=frame)
    o.rotation_quaternion=samples[-1][1];o.keyframe_insert('rotation_quaternion',frame=2430);o.keyframe_insert('rotation_quaternion',frame=2700)
    action=o.animation_data.action;action.name='V15_CONTINUOUS_REAR_GAZE'
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:point.interpolation='LINEAR'
    scene.frame_set(old);print('V15_CAMERA_FIXED',flush=True)

def validate_camera():
    main=bpy.context.scene;old_frame=main.frame_current;source=main.camera;chain=[];o=source
    while o:chain.append(o);o=o.parent
    qa=bpy.data.scenes.new('V15 temporary camera validation');qa.render.fps=30;mapping={}
    for o in reversed(chain):
        clone=o.copy();clone.name='V15 QA '+o.name;qa.collection.objects.link(clone)
        if o.data:clone.data=o.data.copy()
        clone.parent=mapping.get(o.parent);clone.matrix_parent_inverse=o.matrix_parent_inverse.copy();clone.matrix_basis=o.matrix_basis.copy();mapping[o]=clone
    camera=mapping[source];qa.camera=camera;bpy.context.window.scene=qa
    samples=[];previous=None;previous_position=None
    for f in range(2701):
        qa.frame_set(f);matrix=camera.matrix_world;q=matrix.to_quaternion().normalized();position=matrix.translation.copy()
        step=0 if previous is None else math.degrees(2*math.acos(min(1,abs(previous.dot(q)))))
        travel=0 if previous_position is None else (position-previous_position).length
        samples.append({'frame':f,'rotation_deg':step,'travel_m':travel,'position':list(position)})
        previous=q;previous_position=position
    report={'samples':len(samples),'frame_2323':samples[2323],'largest_rotation_steps':sorted(samples,key=lambda p:p['rotation_deg'],reverse=True)[:12],'largest_translation_steps':sorted(samples,key=lambda p:p['travel_m'],reverse=True)[:5]}
    assert samples[2323]['rotation_deg']<2
    assert max(p['rotation_deg'] for p in samples[2250:2401])<3
    # Subframe evaluation catches interpolation failures that integer samples miss.
    previous=None;maximum=0
    for i in range(400):
        frame=2300+i/8;qa.frame_set(int(frame),subframe=frame-int(frame));q=camera.matrix_world.to_quaternion().normalized()
        if previous:maximum=max(maximum,math.degrees(2*math.acos(min(1,abs(previous.dot(q))))))
        previous=q
    report['maximum_rotation_per_eighth_frame_2300_2350']=maximum
    bpy.context.window.scene=main;main.frame_set(old_frame)
    for clone in mapping.values():bpy.data.objects.remove(clone,do_unlink=True)
    bpy.data.scenes.remove(qa)
    # Conservative camera-to-vehicle box distances through the walking section.
    boxes={}
    for tag in ['PRELUDE_SHOWROOM','VEZEL_SHOWROOM']:
        root=bpy.data.objects[tag+'.V15_BODY'];points=[]
        for o in root.children_recursive:
            if o.type in {'MESH','CURVE','FONT'} and not o.hide_render:points.extend(o.matrix_world@Vector(v) for v in o.bound_box)
        lo=[min(p[i] for p in points) for i in range(3)];hi=[max(p[i] for p in points) for i in range(3)]
        distances=[]
        for pose in samples[648:2431]:
            x,y,z=pose['position'];dx=max(lo[0]-x,0,x-hi[0]);dy=max(lo[1]-y,0,y-hi[1]);distances.append((math.hypot(dx,dy),pose['frame']))
        minimum=min(distances);boxes[tag]={'min':lo,'max':hi,'minimum_xy_camera_distance_m':minimum[0],'at_frame':minimum[1]}
        assert minimum[0]>.275,boxes[tag]
    report['vehicle_clearance_scope']='Conservative XY boxes against all integer walking-camera samples. Not a whole-scene collision proof.';report['vehicle_boxes']=boxes
    (ROOT/'docs/v15-camera-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('V15_CAMERA_VALIDATED',json.dumps({'frame2323':samples[2323]['rotation_deg'],'max_all':report['largest_rotation_steps'][0]['rotation_deg'],'subframe_max':maximum}),flush=True)
    return report

def refined_traffic():
    tile=bpy.data.collections['V15_CITY_256M_MODULE'];source=bpy.data.objects['PRELUDE_SHOWROOM.V15_BODY'];templates=[]
    for colour,rgba in [('pearl',(.42,.45,.48,1)),('graphite',(.025,.031,.042,1)),('blue',(.004,.014,.043,1))]:
        name='V15_TRAFFIC_REFINED_'+colour
        if bpy.data.collections.get(name):templates.append(bpy.data.collections[name]);continue
        col=bpy.data.collections.new(name);paint=bpy.data.materials['V15 Prelude sapphire blue'].copy();paint.name='V15 traffic '+colour;paint.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=rgba
        groups={}
        for side in [-1,1]:
            for wi,wy in enumerate([-1.3025,1.3025]):
                group=bpy.data.objects.new('V15 rotating traffic wheel',None);col.objects.link(group);group.location=(side*(.8125 if wi==0 else .8075),wy,.3353)
                driver=group.driver_add('rotation_euler',0);driver.driver.type='SCRIPTED';driver.driver.expression='2*pi*122*frame/1440';groups[(side,wi)]=group
        wheel_terms=[' tyre',' tread',' sidewall',' wheel outer',' wheel inner',' brake rotor',' sculpted wheel spoke',' RS diamond',' recessed secondary spoke',' wheel centre',' wheel hex',' wheel H']
        for o in source.children_recursive:
            if o.hide_render:continue
            n=o.copy();n.data=o.data;col.objects.link(n);n.parent=None;n.matrix_world=o.matrix_local.copy();n.animation_data_clear();n.hide_render=False
            if n.type=='MESH':
                for slot in n.material_slots:
                    if slot.material and slot.material.name=='V15 Prelude sapphire blue':slot.link='OBJECT';slot.material=paint
            if any(term in o.name for term in wheel_terms):
                corners=[n.matrix_world@Vector(v) for v in n.bound_box];centre=sum(corners,Vector())/len(corners)
                side=1 if centre.x>0 else -1;wi=1 if centre.y>0 else 0;group=groups[(side,wi)];world=n.matrix_world.copy();n.parent=group;n.matrix_parent_inverse=Matrix.Identity(4);n.matrix_basis=Matrix.Translation(-group.location)@world
        templates.append(col)
    for o in tile.objects:
        if o.name.startswith('V15 traffic vehicle '):
            i=int(o.name.rsplit(' ',1)[1]);o.instance_collection=templates[i%3]
    print('V15_REFINED_TRAFFIC_READY',flush=True)

def build_loop():
    main=bpy.context.scene;old_frame=main.frame_current;main.frame_set(0)
    existing=bpy.data.scenes.get('CPO_V15_DRIVE_LOOP')
    if existing:raise RuntimeError('Loop scene already exists; update it rather than silently duplicating it.')
    arrival=bpy.data.objects['ARRIVAL_CAR'];arrival_members={arrival,*arrival.children_recursive}
    storefront=bpy.data.collections.new('V15_LOOP_STOREFRONT_STATIC')
    for o in list(main.objects):
        if o in arrival_members or o.hide_render or o.type not in {'MESH','CURVE','FONT','LIGHT'}:continue
        if 'atmosphere' in o.name.lower() or 'haze' in o.name.lower() or o.name.startswith('CITY.'):continue
        if o.type=='LIGHT' and o.data.type=='SUN':continue
        n=o.copy();n.data=o.data;storefront.objects.link(n);n.parent=None;n.matrix_world=o.matrix_world.copy();n.animation_data_clear();n.hide_render=False
    loop=bpy.data.scenes.new('CPO_V15_DRIVE_LOOP');loop.world=main.world;loop.render.engine='CYCLES';loop.render.fps=30;loop.frame_start=0;loop.frame_end=1439
    loop.cycles.samples=128;loop.cycles.use_denoising=True;loop.cycles.max_bounces=10;loop.cycles.transmission_bounces=8
    loop.render.resolution_x=1920;loop.render.resolution_y=1080;loop.render.resolution_percentage=100
    loop.view_settings.view_transform=main.view_settings.view_transform;loop.view_settings.look=main.view_settings.look;loop.view_settings.exposure=main.view_settings.exposure
    for index in [-2,-1,0,1,2]:
        for label,col in [('city',bpy.data.collections['V15_CITY_256M_MODULE']),('storefront',storefront)]:
            o=bpy.data.objects.new('V15 loop '+label+' '+str(index),None);loop.collection.objects.link(o);o.instance_type='COLLECTION';o.instance_collection=col;o.location.x=index*256
    for o in main.objects:
        if o.name=='V15 avenue atmosphere' or (o.type=='LIGHT' and o.data.type=='SUN' and not o.hide_render):loop.collection.objects.link(o)
    root=bpy.data.objects.new('V15_LOOP_CAR',None);loop.collection.objects.link(root);root.matrix_world=arrival.matrix_world.copy();inverse=root.matrix_world.inverted()
    for o in arrival.children_recursive:
        if o.hide_render or o.type not in {'MESH','CURVE','FONT','LIGHT'}:continue
        n=o.copy();n.data=o.data;loop.collection.objects.link(n);n.parent=root;n.matrix_parent_inverse=Matrix.Identity(4);n.matrix_basis=inverse@o.matrix_world;n.animation_data_clear();n.hide_render=False
    start_x=root.location.x;driver=root.driver_add('location',0);driver.driver.type='SCRIPTED';driver.driver.expression=f'{start_x}+256*frame/1440'
    data=main.camera.data.copy();data.animation_data_clear();data.dof.focus_distance=30;data.clip_end=200
    camera=bpy.data.objects.new('V15_LOOP_CAMERA',data);loop.collection.objects.link(camera);camera.parent=root;camera.matrix_parent_inverse=Matrix.Identity(4);camera.matrix_basis=inverse@main.camera.matrix_world
    for index,amplitude,cycles in [(0,.0010,52),(1,.0007,61),(2,.0004,43)]:
        value=camera.location[index];driver=camera.driver_add('location',index);driver.driver.type='SCRIPTED';driver.driver.expression=f'{value}+{amplitude}*sin(2*pi*{cycles}*frame/1440)'
    loop.camera=camera;loop['purpose']='48 second seamless driving plate; arrival continues in the main scene at frame 0.';loop['period_m']=256;loop['period_frames']=1440;loop['render_exclusive_end']=1440
    loop.timeline_markers.new('LOOP START / ARRIVAL MATCH',frame=0);loop.timeline_markers.new('EXCLUSIVE LOOP END',frame=1440)
    main['V15_loop_scene']=loop.name;main['V15_arrival_entry_frame']=0
    main.frame_set(old_frame);bpy.context.window.scene=main
    print('V15_LOOP_READY',len(storefront.objects),'storefront objects',flush=True)

def match_arrival_velocity():
    import numpy as np
    samples=np.load(ROOT/'assets/source/v13/animation/camera_samples.npz')['source_position']
    speed=float((-3*samples[0,0]+4*samples[1,0]-samples[2,0])*15)
    amplitude=speed/(256/48)-1
    root=bpy.data.objects['V15_LOOP_CAR'];curve=root.animation_data.drivers.find('location',index=0)
    curve.driver.expression=f'-48+256*(frame/1440+({amplitude})/(2*pi)*sin(2*pi*frame/1440))'
    lead=bpy.data.objects['V15 traffic vehicle 0'];lead.animation_data.drivers.find('location',index=0).driver.expression='((-9+(256/48)*frame/30+128)%256)-128'
    loop=bpy.data.scenes['CPO_V15_DRIVE_LOOP'];loop['arrival_speed_m_s']=speed;loop['minimum_loop_speed_m_s']=(256/48)*(1-amplitude)
    loop['motion_profile']='Smooth periodic speed variation; start and end velocity match the arrival clip.'
    report={'period_m':256,'seconds':48,'initial_arrival_speed_m_s':speed,'loop_start_end_speed_m_s':(256/48)*(1+amplitude),'minimum_loop_speed_m_s':(256/48)*(1-amplitude),'camera_translation_per_cycle_m':256,'same_lane_minimum_centre_separation_m':39-256*amplitude/(2*math.pi)}
    assert report['minimum_loop_speed_m_s']>0
    assert report['same_lane_minimum_centre_separation_m']>12
    (ROOT/'docs/v15-loop-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('V15_LOOP_SPEED_MATCHED',json.dumps(report),flush=True)
