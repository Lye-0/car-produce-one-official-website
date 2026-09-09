import json,math,random
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
rows=json.loads((ROOT/'docs/v17-ad-source.json').read_text());n=len(rows)
centres=np.array([[(a+b)/2 for a,b in zip(r['min'],r['max'])] for r in rows]);sizes=np.array([[b-a for a,b in zip(r['min'],r['max'])] for r in rows]);weights=np.zeros((n,n))
# Same frontage, the end/start boundary and across-road pairs.
for i in range(n):
 for j in range(i+1,n):
  dx=abs(centres[i,0]-centres[j,0]);dx=min(dx,256-dx);same=centres[i,1]*centres[j,1]>0
  if same and dx<12:weights[i,j]+=12
  elif same and dx<33:weights[i,j]+=4
  elif not same and dx<22:weights[i,j]+=3
# Approximate camera co-visibility, weighted by projected size and screen proximity.
for x in np.arange(-128,128,2):
 visible=[]
 for i in range(n):
  dx=(centres[i,0]-x)%256;dy=centres[i,1]+5.23
  if not 4<dx<110:continue
  angle=math.atan2(dy,dx)-.10
  if abs(angle)>.62:continue
  area=abs(math.atan2(dy,max(1,dx-sizes[i,0]/2))-math.atan2(dy,dx+sizes[i,0]/2))*sizes[i,2]/dx
  visible.append((angle,i,area))
 visible.sort()
 for a,b in zip(visible,visible[1:]):
  i,j=sorted([a[1],b[1]]);weights[i,j]+=min(.8,20*math.sqrt(a[2]*b[2]))
families={1:'blue',2:'blue',3:'amber',4:'blue',5:'amber',6:'light',7:'green',8:'purple',9:'amber',10:'light',11:'yellow',12:'blue',13:'cyan',14:'blue',15:'green',16:'amber'}
def similarity(a,b):
 if a==b:return 2.0
 if families[a]==families[b]:return 1.0
 if {families[a],families[b]}=={'blue','cyan'}:return .65
 if {families[a],families[b]}=={'amber','yellow'}:return .30
 return .03
similar=np.array([[similarity(a,b) for b in range(1,17)] for a in range(1,17)])
edges=[(i,j,weights[i,j]) for i in range(n) for j in range(i+1,n) if weights[i,j]>0]
def cost(order):
 score=sum(w*similar[order[i]-1,order[j]-1] for i,j,w in edges)
 # Avoid severe cropping of portrait artwork on a broad billboard.
 score+=sum(15 for i,c in enumerate(order) if c>=9 and sizes[i,0]/sizes[i,2]>1.05)
 return score
old=[r['id'] for r in rows];rng=random.Random(1709);best=None;bestscore=float('inf')
for restart in range(12):
 order=list(range(1,17))+[7,11];rng.shuffle(order);score=cost(order)
 for step in range(8000):
  a,b=rng.sample(range(n),2);order[a],order[b]=order[b],order[a];candidate=cost(order);temp=8*(1-step/8000)**2+.04
  if candidate<score or rng.random()<math.exp(min(0,(score-candidate)/temp)):score=candidate
  else:order[a],order[b]=order[b],order[a]
  if score<bestscore:bestscore=score;best=order.copy()
report={'method':'Visible size/proximity and periodic same-frontage adjacency; heuristic projection, followed by rendered review.','before_score':cost(old),'after_score':bestscore,'families':families,'assignments':[{'name':r['name'],'before':r['id'],'after':best[i],'position':centres[i].tolist()} for i,r in enumerate(rows)],'nearest_same_colour_before':sum(1 for i,j,w in edges if w>=12 and families[old[i]]==families[old[j]]),'nearest_same_colour_after':sum(1 for i,j,w in edges if w>=12 and families[best[i]]==families[best[j]])}
(ROOT/'docs/v17-ad-layout.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['assignments','families']}),flush=True)
