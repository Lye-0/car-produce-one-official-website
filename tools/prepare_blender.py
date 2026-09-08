"""Prepare/verify the CPO v13 working file using Blender's background CLI.

Run with: blender --background --factory-startup --python this_file -- ROOT [--verify]
This deliberately runs in an isolated process, never in a user's live scene.
"""
import bpy
import json
import math
import runpy
import sys
from pathlib import Path
import numpy as np
from mathutils import Quaternion

args = sys.argv[sys.argv.index('--') + 1:]
root = Path(args[0]).resolve()
verify = '--verify' in args
package = root / 'assets/source/v13'
dest = root / 'assets/blender/CPO_v13_working.blend'
report_path = root / 'docs' / ('blender-reopen-validation.json' if verify else 'blender-import-validation.json')

if verify:
    bpy.ops.wm.open_mainfile(filepath=str(dest))
else:
    if dest.exists():
        raise FileExistsError(f'Will not overwrite: {dest}')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    original_empty = list(bpy.data.scenes)
    namespace = runpy.run_path(str(package / 'OPEN_IN_BLENDER.py'), run_name='cpo_original_importer')
    namespace['main']()
    for scene in original_empty:
        if len(scene.objects) == 0 and scene != bpy.context.scene:
            bpy.data.scenes.remove(scene)
    for action in bpy.data.actions:
        action.use_fake_user = True
    bpy.ops.file.pack_all()
    bpy.context.scene['CPO_source'] = '//../source/v13/CAR_PRODUCE_ONE_ANIMATED_v13.glb'
    bpy.context.scene['CPO_scope'] = 'Preparation only. Original geometry and baked camera retained. Review lighting from supplied importer.'

scene = bpy.context.scene
camera = scene.camera
assert camera and camera.name == 'CPO_CINEMATIC_CAMERA'
assert scene.render.fps == 30 and scene.render.fps_base == 1
assert (scene.frame_start, scene.frame_end) == (0, 2700)
samples = np.load(package / 'animation/camera_samples.npz')
poses = []
frames = [0, 150, 378, 450, 594, 702, 1026, 1080, 1200, 1296, 1500, 1701, 1800, 1950, 2025, 2200, 2430, 2520, 2619, 2700]
for frame in frames:
    scene.frame_set(frame)
    actual = camera.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world
    actual_q = actual.to_quaternion()
    q = samples['source_quaternion'][frame]
    expected_q = Quaternion((q[3], q[0], q[1], q[2]))
    dot = min(1.0, abs(float(actual_q.dot(expected_q))))
    poses.append({'frame': frame, 'position': list(actual.translation),
                  'position_error_m': float(np.linalg.norm(np.array(actual.translation) - samples['source_position'][frame])),
                  'rotation_error_deg': math.degrees(2 * math.acos(dot))})

missing_images = [im.name for im in bpy.data.images if im.source == 'FILE' and not im.packed_file and not im.packed_files]
actions = [{'name': a.name, 'frames': list(a.frame_range), 'fake_user': a.use_fake_user, 'users': a.users} for a in bpy.data.actions]
report = {'blender': bpy.app.version_string, 'mode': 'reopen' if verify else 'import',
          'file': str(dest), 'scene': scene.name, 'objects': len(scene.objects),
          'mesh_objects': sum(o.type == 'MESH' for o in scene.objects),
          'camera': camera.name, 'fps': scene.render.fps, 'frame_range': [scene.frame_start, scene.frame_end],
          'actions': actions, 'markers': [{'name': m.name, 'frame': m.frame} for m in scene.timeline_markers],
          'images': len(bpy.data.images), 'unpacked_file_images': missing_images, 'camera_samples': poses,
          'max_position_error_m': max(p['position_error_m'] for p in poses),
          'max_rotation_error_deg': max(p['rotation_error_deg'] for p in poses),
          'limitations': ['Camera checked at selected frames, not a new collision audit.', 'No production material, lighting, or website redesign.']}
report['passed'] = not missing_images and report['max_position_error_m'] < .001 and report['max_rotation_error_deg'] < .1
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('CPO_REPORT', json.dumps(report, ensure_ascii=False), flush=True)
assert report['passed'], 'Import validation failed; see JSON report.'
scene.frame_set(0)
if not verify:
    dest.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest), compress=True)
    print('CPO_SAVED', str(dest), flush=True)
if verify and '--render' in args:
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 8
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    output = root / 'work/blender-review'
    output.mkdir(parents=True, exist_ok=True)
    for frame in [1080, 1800, 2520]:
        scene.frame_set(frame)
        scene.render.filepath = str(output / f'frame_{frame}.png')
        bpy.ops.render.render(write_still=True)
    print('CPO_RENDER_DONE', flush=True)
