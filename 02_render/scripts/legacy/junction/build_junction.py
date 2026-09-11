"""A fixed junction and a vehicle-mounted camera: one continuous physical route."""
import bpy, math, json
from pathlib import Path
from mathutils import Matrix, Vector
R=Path(__file__).resolve().parents[3];O=R/'output/junction-work-v4';O.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'scene/CPO_MASTER.blend'))
bpy.data.batch_remove([ob for ob in bpy.data.objects if ob.name.startswith('JT.')])
print('JUNCTION_PREVIOUS_OBJECTS_CLEARED',flush=True)
if bpy.data.scenes.get('CPO_JUNCTION_DRIVE'):bpy.data.scenes.remove(bpy.data.scenes['CPO_JUNCTION_DRIVE'])
main=bpy.data.scenes['CPO_V18_SITE_MAIN'];bpy.context.window.scene=main;main.frame_set(0);bpy.context.view_layer.update()
scene=main.copy();scene.name='CPO_JUNCTION_DRIVE';scene.use_fake_user=True
for c in list(scene.collection.children):scene.collection.children.unlink(c)
for ob in list(scene.collection.objects):scene.collection.objects.unlink(ob)
city=bpy.data.collections.new('JT.Fixed city module');scene.collection.children.link(city)
unique=bpy.data.collections.new('JT.Original destination');scene.collection.children.link(unique)
vehicles=bpy.data.collections.new('JT.Vehicle and cameras');scene.collection.children.link(vehicles)
road=bpy.data.collections.new('JT.Fixed intersection');scene.collection.children.link(road)
rig=bpy.data.objects.new('JT.Vehicle path',None);vehicles.objects.link(rig)
car=bpy.data.objects['ARRIVAL_CAR'];members={car,*car.children_recursive};origin=car.matrix_world.translation.copy()
allowed=set()
def visit(layer,hidden=False):
 hidden=hidden or layer.exclude or layer.collection.hide_render
 if not hidden:allowed.update(layer.collection.objects)
 for c in layer.children:visit(c,hidden)
visit(bpy.context.view_layer.layer_collection)
def bounds(ob):
 pts=[ob.matrix_world@Vector(p) for p in ob.bound_box]
 return [min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]
def chain(ob):
 a=ob;names=[]
 while a:names.append(a.name);a=a.parent
 return names
