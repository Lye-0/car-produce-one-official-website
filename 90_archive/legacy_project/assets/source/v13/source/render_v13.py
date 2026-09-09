"""Render the delivered animated GLB with VTK. No illustrative image generation."""
import os,sys,json,math,io,time,subprocess
from pathlib import Path
os.environ.setdefault('VTK_DEFAULT_OPENGL_WINDOW','vtkEGLRenderWindow')
import numpy as np, vtk
from scipy.spatial.transform import Rotation,Slerp
from vtk.util.numpy_support import numpy_to_vtk,numpy_to_vtkIdTypeArray,vtk_to_numpy
from PIL import Image,ImageDraw
from glb_edit import GLB
OUT=Path(__file__).resolve().parents[1];g=GLB(OUT/'CAR_PRODUCE_ONE_ANIMATED_v13.glb');j=g.j
base_nodes=[dict(n) for n in j['nodes']];parents=g.parent
ren=vtk.vtkRenderer();win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.AddRenderer(ren);win.SetMultiSamples(0);win.SetSize(1280,800);ren.SetBackground(.015,.023,.035);ren.AutomaticLightCreationOff()
actors=[];txcache={};holds=[]
def gettex(idx):
 if idx in txcache:return txcache[idx]
 im=j['images'][j['textures'][idx]['source']];v=j['bufferViews'][im['bufferView']];pic=Image.open(io.BytesIO(g.data[v['byteOffset']:v['byteOffset']+v['byteLength']])).convert('RGBA');a=np.ascontiguousarray(np.array(pic));vi=vtk.vtkImageData();vi.SetDimensions(pic.width,pic.height,1);vi.GetPointData().SetScalars(numpy_to_vtk(a.reshape(-1,4),deep=True));t=vtk.vtkTexture();t.SetInputData(vi);t.InterpolateOn();t.RepeatOn();t.MipmapOn();txcache[idx]=t;holds.append(vi);return t
for i,n in enumerate(j['nodes']):
 if 'mesh' not in n:continue
 for p in j['meshes'][n['mesh']]['primitives']:
  v=g.acc(p['attributes']['POSITION']).astype('float32');faces=g.acc(p['indices']).reshape(-1,3).astype('int64');pd=vtk.vtkPolyData();pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(v,deep=True));pd.SetPoints(pts);ca=vtk.vtkCellArray();ca.SetCells(len(faces),numpy_to_vtkIdTypeArray(np.c_[np.full(len(faces),3),faces].ravel(),deep=True));pd.SetPolys(ca)
  if 'NORMAL'in p['attributes']:
   ns=numpy_to_vtk(g.acc(p['attributes']['NORMAL']),deep=True);ns.SetName('Normals');pd.GetPointData().SetNormals(ns)
  if 'TEXCOORD_0'in p['attributes']:
   tc=numpy_to_vtk(g.acc(p['attributes']['TEXCOORD_0']),deep=True);tc.SetName('TCoords');pd.GetPointData().SetTCoords(tc)
  mp=vtk.vtkPolyDataMapper();mp.SetInputData(pd);mp.ScalarVisibilityOff();ac=vtk.vtkActor();ac.SetMapper(mp);pr=ac.GetProperty();pr.SetInterpolationToPhong();mat=j['materials'][p.get('material',0)];pbr=mat.get('pbrMetallicRoughness',{});clr=np.array(pbr.get('baseColorFactor',[1,1,1,1])[:3]);clr=np.where(clr<=.0031308,12.92*clr,1.055*clr**(1/2.4)-.055);pr.SetColor(*clr);pr.SetAmbient(.25);pr.SetDiffuse(.65);metal=pbr.get('metallicFactor',0);rough=pbr.get('roughnessFactor',.5);pr.SetSpecular(.65 if metal>.3 else .18);pr.SetSpecularPower(85*(1-rough)+10)
  if 'baseColorTexture'in pbr:ac.SetTexture(gettex(pbr['baseColorTexture']['index']))
  if mat.get('extensions',{}).get('KHR_materials_transmission'):
   if 'Frosted'in mat['name']:pr.SetOpacity(.42);pr.SetColor(.64,.77,.83)
   elif '.SmokedGlass' in mat['name']:pr.SetOpacity(.38);pr.SetColor(.07,.12,.17)
   else:pr.SetOpacity(.075);pr.SetColor(.70,.81,.89)
  if mat.get('alphaMode')=='BLEND':ac.ForceTranslucentOn()
  if max(mat.get('emissiveFactor',[0,0,0]))>0:pr.SetAmbient(.96);pr.SetDiffuse(.15)
  ren.AddActor(ac);actors.append((i,ac));holds.extend([pd,pts,ca,mp])
print('actors',len(actors),flush=True)
# Source world transform cache; skip the root glTF Y-up conversion, use Z-up for VTK camera.
def matrix(n):
 if 'matrix'in n:return np.array(n['matrix']).reshape(4,4,order='F')
 m=np.eye(4);m[:3,:3]=Rotation.from_quat(n.get('rotation',[0,0,0,1])).as_matrix()@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0]);return m
