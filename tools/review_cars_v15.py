"""Isolated studio checks. Never saves over the production scene."""
import bpy,math,sys,json
from mathutils import Matrix,Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/blender/CPO_v15_refined.blend'))
scene=bpy.data.scenes.new('V15 temporary studio');bpy.context.window.scene=scene
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
scene.cycles.device='GPU';scene.cycles.max_bounces=10;scene.cycles.transmission_bounces=8
scene.render.resolution_x=1280;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
world=bpy.data.worlds.new('studio grey environment');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.34,.36,.4,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45;scene.world=world
def area(name,pos,target,power,size,size_y):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='RECTANGLE';d.size=size;d.size_y=size_y
 o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('studio main softbox',(1,-3,5),(0,0,.6),650,5,3)
area('studio long side card',(-4,0,4.5),(0,0,.8),650,6,1.2)
area('studio rear edge',(3,4,5),(0,0,.7),800,4,1.8)
for light in scene.objects:
 if light.type=='LIGHT':light.data.energy=0
nt=world.node_tree;env=nt.nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(ROOT/'assets/textures/v15/studio_small_09_4k.exr'),check_existing=True)
nt.links.new(env.outputs['Color'],nt.nodes['Background'].inputs['Color']);nt.nodes['Background'].inputs['Strength'].default_value=.55
mat=bpy.data.materials.new('studio warm light grey');mat.diffuse_color=(.24,.25,.27,1);mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.24,.25,.27,1);mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.7
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.005));bpy.context.object.data.materials.append(mat)
d=bpy.data.cameras.new('studio lens');d.lens=58;d.clip_start=.05;c=bpy.data.objects.new('studio camera',d);scene.collection.objects.link(c);scene.camera=c
out=ROOT/'work/v15-studio';out.mkdir(parents=True,exist_ok=True)
only=sys.argv[sys.argv.index('--car')+1] if '--car' in sys.argv else None
for tag in ['PRELUDE_SHOWROOM','VEZEL_SHOWROOM']:
 if only and only not in tag:continue
 original=bpy.data.objects[tag+'.V15_BODY'];copies=[]
 for o in original.children_recursive:
  if o.hide_render:continue
  n=o.copy();n.data=o.data;scene.collection.objects.link(n);n.parent=None;n.matrix_world=o.matrix_local.copy();n.hide_render=False;n.hide_set(False);copies.append(n)
 shots=[('front',(5.8,-7.5,3.5),(0,0,.70)),('side',(8,-.05,2.5),(0,0,.72)),('rear',(5.8,7.5,3.4),(0,0,.78)),('wheel',(2.3,-2.2,.87),(.8,-1.30,.38))]
 if '--turntable' in sys.argv:
  scene.render.resolution_x=960;scene.render.resolution_y=600;scene.cycles.samples=24;scene.render.use_persistent_data=True
  shots=[(f'rotation/{i:04d}',(8.2*math.sin(2*math.pi*i/192),-8.2*math.cos(2*math.pi*i/192),2.9),(0,0,.73)) for i in range(192)]
  (out/(tag+'_rotation')).mkdir(parents=True,exist_ok=True)
 for label,eye,target in shots:
  if label=='wheel':d.lens=64
  else:d.lens=58
  c.location=eye;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/f'{tag}_{label}.png');bpy.ops.render.render(write_still=True)
  print('STUDIO',tag,label,flush=True)
 for o in copies:bpy.data.objects.remove(o,do_unlink=True)
print('V15_STUDIO_DONE',flush=True)
