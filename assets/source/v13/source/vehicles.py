"""Editable, original photo-guided approximate vehicle models; not Honda CAD assets.
Coordinate convention: width X, forward -Y, up Z. Metres. No downloaded meshes.
"""
import math
import numpy as np
import trimesh
from scipy.interpolate import PchipInterpolator
from shapely.geometry import Polygon,Point,box
import geometry_tools as h
from glb_edit import prism

def patch(name,pts,mat,parent,smooth=True):
    a=np.asarray(pts,float);ny,nx,_=a.shape;f=[]
    for j in range(ny-1):
        for k in range(nx-1):
            p=j*nx+k;f.extend([[p,p+1,p+nx+1],[p,p+nx+1,p+nx]])
    m=trimesh.Trimesh(a.reshape(-1,3),f,process=False)
    return h.mesh(name,m,mat,parent,smooth=smooth)

def sheet(name,poly,thick,mat,parent):
    v,f=prism(Polygon(poly),-thick/2,thick/2)
    return h.mesh(name,trimesh.Trimesh(v,f,process=False),mat,parent)

def make_car(tag,parent,suv=False,cabin=False):
    root=h.group(tag,parent,'Photo-guided procedural approximation; editable panels. No manufacturer CAD.')
    L,W,H=(4.34,1.79,1.59) if suv else (4.52,1.88,1.355)
    paint=h.material(tag+'.Paint',(0.009,0.013,0.020) if suv else ((.027,.032,.042) if cabin else (.010,.033,.095)),.23,.65)
    h.g.j['materials'][paint]['extensions']={'KHR_materials_clearcoat':{'clearcoatFactor':1,'clearcoatRoughnessFactor':.13}}
    if 'KHR_materials_clearcoat' not in h.g.j['extensionsUsed']:h.g.j['extensionsUsed'].append('KHR_materials_clearcoat')
    black=h.material(tag+'.Rubber',(.012,.014,.016),.72,0)
    dark=h.material(tag+'.Trim',(.020,.026,.032),.38,.35)
    alloy=h.material(tag+'.BrushedAlloy',(.32,.38,.43),.23,.92)
    gun=h.material(tag+'.WheelGunmetal',(.067,.082,.099),.26,.86)
    glass=h.material(tag+'.SmokedGlass',(.015,.040,.058),.12,.08)
    h.g.j['materials'][glass]['extensions']={'KHR_materials_transmission':{'transmissionFactor':.72 if not cabin else .96},'KHR_materials_ior':{'ior':1.46}}
    h.g.j['materials'][glass]['doubleSided']=True
    led=h.material(tag+'.LED',(.76,.85,.94),.2,.1,emission=(.48,.62,.83))
    red=h.material(tag+'.RearLED',(.4,.008,.012),.23,.1,emission=(.25,.002,.003))
    brake=h.material(tag+'.Caliper',(.05,.14,.42) if not suv else (.18,.20,.21),.34,.52)
    leather=h.material(tag+'.Leather',(.018,.023,.029),.67,.02)
    body=h.group(tag+'.Body',root); roof=h.group(tag+'.CabinShell',root)
    half=L/2; belt=.99 if suv else .88; wb=2.61 if suv else 2.60; yf=-wb/2;yr=wb/2;r=.346 if suv else .327
    ys=np.array([-half,-half+.16,-1.5,-.85,0,.9,1.6,half-.08,half]);ws=W/2*np.array([.82,.94,.99,1,.985,1,.99,.94,.86]);tops=np.array([.70,.80,.89,belt,belt,belt,.86,.80,.73]) if not suv else np.array([.79,.88,.99,1.04,1.04,1.04,1.03,.95,.86])
    width=PchipInterpolator(ys,ws);top=PchipInterpolator(ys,tops)
    # Side skins genuinely have open wheel-arch cutouts rather than discs painted over a box.
    sample=np.linspace(-half,half,100)
    poly=Polygon([(y,.20 if not suv else .23) for y in sample]+[(y,float(top(y))) for y in sample[::-1]])
    for wheel_y in [yf,yr]:poly=poly.difference(Point(wheel_y,r).buffer(r+.047,quad_segs=28))
    for side in [-1,1]:
        v,f=prism(poly,0,.025);v=np.c_[side*(width(v[:,0])-.045*(1-v[:,1]/belt)+v[:,2]),v[:,0],v[:,1]]
        m=trimesh.Trimesh(v,f,process=False);m.fix_normals();h.mesh(tag+f'.Body.Side{side}',m,paint,body,smooth=True)
        # Character line and sill; no fake full mesh panels over the arches.
        for zoff in [-.055,-.16]:
            line=[(side*(float(width(y))+.008),y,float(top(y))+zoff) for y in np.linspace(-1,1.04,30)]
            h.pipe(tag+f'.Crease{side}_{zoff}',line,.003,dark,body,n=8)
        h.transformed_box(tag+f'.Rocker{side}',(side*(W/2-.022),0,.19 if not suv else .24),(.05,1.88,.07),dark,body,bevel=.012)
        for yy in [yf,yr]:
            aa=np.linspace(0,np.pi,55);line=[(side*(float(width(yy+.375*np.cos(a)))+.008),yy+(r+.052)*np.cos(a),r+(r+.052)*np.sin(a)) for a in aa]
            h.pipe(tag+f'.ArchTrim{side}_{yy}',line,.014 if suv else .009,dark if suv else paint,body,n=10)
    # Belt deck with crown, hood and rear deck; cabin volume sits above it.
    pts=[[(x*float(width(y)),y,float(top(y))+.026*(1-x*x)) for x in np.linspace(-1,1,21)] for y in sample]
    # Keep the passenger compartment open down to its real floor, not capped at the belt line.
    for sl,label in [(np.linspace(-half,-1.13,35),'HoodSkin'),(np.linspace(1.63,half,22),'TailDeck')]:
        patch(tag+'.'+label,[[(x*float(width(y)),y,float(top(y))+.026*(1-x*x)) for x in np.linspace(-1,1,25)] for y in sl],paint,body)
    h.transformed_box(tag+'.CabinBase',(0,.20,.26),(1.56,2.52,.08),leather,roof,bevel=.012)
    for end in [-1,1]:
        y=end*half;zz=np.linspace(.22 if not suv else .25,float(top(y)),13)
        pts=[[(x*float(width(y))*(.96+.04*np.sin((z-.2)*np.pi)),y-end*.18*x*x,z) for x in np.linspace(-1,1,21)] for z in zz]
        patch(tag+f'.Bumper{end}',pts,paint,body)
        h.transformed_box(tag+f'.LowerSplitter{end}',(0,y-end*.012,.22 if not suv else .24),(W*.88,.09,.048),dark,body,bevel=.015)
    # Windshield/canopy continuous curves, separate glazed and painted roof regions.
    cY=np.array([-1.13,-.72,-.29,.67,1.13,1.63] if not suv else [-1.02,-.63,-.32,.66,1.29,1.73])
    cH=np.array([belt+.02,H-.14,H,H-.012,H-.22,belt+.03] if not suv else [1.06,H-.15,H,H,H-.10,1.06])
    cW=np.array([.84,.71,.64,.67,.75,.85])*W/1.88
    if suv:cW=np.array([.78,.72,.69,.71,.74,.78])
    for a,b,material,label in [(0,2,glass,'Windshield'),(2,3,paint,'Roof'),(3,5,glass,'RearGlass')]:
        sy=np.linspace(cY[a],cY[b],28);ih=PchipInterpolator(cY,cH);iw=PchipInterpolator(cY,cW)
        pts=[[(x*float(iw(y)),y,float(ih(y))-.065*x*x) for x in np.linspace(-1,1,23)] for y in sy]
        if not cabin or label!='Roof':patch(tag+'.'+label,pts,material,roof)
        else:patch(tag+'.'+label,pts,paint,roof)
    for side in [-1,1]:
        line=[(side*cW[i],cY[i],cH[i]-.064) for i in range(6)]
        h.pipe(tag+f'.RoofRail{side}',line,.025,paint,roof,n=14)
        pts=[[(side*(cW[k]*(1-v)+float(width(cY[k]))*v*.965),cY[k],(cH[k]-.065)*(1-v)+(float(top(cY[k]))+.02)*v) for v in np.linspace(0,1,8)] for k in range(6)]
        if not cabin:patch(tag+f'.SideWindow{side}',pts,glass,roof)
        for k in ([2,4] if suv else [3]):
            h.pipe(tag+f'.Pillar{side}_{k}',[(side*cW[k],cY[k],cH[k]-.07),(side*(float(width(cY[k]))*.974),cY[k],float(top(cY[k]))+.005)],.032,paint,roof)
        h.pipe(tag+f'.WindowSill{side}',[(side*float(width(y))*.973,y,float(top(y))+.018) for y in np.linspace(cY[0],cY[-1],30)],.011,alloy if suv else dark,roof,n=10)
        for yy in ([.22,1.09] if suv else [.62]):
            xx=side*(float(width(yy))+.013)
            h.transformed_box(tag+f'.Handle{side}_{yy}',(xx,yy,belt-.06),(.020,.145,.032),paint,body,bevel=.006)
        for yy in ([.45,1.63] if suv else [1.19]):
            zz=float(top(yy));h.pipe(tag+f'.DoorSeam{side}_{yy}',[(side*float(width(yy)),yy,.25),(side*(float(width(yy))+.007),yy,zz-.02)],.003,dark,body,n=6)
        # Mirror stalk and housing; included in clearance bounding box.
        h.cyl(tag+f'.MirrorStem{side}',(side*(W/2-.03),-.69,belt+.12),(side*(W/2+.07),-.64,belt+.16),.018,dark,body,n=14)
        h.ball(tag+f'.Mirror{side}',(side*(W/2+.078),-.59,belt+.175),(.10,.16,.065),paint,body)
        h.transformed_box(tag+f'.MirrorFace{side}',(side*(W/2+.083),-.437,belt+.179),(.145,.008,.08),alloy,body,bevel=.01)
    # Hood seams and grille, distinct coupe versus SUV faces.
    for side in [-1,1]:
        h.pipe(tag+f'.HoodSeam{side}',[(side*float(width(y))*.77,y,float(top(y))+.02) for y in np.linspace(-half+.12,-1.05,30)],.003,dark,body,n=8)
        head=[(side*.22,-half+.02,.81 if suv else .73),(side*.55,-half+.07,.83 if suv else .75),(side*.80,-half+.29,.91 if suv else .83)]
        h.pipe(tag+f'.HeadlightHousing{side}',head,.033,dark,body,n=16);h.pipe(tag+f'.Daylight{side}',[(x,y-.009,z+.008) for x,y,z in head],.011,led,body,n=12)
        for k in range(3):h.ball(tag+f'.LEDProjector{side}_{k}',(side*(.49+k*.085),-half+.072+k*.05,.80 if suv else .72),(.03,.018,.022),alloy,body)
        rear=[(side*.12,half+.008,.73 if not suv else .91),(side*.66,half-.015,.74 if not suv else .92),(side*.81,half-.14,.77 if not suv else .98)]
        h.pipe(tag+f'.TailLight{side}',rear,.018,red,body,n=10)
    h.transformed_box(tag+'.Grille',(0,-half-.010,.55 if suv else .41),(1.26,.045,.30 if suv else .21),black,body,bevel=.055)
    for i in range(7 if suv else 4):h.transformed_box(tag+f'.GrilleSlat{i}',(0,-half-.039,(.43+i*.037) if suv else (.345+i*.043)),(1.18,.014,.011),gun,body,bevel=.004)
    if not suv:
        for x in np.arange(-.56,.57,.065):h.transformed_box(tag+f'.GrilleMesh{x}',(x,-half-.035,.413),(.009,.013,.16),gun,body,bevel=.002)
    # Modest original H-like emblem built as a frame; no downloaded logo texture.
    h.pipe(tag+'.BadgeFrame',[(-.045,-half-.044,.68),(-.05,-half-.044,.755),(.05,-half-.044,.755),(.045,-half-.044,.68),(-.045,-half-.044,.68)],.006,alloy,body,n=8)
    for x in [-.023,.023]:h.cyl(tag+f'.BadgeH{x}',(x,-half-.049,.692),(x,-half-.049,.744),.005,alloy,body,n=10)
    h.cyl(tag+'.BadgeCross',(-.023,-half-.049,.717),(.023,-half-.049,.717),.004,alloy,body,n=10)
    h.transformed_box(tag+'.Plate',(0,-half-.067,.52 if not suv else .37),(.32,.02,.11),dark,body,bevel=.012)
    # Four wheels with tyre bulge, beads, tread grooves, disc, two-tone paired spokes and fasteners.
    wheels=[]
    for side in [-1,1]:
        for yy in [yf,yr]:
            ww=h.group(tag+f'.Wheel_{side}_{yy}',root);wheels.append((ww,(side*(W/2-.065),yy,r)))
            xc=side*(W/2-.065);angles=np.linspace(0,2*np.pi,73)
            profile=[(-.115,r*.79),(-.118,r*.88),(-.095,r*.975),(-.067,r),(.067,r),(.095,r*.975),(.118,r*.88),(.115,r*.79)]
            vv=[(xc+d,yy+rr*np.sin(a),r+rr*np.cos(a)) for d,rr in profile for a in angles];ff=[];n=len(angles)
            for j in range(len(profile)):
                jj=(j+1)%len(profile)
                for k in range(n-1):ff.extend([[j*n+k,j*n+k+1,jj*n+k+1],[j*n+k,jj*n+k+1,jj*n+k]])
            m=trimesh.Trimesh(vv,ff,process=False);m.fix_normals();h.mesh(tag+f'.Tire{side}_{yy}',m,black,ww,smooth=True)
            xo=xc+side*.119
            h.cyl(tag+f'.BrakeDisc{side}_{yy}',(xo-side*.06,yy,r),(xo-side*.04,yy,r),r*.64,alloy,ww,n=56)
            h.ring(tag+f'.Rim{side}_{yy}',(xo,yy,r),r*.78,.012,alloy,ww,axis='x',segments=64)
            h.ring(tag+f'.Bead{side}_{yy}',(xo+side*.002,yy,r),r*.84,.006,black,ww,axis='x')
            h.transformed_box(tag+f'.Caliper{side}_{yy}',(xo-side*.027,yy+.18,r+.04),(.06,.075,.19),brake,ww,bevel=.012)
            for k in range(10):
                a=k*2*np.pi/10
                for delta in [-.035,.035]:
                    a1=a+delta;pts=[(xo,yy+.066*np.sin(a),r+.066*np.cos(a)),(xo,yy+r*.745*np.sin(a1+.08),r+r*.745*np.cos(a1+.08))]
                    h.pipe(tag+f'.Spoke{side}_{yy}_{k}_{delta}',pts,.011,alloy if k%2==0 else gun,ww,n=8)
            h.cyl(tag+f'.Hub{side}_{yy}',(xo-side*.007,yy,r),(xo+side*.012,yy,r),.071,gun,ww,n=32)
            for k in range(5):
                a=k*2*np.pi/5;h.ball(tag+f'.Lug{side}_{yy}_{k}',(xo+side*.014,yy+.048*np.sin(a),r+.048*np.cos(a)),(.009,.009,.009),alloy,ww)
            # Circumferential tread bands, subtle actual geometry.
            for off in [-.059,-.020,.020,.059]:h.ring(tag+f'.TreadBand{side}_{yy}_{off}',(xc+off,yy,r),r+.0007,.0018,dark,ww,axis='x',segments=72)
    # Floor and dark dashboard complete the view through the smoked windows.
    if not cabin:
        h.transformed_box(tag+'.Dash',(0,-.84,.70),(1.59,.27,.20),leather,roof,bevel=.04)
        for side in [-1,1]:h.transformed_box(tag+f'.InnerDoor{side}',(side*.82,.05,.59),(.06,2.0,.49),leather,roof,bevel=.02)
    # Simplified visible cabin for showroom models (no occupants).
    for side in [-1,1]:
        h.transformed_box(tag+f'.SeatCushion{side}',(side*.39,.18,.49),(.44,.50,.11),leather,roof,bevel=.046)
        h.transformed_box(tag+f'.SeatBack{side}',(side*.39,.40,.79),(.44,.13,.57),leather,roof,bevel=.04)
        h.ball(tag+f'.HeadRest{side}',(side*.39,.41,1.08),(.16,.07,.12),leather,roof)
    if cabin:
        # The large full-width deck under a closed car would block the seated camera.
        # Replace its cabin part with a hood and aft deck only.
        h.g.remove(tag+'.Body.UpperDeck')
        for sl,label in [(np.linspace(-half,-1.1,28),'HoodOnly'),(np.linspace(1.57,half,18),'DeckOnly')]:
            patch(tag+'.'+label,[[(x*float(width(y)),y,float(top(y))+.025*(1-x*x)) for x in np.linspace(-1,1,19)] for y in sl],paint,body)
        h.transformed_box(tag+'.CabinFloor',(0,.12,.23),(1.63,2.15,.07),leather,roof,bevel=.02)
        h.transformed_box(tag+'.Dashboard',(0,-.78,.75),(1.62,.34,.22),leather,roof,bevel=.065)
        glow=h.material(tag+'.CockpitGlow',(.04,.28,.36),.45,0,(.06,.54,.67))
        h.pipe(tag+'.DashLight',[(-.72,-.595,.822),(-.12,-.595,.84),(.72,-.595,.80)],.0035,glow,roof,n=10)
        h.transformed_box(tag+'.CenterConsole',(0,.06,.46),(.26,.86,.35),dark,roof,bevel=.03)
        h.transformed_box(tag+'.Display',(0,-.581,.91),(.43,.021,.18),dark,roof,bevel=.009)
        for i in range(5):h.transformed_box(tag+f'.DisplayBar{i}',(-.13+i*.065,-.566,.906),(.032,.002,.007+i*.009),glow,roof,bevel=.001)
        h.ring(tag+'.SteeringWheel',(-.39,-.46,.82),.156,.016,black,roof,axis='y')
        h.pipe(tag+'.SteeringSpokes',[(-.53,-.46,.82),(-.39,-.46,.82),(-.28,-.46,.87)],.018,dark,roof)
        h.transformed_box(tag+'.WheelHub',(-.39,-.46,.82),(.14,.05,.09),dark,roof,bevel=.02)
        # Usable passenger-side aperture: cut away the front-door area of the side panel.
        h.g.remove(tag+'.Body.Side1')
        side_poly=poly.difference(box(-.98,.30,.49,1.8));v,f=prism(side_poly,0,.025);v=np.c_[width(v[:,0])-.045*(1-v[:,1]/belt)+v[:,2],v[:,0],v[:,1]];m=trimesh.Trimesh(v,f,process=False);m.fix_normals();h.mesh(tag+'.Body.PassengerSideAperture',m,paint,body,smooth=True)
        door=h.group(tag+'.PassengerDoorPivot',root)
        # Construct in car coordinates then pivot the meshes around the hinge when animating.
        h.transformed_box(tag+'.PassengerDoor',(W/2-.008,-.255,.62),(.055,1.39,.64),paint,door,bevel=.032)
        h.transformed_box(tag+'.DoorInterior',(W/2-.046,-.24,.61),(.025,1.29,.55),leather,door,bevel=.026)
        h.pipe(tag+'.DoorPull',[(W/2-.087,-.46,.63),(W/2-.12,-.18,.63)],.022,dark,door)
        h.transformed_box(tag+'.DoorGlass',(W/2-.10,-.25,1.06),(.011,1.16,.40),glass,door,bevel=.008)
        return root,wheels,door,(W/2-.008,-.95,.62)
    return root,wheels,None,None
