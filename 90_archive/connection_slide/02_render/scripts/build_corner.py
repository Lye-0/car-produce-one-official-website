"""Build the B+C corner connector; retain all existing master scenes unchanged."""
import bpy, math, json
from pathlib import Path
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/corner-work';OUT.mkdir(parents=True,exist_ok=True)
MASTER=ROOT/'scene/CPO_MASTER.blend'
bpy.ops.wm.open_mainfile(filepath=str(MASTER))
for obj in list(bpy.data.objects):
 if obj.name.startswith('BC.'):bpy.data.objects.remove(obj,do_unlink=True)
if bpy.data.scenes.get('CPO_CORNER_CONNECTOR'):bpy.data.scenes.remove(bpy.data.scenes['CPO_CORNER_CONNECTOR'])
main=bpy.data.scenes['CPO_V18_SITE_MAIN'];bpy.context.window.scene=main;main.frame_set(0);bpy.context.view_layer.update()
scene=main.copy();scene.name='CPO_CORNER_CONNECTOR';scene.use_fake_user=True
for coll in list(scene.collection.children):scene.collection.children.unlink(coll)
for obj in list(scene.collection.objects):scene.collection.objects.unlink(obj)
collection=bpy.data.collections.new('BC.Connector');scene.collection.children.link(collection)
root=bpy.data.objects.new('BC.Environment',None);collection.objects.link(root)
car=bpy.data.objects['ARRIVAL_CAR'];cabin={car,*car.children_recursive}
allowed=set()
def visit(layer,hidden=False):
 hidden=hidden or layer.exclude or layer.collection.hide_render
 if not hidden:allowed.update(layer.collection.objects)
 for child in layer.children:visit(child,hidden)
visit(bpy.context.view_layer.layer_collection)
deps=bpy.context.evaluated_depsgraph_get();copies={}
for i,o in enumerate(main.objects):
 if o not in allowed:continue
 evaluated=o.evaluated_get(deps);matrix=evaluated.matrix_world.copy()
 n=o.copy();n.name='BC.'+o.name;n.animation_data_clear();n.constraints.clear();n.parent=None
 if o.type in ('CAMERA','LIGHT'):
  n.data=o.data.copy();n.data.animation_data_clear()
 collection.objects.link(n)
 if o not in cabin and o.type!='CAMERA':n.parent=root
 n.matrix_world=matrix;copies[o.name]=n
 if i%2000==0:print('COPIED',i,flush=True)
cam=copies['V18_desktop_Route'];C=cam.matrix_world.copy();pivot=C.translation.copy()
# A nearby solid corner passes right-to-left. Its façade remains opaque at the cut.
wall=bpy.data.objects.new('BC.Corner',None);collection.objects.link(wall)
def material(name,color,roughness=.7,metallic=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=metallic
 tex=m.node_tree.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=65;tex.inputs['Detail'].default_value=3
 bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.2;bump.inputs['Distance'].default_value=.018;m.node_tree.links.new(tex.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal']);return m
concrete=material('BC.Rain-dark architectural concrete',(.092,.116,.123),.72)
metal=material('BC.Vertical graphite battens',(.035,.053,.063),.4,.55)
edge=material('BC.Worn corner trim',(.18,.21,.21),.42,.6)
def box(name,position,scale,mat):
 mesh=bpy.data.meshes.new(name);verts=[(x/2,y/2,z/2) for x in (-1,1) for y in (-1,1) for z in (-1,1)];faces=[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)];mesh.from_pydata(verts,[],faces);mesh.materials.append(mat)
 ob=bpy.data.objects.new(name,mesh);collection.objects.link(ob);ob.parent=wall;ob.location=position;ob.scale=scale
 for attribute in ('visible_shadow','visible_diffuse','visible_glossy','visible_volume_scatter'):setattr(ob,attribute,False)
 bevel=ob.modifiers.new('Rounded masonry edges','BEVEL');bevel.width=.025;bevel.segments=2
 return ob
facade=box('BC.Opaque building corner',(0,1,-1),(7,16,2),concrete)
for x in [-3.35,-2.65,-1.95,-1.25,-.55,.15,.85,1.55,2.25,2.95]:box('BC.Facade batten '+str(x),(x,1,.035),(.055,16,.075),metal)
box('BC.Solid corner trim',(-3.47,1,.08),(.14,16,.18),edge)
for y in [-2.4,-.1,2.2,4.5,6.8]:box('BC.Panel joint '+str(y),(0,y,.02),(7,.032,.03),metal)
DURATION=3.2;FPS=30;LAST=96
smooth=lambda t:t*t*(3-2*t)
for f in range(LAST+1):
 t=f/LAST
 # Exterior rotates into alignment after the façade covers the view.
 turn=smooth(min(1,max(0,(t-.36)/.64)))
 angle=math.radians(32)*(1-turn)
 travel=C.to_3x3()@Vector((1.2*(1-turn),0,-1.1*(1-turn)))
 root.matrix_world=Matrix.Translation(pivot+travel)@Matrix.Rotation(angle,4,'Z')@Matrix.Translation(-pivot)
 root.keyframe_insert('location',frame=f);root.keyframe_insert('rotation_euler',frame=f)
 x=10-20*t
 wall.matrix_world=C@Matrix.Translation((x,0,-3.3))@Matrix.Rotation(math.radians(-12+24*t),4,'Y')
 wall.keyframe_insert('location',frame=f);wall.keyframe_insert('rotation_euler',frame=f)
for rig in [root,wall]:
 for layer in rig.animation_data.action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
scene.frame_start=0;scene.frame_end=LAST;scene.render.fps=FPS
scene['BC_duration']=DURATION;scene['BC_purpose']='Corner occlusion, frozen cabin, environment turn; cut only inside verified full cover.'
scene['BC_camera_desktop']=copies['V18_desktop_Route'].name;scene['BC_camera_mobile']=copies['V18_mobile_Route'].name
# Track the solid building's conservative interior face, independent of any decoration.
def hull(points):
 points=sorted(set(tuple(p) for p in points))
 def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 lower=[]
 for p in points:
  while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
  lower.append(p)
 upper=[]
 for p in reversed(points):
  while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
  upper.append(p)
 return lower[:-1]+upper[:-1]
tracking={}
bpy.context.window.scene=scene
for profile,w,h in [('desktop',1280,720),('mobile',720,1280)]:
 scene.camera=copies['V18_'+profile+'_Route'];scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100
 rows=[]
 for f in range(LAST+1):
  scene.frame_set(f);bpy.context.view_layer.update()
  pts=[world_to_camera_view(scene,scene.camera,facade.matrix_world@v.co) for v in facade.data.vertices]
  assert all(p.z>0 for p in pts),(profile,f,'building crosses camera plane')
  poly=hull([(p.x,1-p.y) for p in pts]);rows.append({'f':f,'polygon':[[round(x,7),round(y,7)] for x,y in poly]})
 tracking[profile]=rows
(OUT/'corner-tracking.json').write_text(json.dumps({'fps':FPS,'lastFrame':LAST,'duration':DURATION,'profiles':tracking},separators=(',',':')))
scene.camera=copies['V18_desktop_Route'];scene.frame_set(0);scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.filepath='//../output/manual-corner/frame_'
bpy.context.window.scene=main;main.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CPO_CORNER_CANDIDATE.blend'))
print('CORNER_SETUP_COMPLETE',len(scene.objects),flush=True)