# The northbound car uses the left lane, then joins the existing eastbound lane.
X=-86.;HALF=6.;PERIOD=160.;removed=[];copies={};static=[]
LANE=X-2.6
def box(name,lo,hi,mat,collection=road):
 verts=[(x,y,z) for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]
 faces=[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(mat)
 ob=bpy.data.objects.new(name,mesh);collection.objects.link(ob);static.append(ob);return ob
# Cut the road opening through the instanced detailed city module as well.
import re
source_module=bpy.data.collections.get('V15_CITY_256M_MODULE')
cut_module=bpy.data.collections.new('JT.Detailed city with junction')
blocked_groups=set();blocked_objects=set()
blocked_traffic={ob.name for ob in source_module.all_objects if ob.instance_type=='COLLECTION' and 'TRAFFIC' in ob.instance_collection.name and abs(ob.matrix_world.translation.x-X)<6} if source_module else set()
if source_module:
 for ob in source_module.all_objects:
  if ob.type!='MESH':continue
  lo,hi=bounds(ob)
  if (lo[0]<X+HALF+1 and hi[0]>X-HALF-1 and hi[2]>.25) or (ob.name.startswith('V15 skyline') and lo[0]<X+28 and hi[0]>X-28):
   match=re.match(r'(V15 block \d+\.[NS])',ob.name)
   if match:blocked_groups.add(match.group(1))
   else:blocked_objects.add(ob.name)
 for ob in source_module.all_objects:
  if ob.type=='MESH' and ob.name=='V16 north urban ground':
   lo,hi=bounds(ob)
   if lo[0]<X-HALF and hi[0]>X+HALF:
    box('JT.Module.ground west',lo,[X-HALF,hi[1],hi[2]],ob.data.materials[0],cut_module)
    box('JT.Module.ground east',[X+HALF,lo[1],lo[2]],hi,ob.data.materials[0],cut_module)
    removed.append(ob.name);continue
  if any(n in blocked_traffic for n in chain(ob)) or ob.name in blocked_objects or any(ob.name.startswith(g) for g in blocked_groups):removed.append(ob.name);continue
  n=ob.copy();n.name='JT.Module.'+ob.name;n.animation_data_clear();n.constraints.clear();n.parent=None;n.matrix_parent_inverse=Matrix.Identity(4);cut_module.objects.link(n);n.matrix_world=ob.matrix_world.copy();static.append(n)
 print('OPENED_DETAILED_BLOCKS',sorted(blocked_groups),sorted(blocked_objects),flush=True)
for index,ob in enumerate(main.objects):
 if ob not in allowed:continue
 if ob.instance_type=='COLLECTION' and ob.instance_collection==source_module and abs(ob.matrix_world.translation.x)>128:continue
 names=chain(ob)
 if any(n.startswith('CITY.Block06_') for n in names):removed.append(ob.name);continue
 is_city=any(n.startswith(('CITY','V15 ','V15.','V14 Avenue')) for n in names)
 if 'atmosphere' in ob.name.lower():continue
 if ob.type=='MESH' and ob not in members:
  lo,hi=bounds(ob)
  # Open the pavement across the side street, retaining the unmodified rest.
  if 'Sidewalk' in ob.name and lo[0]<X-HALF and hi[0]>X+HALF and hi[2]<.2:
   mat=ob.data.materials[0]
   box('JT.Split pavement west '+ob.name,lo,[X-HALF,hi[1],hi[2]],mat,city)
   box('JT.Split pavement east '+ob.name,[X+HALF,lo[1],lo[2]],hi,mat,city)
   removed.append(ob.name);continue
  if lo[0]<X+HALF and hi[0]>X-HALF and hi[2]>.25 and lo[2]<4  and (hi[0]-lo[0])<45 and not ob.name.startswith('CITY.Road'):
   removed.append(ob.name);continue
 n=ob.copy();n.name='JT.'+ob.name;n.animation_data_clear();n.constraints.clear();n.parent=None;n.matrix_parent_inverse=Matrix.Identity(4)
 if ob.type in ('CAMERA','LIGHT'):n.data=ob.data.copy();n.data.animation_data_clear()
 collection=vehicles if ob in members or ob.type=='CAMERA' else city if is_city else unique
 if ob.instance_type=='COLLECTION' and ob.instance_collection==source_module:n.instance_collection=cut_module
 collection.objects.link(n);n.matrix_world=ob.matrix_world.copy()
 if collection==vehicles:n.parent=rig;n.matrix_world=ob.matrix_world.copy()
 else:static.append(n)
 copies[ob.name]=n
 if index%3000==0:print('JUNCTION_COPY',index,flush=True)
asphalt=bpy.data.materials['V15 rain-dark asphalt'].copy();asphalt.name='JT.Periodic northbound asphalt'
# The original material wraps along X. This street travels along Y.
nt=asphalt.node_tree;sep=next(n for n in nt.nodes if n.type=='SEPXYZ');phase=next(n for n in nt.nodes if n.type=='MATH' and n.operation=='MULTIPLY' and abs(n.inputs[1].default_value-2*math.pi/256)<.001)
nt.links.new(sep.outputs['Y'],phase.inputs[0]);phase.inputs[1].default_value=2*math.pi/PERIOD
coord=nt.nodes['256m periodic world coordinates'];nt.links.new(sep.outputs['X'],coord.inputs['Z']);coord.name='160m periodic northbound coordinates'
pavement=bpy.data.materials['V15 granite pedestrian paving']
paint=bpy.data.materials.new('JT.Road paint');paint.diffuse_color=(.55,.57,.49,1);paint.use_nodes=True;paint.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.55,.57,.49,1)
# A complete 160 m district contains varied frontage and one cross street.
for a,b in [(-140,-15),(-2,20)]:
 box('JT.Incoming asphalt '+str(a),(X-HALF,a,-.21),(X+HALF,b,-.1095),asphalt,city)
 for side in [-1,1]:
  x=X+side*(HALF+1)
  sections=[(a,b)] if side<0 or a!=-140 else [(a,-111),(-103,b)]
  for aa,bb in sections:box('JT.Walkway '+str(aa)+' '+str(side),(x-1,aa,-.22),(x+1,bb,-.02),pavement,city)
  box('JT.White edge '+str(a)+' '+str(side),(X+side*(HALF-.45)-.035,a,-.108),(X+side*(HALF-.45)+.035,b,-.105),paint,city)
