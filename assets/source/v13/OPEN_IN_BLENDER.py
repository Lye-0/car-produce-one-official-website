"""Open the animated v13 in a NEW Blender scene, choose the real animated camera.
Run from Blender's Text Editor. Does not erase existing scenes or overwrite a file.
Import/render in Blender itself has NOT been executed in the authoring container.
"""
from pathlib import Path
import json,math
import bpy
from mathutils import Vector
MODEL_PATH = ''  # Only set when this script is pasted into an unsaved Blender text block.
SAVE_BLEND = False  # True saves a new uniquely named .blend next to the GLB.
MODEL_FILENAME='CAR_PRODUCE_ONE_ANIMATED_v13.glb'

def locate():
    candidates=[]
    if MODEL_PATH:candidates.append(Path(bpy.path.abspath(MODEL_PATH)).expanduser())
    if '__file__' in globals():candidates.append(Path(__file__).resolve().parent/MODEL_FILENAME)
    for t in bpy.data.texts:
        if t.filepath and Path(t.filepath).name=='OPEN_IN_BLENDER.py':candidates.append(Path(bpy.path.abspath(t.filepath)).parent/MODEL_FILENAME)
    if bpy.data.filepath:candidates.append(Path(bpy.data.filepath).parent/MODEL_FILENAME)
    for p in candidates:
        if p.is_file():return p
    raise FileNotFoundError('Keep this script next to the v13 GLB, or set MODEL_PATH.')

def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def main():
    model=locate();scene=bpy.data.scenes.new('CPO_v13_ANIMATED')
    if bpy.context.window is None:raise RuntimeError('Run in the Blender interface.')
    bpy.context.window.scene=scene
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    # Set FPS before import: glTF seconds are converted into Blender frame numbers.
    scene.render.fps=30;scene.render.fps_base=1.0
    scene.frame_start=0;scene.frame_end=2700
    scene.render.resolution_x=1920;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
    try:scene.render.engine='BLENDER_EEVEE_NEXT'
    except TypeError:scene.render.engine='CYCLES';scene.cycles.samples=32
    prior=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(model))
    imported=set(bpy.data.objects)-prior
    cams=[o for o in imported if o.type=='CAMERA' and 'CPO_CINEMATIC_CAMERA' in o.name]
    if not cams:raise RuntimeError('The animated camera was not imported.')
    scene.camera=cams[0];scene.camera.data.clip_start=.012;scene.camera.data.clip_end=450
    scene.camera.data.sensor_fit='VERTICAL';scene.camera.data.angle_y=math.radians(46)
    # Keep the MASTER, do not stack the optional idle-loop city animation during the 90s movie.
    for obj in imported:
        ad=obj.animation_data
        if ad:
            for track in ad.nla_tracks:
                if any('CPO_IDLE_CITY_LOOP' in strip.name or (strip.action and 'CPO_IDLE_CITY_LOOP' in strip.action.name) for strip in track.strips):track.mute=True
        if obj.name.startswith('CITY_PERIODIC_STREET'):
            obj.animation_data_clear();obj.location=(0,0,0)
    world=bpy.data.worlds.new('CPO_v13_Night');world.use_nodes=True
    bg=world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.055,.085,.14,1);bg.inputs['Strength'].default_value=.10;scene.world=world
    try:scene.view_settings.view_transform='AgX'
    except TypeError:pass
    # Broad area sources help reveal the black cars without flattening the existing materials.
    lighting=bpy.data.collections.new('CPO_v13_REVIEW_AREA_LIGHTS');scene.collection.children.link(lighting)
    for name,pos,target,power,size,color in [
        ('Street_Sky',(-5,-10,12),(5,0,1),850,12,(.49,.69,1)),
        ('Prelude_Softbox',(2.0,1.1,2.82),(1.5,1.3,.8),160,2.7,(.74,.85,1)),
        ('Vezel_Softbox',(8.5,1.1,2.82),(8.9,1.3,.8),160,2.7,(.90,.87,.81)),
        ('Tool_Warm',(7.0,3.6,2.65),(7.4,5,1.4),85,1.4,(1,.79,.57)),
        ('Magazine_Fill',(1.6,5.4,2.7),(1.1,6,.73),65,1.2,(1,.91,.78)),
        ('Office_Fill',(3.2,6.4,2.7),(2.3,6.6,1.3),55,1.0,(.81,.90,1)),
    ]:
        d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
        o=bpy.data.objects.new(name,d);lighting.objects.link(o);o.location=pos;aim(o,target)
    manifest_path=model.parent/'animation/timeline.json'
    if manifest_path.exists():
        data=json.loads(manifest_path.read_text(encoding='utf-8'))
        for seg in data['segments']:
            marker=scene.timeline_markers.new(seg['title']);marker.frame=round(seg['range'][0]*2700)
        # Editing reference only; the imported baked camera remains the playback source.
        col=bpy.data.collections.new('CPO_ROUTE_GUIDE_NOT_RENDERED');scene.collection.children.link(col)
        curve=bpy.data.curves.new('CPO_Walking_Route_Reference','CURVE');curve.dimensions='3D';spline=curve.splines.new('POLY')
        coords=[v for t,v in data['route_keys'] if .24<=t<=.90];spline.points.add(len(coords)-1)
        for point,xyz in zip(spline.points,coords):point.co=(*xyz,1)
        obj=bpy.data.objects.new('Route_reference_only',curve);col.objects.link(obj);obj.hide_render=True;obj.hide_set(True)
    scene['CPO_notes']='MASTER: 0–2700 frames at 30fps. Idle loop is preserved as an action but disabled here. HTML handoff is demonstrated in web preview.'
    scene.frame_set(0)
    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.overlay.show_relationship_lines=False
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.clip_end=500
    bpy.ops.object.select_all(action='DESELECT')
    scene.camera.select_set(True);bpy.context.view_layer.objects.active=scene.camera
    if SAVE_BLEND:
        path=model.with_suffix('.blend');n=1
        while path.exists():path=model.with_name(model.stem+f'_{n}.blend');n+=1
        bpy.ops.wm.save_as_mainfile(filepath=str(path))
        print('Saved without overwriting:',path)
    print('CPO v13 ready. Camera selected. Frames 0–2700. Play with Space. Save As to retain your changes.')

if __name__=='__main__':main()