clip=j['animations'][0];tracks=[]
for ch in clip['channels']:
 s=clip['samplers'][ch['sampler']];tt=g.acc(s['input']).ravel();vv=g.acc(s['output']);tracks.append((ch['target']['node'],ch['target']['path'],tt,vv,Slerp(tt,Rotation.from_quat(vv)) if ch['target']['path']=='rotation' else None))
camid=g.ids['CPO_CINEMATIC_CAMERA'];world={}
def pose(t):
 for idx,key,tt,vv,sl in tracks:j['nodes'][idx][key]=(sl([t]).as_quat()[0] if sl else np.array([np.interp(t,tt,vv[:,k]) for k in range(vv.shape[1])])).tolist()
 world.clear()
 def go(i,p):
  world[i]=np.eye(4) if i in [0,1] else p@matrix(j['nodes'][i])
  for c in j['nodes'][i].get('children',[]):go(c,world[i])
 go(0,np.eye(4))
 for i,ac in actors:
  m=vtk.vtkMatrix4x4();v=world[i]
  for r in range(4):
   for c in range(4):m.SetElement(r,c,float(v[r,c]))
  ac.SetUserMatrix(m)
 return world[camid]
def light(pos,target,power,color,positional=False):
 l=vtk.vtkLight();l.SetPosition(*pos);l.SetFocalPoint(*target);l.SetColor(*color);l.SetIntensity(power);l.SetLightTypeToSceneLight()
 if positional:l.SetPositional(True);l.SetConeAngle(170);l.SetAttenuationValues(1,.2,.1)
 ren.AddLight(l)
# Broad, soft inspection lights; authored actual glTF lights remain in the file.
light((-5,-8,12),(3,3,0),.36,(.57,.72,1));light((12,-2,6),(5,3,1),.31,(.51,.66,.9));light((2,5,2.8),(2,6,1),.65,(1,.81,.58));light((7,3,2.8),(7,5,1),.72,(1,.83,.66));light((1,1,2.8),(1,1,0),.50,(.76,.83,1))
head=vtk.vtkLight();head.SetLightTypeToHeadlight();head.SetIntensity(.40);head.SetColor(.81,.88,1);ren.AddLight(head)
steps=vtk.vtkRenderStepsPass();ss=vtk.vtkSSAOPass();ss.SetDelegatePass(steps);ss.SetRadius(.19);ss.SetBias(.002);ss.SetKernelSize(32);ss.BlurOn();ren.SetPass(ss)
cam=ren.GetActiveCamera();cam.SetClippingRange(.012,480);cam.SetViewAngle(46);cam.SetViewUp(0,0,1)
wf=vtk.vtkWindowToImageFilter();wf.SetInput(win);wf.SetInputBufferTypeToRGB();wf.ReadFrontBufferOff()
def capture(t,path=None,custom=None):
 m=pose(t);eye=m[:3,3];target=eye-m[:3,2];up=m[:3,1]
 if custom:eye,target=map(np.array,custom);up=[0,0,1]
 cam.SetPosition(*eye);cam.SetFocalPoint(*target);cam.SetViewUp(*up);cam.SetClippingRange(.012,480);win.Render();wf.Modified();wf.Update();img=wf.GetOutput();w,ht,_=img.GetDimensions();a=vtk_to_numpy(img.GetPointData().GetScalars()).reshape(ht,w,3)[::-1].copy()
 if path:Image.fromarray(a).save(path)
 return a
views=[(0,'01_night_cabin',None),(19.2,'02_arrival',None),(24,'03_entry_open',None),(27.5,'04_two_cars',((5.3,-.38,2.2),(4.9,1.4,.70))),(36,'05_tools_hold',None),(60,'06_magazine_hold',None),(77.5,'07_rear_turn',None),(84,'08_pc_approach',None),(90,'09_screen_handoff',None),(28,'10_prelude',((4.2,-.4,1.8),(1.5,1.1,.67))),(28,'11_vezel',((6.0,-.4,1.9),(8.9,1.15,.82)))]
for t,name,custom in views:
 st=time.time();capture(t,OUT/'previews'/f'{name}.png',custom);print(name,round(time.time()-st,2),flush=True)
if '--video'in sys.argv:
 # Overview movie, camera path exactly as stored in GLB. Not a final photoreal render.
 win.SetSize(800,500);fps=8;cmd=['ffmpeg','-y','-f','rawvideo','-pix_fmt','rgb24','-s','800x500','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'previews/CPO_full_journey_review.mp4')];proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=open(OUT/'source/video_render.log','w'))
 for k,t in enumerate(np.linspace(0,90,90*fps+1)):
  a=capture(float(t));proc.stdin.write(a.tobytes())
  if k%120==0:print('video',k,flush=True)
 proc.stdin.close();proc.wait()
win.Finalize()