# Stop line and crosswalk identify the opening before the turn starts.
for aa,bb in [(-140,-23.6),(-2,20)]:box('JT.Centre line '+str(aa),(X-.05,aa,-.104),(X+.05,bb,-.102),bpy.data.materials['V15 amber road paint'],city)
for yy in [-119,-57]:
 for side in [-1,1]:
  xx=X+side*2.6;direction=-side
  box('JT.Lane arrow stem '+str(side)+str(yy),(xx-.09,yy-1.7,-.103),(xx+.09,yy+1.0,-.101),paint,city)
  points=[(xx-.65,yy+direction*.7,-.100),(xx+.65,yy+direction*.7,-.100),(xx,yy+direction*2,-.100)]
  data=bpy.data.meshes.new('JT.Lane arrow');data.from_pydata(points,[],[(0,1,2)]);data.materials.append(paint);ob=bpy.data.objects.new('JT.Lane arrow head',data);city.objects.link(ob)
box('JT.Parking bay',(X+6,-111,-.20),(X+9.5,-103,-.109),asphalt,city)
box('JT.Parking rear pavement',(X+9.5,-111,-.22),(X+11.5,-103,-.02),pavement,city)
box('JT.Stop line',(X-5.55,-23.5,-.105),(X-.15,-23.15,-.101),paint,city)
for x in range(-91,-80,2):box('JT.Crosswalk '+str(x),(x,-20.4,-.104),(x+.7,-17.1,-.101),paint,city)
# Street furniture remains outside the carriageway and is stationary.
metal=bpy.data.materials['CITY.GraphiteMetal']
for y in [-128,-96,-64,-32]:
 for side in [-1,1]:
  x=X+side*7.5
  box('JT.Lamp post '+str(x)+' '+str(y),(x-.07,y-.07,-.02),(x+.07,y+.07,6.2),metal,city)
  data=bpy.data.lights.new('JT.Downlight '+str(x)+' '+str(y),'AREA');data.energy=380;data.color=(1,.79,.58);data.shape='DISK';data.size=4
  lamp=bpy.data.objects.new(data.name,data);city.objects.link(lamp);lamp.location=(x-side*1.5,y,6);lamp.visible_camera=False;lamp.visible_transmission=False;lamp.visible_glossy=False;static.append(lamp)
  box('JT.Lamp housing '+str(x)+' '+str(y),(x-side*1.5-.35,y-.16,6.05),(x-side*1.5+.35,y+.16,6.16),metal,city)
# Reuse the arrival district's complete buildings, facing this street.
import importlib.util
spec=importlib.util.spec_from_file_location('frontage',Path(__file__).with_name('junction_frontage.py'));frontage=importlib.util.module_from_spec(spec);spec.loader.exec_module(frontage)
frontage.build(source_module,city,X,box,asphalt)
spec=importlib.util.spec_from_file_location('streetlife',Path(__file__).with_name('junction_streetlife.py'));streetlife=importlib.util.module_from_spec(spec);spec.loader.exec_module(streetlife)
streetlife.build(source_module,city,X,frontage,asphalt)
# Repeat the entire mixed district, including its ground-level lighting.
for k in range(-3,4):
 if k==0:continue
 inst=bpy.data.objects.new('JT.Fixed block '+str(k),None);inst.instance_type='COLLECTION';inst.instance_collection=city;inst.location=(0,PERIOD*k,0);road.objects.link(inst);static.append(inst)
# One uniform volume avoids overlapping fog at module boundaries.
source_fog=bpy.data.objects.get('V15 avenue atmosphere')
if source_fog:
 lo,hi=bounds(source_fog);box('JT.Avenue atmosphere',(lo[0],-1200,lo[2]),(hi[0],1200,hi[2]),source_fog.data.materials[0],road)
