import bpy,math,json,runpy
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(__file__).resolve().parents[1]
def pchip(xs,ys,x):
 h=[b-a for a,b in zip(xs,xs[1:])];d=[(b-a)/dt for a,b,dt in zip(ys,ys[1:],h)];m=[d[0]]
 for i in range(1,len(xs)-1):
  if d[i-1]*d[i]<=0:m.append(0)
  else:
   w1=2*h[i]+h[i-1];w2=h[i]+2*h[i-1];m.append((w1+w2)/(w1/d[i-1]+w2/d[i]))
 m.append(0);m[0]=0
 i=min(len(xs)-2,max(0,next((j for j in range(len(xs)-1) if x<=xs[j+1]),len(xs)-2)));t=(x-xs[i])/h[i]
 return (2*t**3-3*t*t+1)*ys[i]+(t**3-2*t*t+t)*h[i]*m[i]+(-2*t**3+3*t*t)*ys[i+1]+(t**3-t*t)*h[i]*m[i+1]
def camera():
 main=bpy.context.scene;base=bpy.data.objects['CPO_BASE_CAMERA_v13'];gaze=bpy.data.objects['CPO_REAR_TURN_GAZE'];qa=bpy.data.scenes.new('V17 sample');anchor=bpy.data.objects.new('V17 anchor',None);qa.collection.objects.link(anchor);anchor.matrix_world=base.parent.matrix_world.copy();bc=base.copy();qa.collection.objects.link(bc);bc.parent=anchor;bc.matrix_parent_inverse=base.matrix_parent_inverse.copy();bc.matrix_basis=base.matrix_basis.copy();gc=gaze.copy();qa.collection.objects.link(gc);gc.parent=bc;gc.matrix_parent_inverse=gaze.matrix_parent_inverse.copy();gc.matrix_basis=gaze.matrix_basis.copy()
 bpy.context.window.scene=qa;poses=[]
 for f in range(2701):
  qa.frame_set(f);poses.append((gc.matrix_world.translation.copy(),gc.matrix_world.to_quaternion().normalized()))
 bpy.context.window.scene=main
 for o in [gc,bc,anchor]:bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.scenes.remove(qa)
 def angles(q):
  v=q@Vector((0,0,-1));return math.degrees(math.atan2(v.y,v.x)),math.degrees(math.asin(max(-1,min(1,v.z))))
 start,end=2025,2430;y0,p0=angles(poses[start][1]);y1,p1=angles(poses[end][1]);y1-=360
 xs=[2025,2100,2175,2250,2350,2400,2430];ys=[y0,62,-13,-49.8,-86.1,-155.55,y1]
 px=[2025,2100,2180,2250,2350,2430];py=[p0,-8,-12,-16,-16,p1]
 def direction(y,p):
  y,p=map(math.radians,(y,p));return Vector((math.cos(p)*math.cos(y),math.cos(p)*math.sin(y),math.sin(p)))
 rolls=[]
 for f in [start,end]:
  q=poses[f][1];y,p=angles(q);track=direction(y,p).to_track_quat('-Z','Y');rolls.append((track.inverted()@q).to_euler().z)
 for f in range(start,end+1):
  y=pchip(xs,ys,f);pitch=pchip(px,py,f);roll=rolls[0]+(rolls[1]-rolls[0])*(f-start)/(end-start)
  poses[f]=(poses[f][0],direction(y,pitch).to_track_quat('-Z','Y')@Quaternion((0,0,1),roll))
 for o in [base,gaze]:
  if o.animation_data and o.animation_data.action:o.animation_data.action.use_fake_user=True
  o.animation_data_clear()
 gaze.matrix_parent_inverse=Matrix.Identity(4);gaze.matrix_basis=Matrix.Identity(4);gaze.rotation_mode='QUATERNION';gaze.rotation_quaternion=(1,0,0,0)
 base.rotation_mode='QUATERNION';previous=None;inv=(base.parent.matrix_world@base.matrix_parent_inverse).inverted()
 for f,(p,q) in enumerate(poses):
  local=inv@Matrix.LocRotScale(p,q,Vector((1,1,1)));lq=local.to_quaternion().normalized()
  if previous and previous.dot(lq)<0:lq.negate()
  base.location=local.translation;base.rotation_quaternion=lq;previous=lq.copy();base.keyframe_insert('location',frame=f);base.keyframe_insert('rotation_quaternion',frame=f)
 base.animation_data.action.name='V17_SINGLE_WORLD_GAZE_AND_ROUTE'
 for layer in base.animation_data.action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for k in fc.keyframe_points:k.interpolation='LINEAR'
 gaze['V17_role']='Identity parent only; no additive rotation action.';main['V17_camera_direction']='Monotone world yaw with steady desk-height gaze around frame 2323.'
 print('V17_CAMERA_DONE',flush=True)
def ads():
 data=json.loads((ROOT/'docs/v17-ad-layout.json').read_text());before=json.loads((ROOT/'docs/v17-ad-source.json').read_text());sources={r['id']:bpy.data.objects[r['name']].data.materials[0] for r in before}
 for row in data['assignments']:
  o=bpy.data.objects[row['name']];cid=row['after'];o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(sources[cid]);o['campaign_id']=cid
  im=next(n.image for n in sources[cid].node_tree.nodes if n.type=='TEX_IMAGE' and n.image);ratio=1 if cid<=8 else im.size[0]/im.size[1];ps=[o.matrix_world@Vector(v) for v in o.bound_box];target=(max(v.x for v in ps)-min(v.x for v in ps))/(max(v.z for v in ps)-min(v.z for v in ps));uw=min(1,target/ratio);vh=min(1,ratio/target)
  scale=.5 if cid<=8 else 1;u0=((cid-1)%2)*.5 if cid<=8 else 0;v0=(1-((cid-1)%4)//2)*.5 if cid<=8 else 0;u0+=scale*(1-uw)/2;v0+=scale*(1-vh)/2;uw*=scale;vh*=scale
  uv=o.data.uv_layers.active.data;lo=min(v.uv.x for v in uv);hi=max(v.uv.x for v in uv);bot=min(v.uv.y for v in uv);top=max(v.uv.y for v in uv)
  for v in uv:v.uv=(u0+uw*(v.uv.x-lo)/(hi-lo),v0+vh*(v.uv.y-bot)/(top-bot))
 print('V17_ADS_DONE',flush=True)
if __name__=='__main__':
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/blender/CPO_v16_refined.blend'));camera();ads();bpy.context.scene.name='CPO_V17_MAIN';bpy.data.scenes['CPO_V16_DRIVE_LOOP'].name='CPO_V17_DRIVE_LOOP';bpy.context.scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/blender/CPO_v17_refined.blend'))
