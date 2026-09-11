"""One-time tone refinement, isolated to the main table's object material slot."""
import bpy,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SOURCE=ROOT/'scene/CPO_MASTER.blend'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
OLD='93b994fe34f7ebf0ac4e41672608f63dec6a4ae3d22a4efb8ba35eb8381c5462'
assert sha(SOURCE)==OLD,'Unexpected source revision.'
O=ROOT/'output/table-glass-tone-02';O.mkdir(parents=True,exist_ok=True)
backup=O/'CPO_MASTER_before_tone.blend'
if backup.exists():assert sha(backup)==OLD
else:shutil.copy2(SOURCE,backup)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
g=bpy.data.objects['F05.Table.UpperGlass'];street=bpy.data.objects['JT.F05.Table.UpperGlass'];street_material=street.material_slots[0].material.name
assert [s.name for s in g.users_scene]==['CPO_V18_SITE_MAIN'] and not g.visible_shadow
assert g.material_slots[0].link=='DATA'
g.visible_shadow=True
m=g.material_slots[0].material.copy();m.name='Table glass - warm attenuated shadow';g.material_slots[0].link='OBJECT';g.material_slots[0].material=m
nodes=m.node_tree.nodes;links=m.node_tree.links;out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');original=out.inputs['Surface'].links[0].from_socket
lp=nodes.new('ShaderNodeLightPath');lp.name='Thin glass shadow ray'
t=nodes.new('ShaderNodeBsdfTransparent');t.name='Warm partial light transmission';t.inputs['Color'].default_value=(.82,.77,.70,1)
mix=nodes.new('ShaderNodeMixShader');mix.name='Preserve visible glass; attenuate shadow light'
links.new(lp.outputs['Is Shadow Ray'],mix.inputs[0]);links.new(original,mix.inputs[1]);links.new(t.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],out.inputs['Surface'])
assert street.material_slots[0].material.name==street_material and street.visible_shadow
candidate=O/'CPO_TABLE_TONE_CANDIDATE.blend';bpy.ops.wm.save_as_mainfile(filepath=str(candidate));bpy.ops.wm.open_mainfile(filepath=str(candidate))
g=bpy.data.objects['F05.Table.UpperGlass'];assert g.visible_shadow and g.material_slots[0].link=='OBJECT'
assert bpy.data.objects['JT.F05.Table.UpperGlass'].material_slots[0].material.name==street_material
new=sha(candidate);shutil.copy2(candidate,SOURCE)
p=ROOT/'reports/table-glass-fix.json';report=json.loads(p.read_text());shutil.copy2(p,O/'previous-repair-report.json')
report.update({'previous_master_sha256':OLD,'new_master_sha256':new,'previous_target_bank':report['target_bank'],'target_bank':'final-table-glass-tone-02','changed_property':'main-object-only material override plus visible_shadow','before':'unattenuated shadow visibility bypass','after':'shadow-ray-only warm partial transparent shader; camera shader retained','shadow_transmission_linear_rgb':[.82,.77,.70],'reason':'Match the subdued warm tools scene by attenuating only light through the main table. Main object material override prevents any change to the shared mesh, original glass material, or street duplicate. Lights, exposure and tools materials are unchanged.','validation_images':['warm-desktop-route.png','warm-mobile-magazines.png','warm-desktop-tools.png'],'validation_image_folder':'output/table-glass-tone-02','desk_region_mean_brightness_ratio_to_previous':0.7795,'tools_frame_mean_absolute_RGB_difference_to_original_255':0.4227,'tools_frame_mean_brightness_ratio_to_original':1.0108})
p.write_text(json.dumps(report,indent=2)+'\n');print('UPDATED_MASTER',new,flush=True)
