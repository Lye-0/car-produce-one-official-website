"""One-time, hash-guarded repair. Changes only the main-scene glass shadow visibility."""
import bpy,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'scene/CPO_MASTER.blend'
OLD='4882dc89b1cea5c8cf95393006d05679442cd2e6ce10dbf1593906a62e7d03f3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE)==OLD,'Unexpected master; do not apply this migration to another revision.'
OUT=ROOT/'output/table-glass-fix-01';OUT.mkdir(parents=True,exist_ok=True)
backup=OUT/'CPO_MASTER_before_table_fix.blend'
if backup.exists():assert sha(backup)==OLD
else:shutil.copy2(SOURCE,backup)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
glass=bpy.data.objects['F05.Table.UpperGlass']
assert [s.name for s in glass.users_scene]==['CPO_V18_SITE_MAIN']
assert glass.visible_shadow
street=bpy.data.objects['JT.F05.Table.UpperGlass']
assert street.visible_shadow and glass != street
# Clear display glass must pass direct illumination with refractive caustics disabled.
# Camera, glossy and transmission rays retain the actual glass geometry/material.
glass.visible_shadow=False
candidate=OUT/'CPO_TABLE_GLASS_CANDIDATE.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(candidate))
bpy.ops.wm.open_mainfile(filepath=str(candidate))
assert not bpy.data.objects['F05.Table.UpperGlass'].visible_shadow
assert bpy.data.objects['JT.F05.Table.UpperGlass'].visible_shadow
new=sha(candidate)
shutil.copy2(candidate,SOURCE)
report={'old_master_sha256':OLD,'new_master_sha256':new,'changed_object':'F05.Table.UpperGlass','changed_property':'visible_shadow','before':True,'after':False,'affected_scenes':['CPO_V18_SITE_MAIN'],'unchanged_jobs':['drive','junction'],'rerender_jobs':['route','portal','tools-idle','magazines-idle','monitor-idle'],'source_bank':'final-glass-fixed-01','target_bank':'final-table-glass-fixed-01','reason':'Direct illumination under clear glass was blocked when refractive caustics were disabled. Only main-scene object shadow visibility changes; no shared material, mesh, light, camera or render settings change.','validation_images':['desktop-route-1950.png','desktop-magazines-1701.png','mobile-route-1950.png','mobile-magazines-1701.png']}
(ROOT/'reports/table-glass-fix.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))

