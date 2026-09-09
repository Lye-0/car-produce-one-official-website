"""Build a contoured, single-thickness door pane without overwriting the master."""
from pathlib import Path
import bpy,math,json,hashlib
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/glass-fix-01';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'scene/CPO_MASTER.blend'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='7ccd0df887e3da00469f6e79901cb4c52b289a86eeab143b89fed4bc56102a8e','Unexpected source master'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s=bpy.data.scenes['CPO_V18_SITE_MAIN'];bpy.context.window.scene=s;s.frame_set(0);bpy.context.view_layer.update()
base=bpy.data.objects['ARRIVAL_CAR.DoorGlass'];street=bpy.data.objects['JT.ARRIVAL_CAR.DoorGlass'];car=bpy.data.objects['ARRIVAL_CAR']
assert base.data==street.data
car_to_pane=base.matrix_world.inverted()@car.matrix_world

def ring_centres(name,n):
 o=bpy.data.objects[name];matrix=car.matrix_world.inverted()@o.matrix_world;verts=o.data.vertices
 assert (len(verts)-2)%n==0
 return [matrix@(sum((verts[i+k].co for k in range(n)),Vector())/n) for i in range(0,len(verts)-2,n)]
roof=ring_centres('ARRIVAL_CAR.RoofRail1',14)
sill=ring_centres('ARRIVAL_CAR.WindowSill1',10)

def at(points,z):
 for a,b in zip(points,points[1:]):
  if a.z<=z<=b.z:return a.lerp(b,(z-a.z)/(b.z-a.z))
 raise ValueError(z)
# Local car axes are X=width, -Y=height and Z=longitudinal after the original import.
# Follow the actual rail/sill centres rather than a free-standing rectangular box.
front=-.99;rear=.65;columns=84;across=12;verts=[]
for j in range(columns+1):
 z=front+(rear-front)*j/columns
 top=at(roof,z);bottom=at(sill,z)
 top.y+=.005;bottom.y-=.002;top.x-=.002;bottom.x-=.004
 assert bottom.y-top.y>.025
 for k in range(across+1):
  v=k/across;p=bottom.lerp(top,v)
  p.x+=.006*math.sin(math.pi*v)*math.sin(math.pi*j/columns)
  verts.append(car_to_pane@p)
faces=[];stride=across+1
for j in range(columns):
 for k in range(across):
  a=j*stride+k;faces.append((a,a+stride,a+stride+1,a+1))
mesh=bpy.data.meshes.new('CPO.Contoured passenger door glass');mesh.from_pydata(verts,[],faces);mesh.update()
for mat in base.data.materials:mesh.materials.append(mat)
for face in mesh.polygons:face.use_smooth=True
for o in (base,street):
 o.data=mesh
 for modifier in list(o.modifiers):
  if modifier.type=='SOLIDIFY':o.modifiers.remove(modifier)
 solid=o.modifiers.new('CPO.Single glass thickness 3.8mm','SOLIDIFY');solid.thickness=.0038;solid.offset=0;solid.use_even_offset=True;solid.use_quality_normals=True
 o['CPO_glass_revision']='contoured-single-shell-01'
# A narrow rubber perimeter seats the cut glass edge in the existing surrounding frame.
boundary=[j*stride for j in range(columns+1)]+[columns*stride+k for k in range(1,across+1)]+[j*stride+across for j in range(columns-1,-1,-1)]+[k for k in range(across-1,0,-1)]
curve=bpy.data.curves.new('CPO.Door glass edge seal','CURVE');curve.dimensions='3D';curve.resolution_u=1;curve.bevel_depth=.003;curve.bevel_resolution=2;curve.resolution_u=1
poly=curve.splines.new('POLY');poly.points.add(len(boundary)-1)
for point,index in zip(poly.points,boundary):point.co=(*verts[index],1)
poly.use_cyclic_u=True
rubber=bpy.data.materials['ARRIVAL_CAR.Rubber'];curve.materials.append(rubber)
for parent,name in [(base,'ARRIVAL_CAR.DoorGlassSeal'),(street,'JT.ARRIVAL_CAR.DoorGlassSeal')]:
 obj=bpy.data.objects.new(name,curve);parent.users_collection[0].objects.link(obj);obj.parent=parent;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=Matrix.Identity(4)
 obj['CPO_glass_revision']='contoured-single-shell-01'
# Parent/animation and all cameras remain unchanged.
report={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'pane_objects':[base.name,street.name],'vertices':len(mesh.vertices),'quads':len(mesh.polygons),'thickness_m':.0038,'front_longitudinal':front,'rear_longitudinal':rear,'parent':base.parent.name,'frame':0}
(OUT/'build.json').write_text(json.dumps(report,indent=2))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CPO_GLASS_CANDIDATE.blend'))
print('GLASS_CANDIDATE_READY',json.dumps(report),flush=True)