FPS=30;LOOP_SECONDS=20;TURN_SECONDS=16;LOOP_LAST=600;LAST=1080
start=Vector((LANE,-45.65,origin.z));p0=Vector((LANE,-17.65));p5=Vector((X+12,-5.65))
controls=[p0,p0+Vector((0,4)),p0+Vector((0,8)),p5-Vector((8,0)),p5-Vector((4,0)),p5]
def bez(u):return sum((controls[i]*(math.comb(5,i)*(1-u)**(5-i)*u**i) for i in range(6)),Vector((0,0)))
def tangent(u):return sum(((controls[i+1]-controls[i])*(5*math.comb(4,i)*(1-u)**(4-i)*u**i) for i in range(5)),Vector((0,0)))
lookup=[bez(i/2000) for i in range(2001)];distances=[0]
for a,b in zip(lookup,lookup[1:]):distances.append(distances[-1]+(b-a).length)
length=distances[-1]
# Smooth speed changes on the straights; constant moderate speed around the curve.
V0=8.;VC=3.;V1=8.4
approach=28/((V0+VC)/2);out_distance=origin.x-p5.x;departure=out_distance/((VC+V1)/2)
turn_time=TURN_SECONDS-approach-departure;curve_speed=length/turn_time
# Match curve speed exactly at the joins by solving the two straight durations.
for _ in range(12):
 VC=curve_speed;approach=56/(V0+VC);departure=2*out_distance/(VC+V1);turn_time=TURN_SECONDS-approach-departure;curve_speed=length/turn_time
VC=curve_speed;approach=56/(V0+VC);departure=2*out_distance/(VC+V1);turn_time=TURN_SECONDS-approach-departure
import bisect
def travel(t,duration,a,b):
 u=max(0,min(1,t/duration));return duration*(a*u+(b-a)*(u**3-.5*u**4))
def sample(t):
 if t<=approach:return Vector((LANE,start.y+travel(t,approach,V0,VC),origin.z)),math.pi/2
 if t<=approach+turn_time:
  d=(t-approach)/turn_time*length;i=min(2000,max(1,bisect.bisect_left(distances,d)));u=((i-1)+(d-distances[i-1])/(distances[i]-distances[i-1]))/2000;p=bez(u);v=tangent(u);return Vector((p.x,p.y,origin.z)),math.atan2(v.y,v.x)
 d=travel(t-approach-turn_time,departure,VC,V1);return Vector((p5.x+d,p5.y,origin.z)),0.
poses=[]
for f in range(LAST+1):
 if f<=LOOP_LAST:p=start+Vector((0,-PERIOD+V0*f/FPS,0));yaw=math.pi/2
 else:p,yaw=sample((f-LOOP_LAST)/FPS)
 rig.matrix_world=Matrix.Translation(p)@Matrix.Rotation(yaw,4,'Z')@Matrix.Translation(-origin)
 rig.keyframe_insert('location',frame=f);rig.keyframe_insert('rotation_euler',frame=f);poses.append({'f':f,'position':list(p),'heading':yaw})
for layer in rig.animation_data.action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for curve in bag.fcurves:
    for key in curve.keyframe_points:key.interpolation='LINEAR'
scene.camera=copies['V18_desktop_Route'];scene.frame_start=0;scene.frame_end=LAST;scene.render.fps=FPS;scene.render.resolution_x=1920;scene.render.resolution_y=1080
scene['JT_camera_desktop']=copies['V18_desktop_Route'].name;scene['JT_camera_mobile']=copies['V18_mobile_Route'].name;scene['JT_loop_last']=LOOP_LAST;scene['JT_last']=LAST
scene['JT_fixed_environment']=True;scene['JT_purpose']='Fixed city, shared straight approach and a vehicle-mounted 90-degree turn.'
meta={'loopSeconds':LOOP_SECONDS,'turnSeconds':TURN_SECONDS,'sourceFps':30,'loopLast':LOOP_LAST,'last':LAST,'approachSeconds':approach,'turningSeconds':turn_time,'departureSeconds':departure,'turnSpeed':VC,'curveLength':length,'removed_for_road':removed,'poses':poses}
meta.update(roadCenterX=X,laneCenterX=LANE)
(O/'junction-path.json').write_text(json.dumps(meta,separators=(',',':')))
bpy.context.window.scene=main;main.frame_set(0);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'CPO_JUNCTION_CANDIDATE.blend'));print('JUNCTION_READY',json.dumps({k:v for k,v in meta.items() if k not in ('poses','removed_for_road')}),flush=True)
