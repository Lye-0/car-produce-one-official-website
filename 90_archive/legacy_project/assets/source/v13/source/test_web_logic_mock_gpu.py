"""UI and actual GLB camera decoding test. GPU calls are mocked because WebGL is disabled here.
This is NOT a visual renderer test. Never report it as one.
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import numpy as np,json,time
root=Path(__file__).resolve().parents[1];web=root/'web';report={'kind':'UI / GLB animation mathematical test with mocked GPU; not a WebGL visual test','checks':[]}
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=__import__('os').environ.get('CHROMIUM_PATH') or None,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=b.new_page(viewport={'width':1440,'height':900});errs=[];page.on('pageerror',lambda e:errs.append(str(e)))
 html=(web/'index.html').read_text().replace('<link rel="stylesheet" href="style.css">','<style>'+(web/'style.css').read_text()+'</style>').replace('<script type="module" src="player.js"></script>','')
 page.set_content(html)
 page.evaluate('''()=>{
 const original=HTMLCanvasElement.prototype.getContext;
 const fake=new Proxy({}, {get:(o,k)=>{if(k.startsWith('create'))return ()=>({});if(k==='getShaderParameter'||k==='getProgramParameter')return ()=>true;if(k==='getUniformLocation')return ()=>({});if(k==='getShaderInfoLog'||k==='getProgramInfoLog')return ()=>'';if(k.toUpperCase()===k)return 1;return ()=>{};}});
 HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl2'?fake:original.call(this,type,...args);};
}''')
 js=(web/'player.js').read_text();js=js[:js.index('try{const response=await fetch')]
 page.add_script_tag(type='module',content=js);page.wait_for_timeout(100)
 page.locator('#localfile').set_input_files(str(root/'CAR_PRODUCE_ONE_ANIMATED_v13.glb'))
 try:page.wait_for_function('window.CPO?.ready()',timeout=120000)
 except Exception:
  print(page.locator('#error').inner_text(),errs,flush=True);raise
 print('LOADED mock GL pipeline',page.evaluate('CPO.last'),flush=True)
 data=np.load(root/'animation/camera_samples.npz')
 for t in [0,12.6,14.7,19.8,22.5,24,34.2,36,43.2,52.5,56.7,60,67.5,72,77.5,81,84,87.3,89,90]:
  page.evaluate('(t)=>{CPO.state.sway=false;CPO.seek(t/90);}',t);page.wait_for_timeout(120)
  actual=page.evaluate('CPO.last.sourceEye');expected=data['source_position'][int(round(t*30))];err=float(np.linalg.norm(np.array(actual)-expected));report['checks'].append({'name':f'actual GLB JS vs source camera at {t}s','passed':err<1e-4,'error_m':err})
 page.wait_for_timeout(200)
 report['checks'].append({'name':'HTML handoff visible at end','passed':page.evaluate("getComputedStyle(document.getElementById('handoff')).opacity==='1'")})
 page.evaluate("CPO.seek(.98)");page.wait_for_timeout(300)
 rect=page.locator('.screenmatch img').bounding_box();report['checks'].append({'name':'matched screen image covers desktop viewport','passed':rect['width']>1000 and rect['height']>650,'rect':rect})
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(350)
 rect=page.locator('.screenmatch img').bounding_box();report['checks'].append({'name':'portrait handoff projects actual LCD','passed':rect['width']>390 and rect['height']>500,'rect':rect})
 page.locator('#reset').click();page.wait_for_timeout(120);report['checks'].append({'name':'Reset enters idle','passed':page.evaluate('CPO.state.idle && CPO.state.p<.001')})
 page.locator('#play').click();page.wait_for_timeout(500);report['checks'].append({'name':'Playback advances master','passed':page.evaluate('CPO.state.playing && CPO.state.p>0')})
 page.locator('#play').click();a=page.evaluate('CPO.state.p');page.wait_for_timeout(150);c=page.evaluate('CPO.state.p');report['checks'].append({'name':'Pause retains time','passed':abs(a-c)<1e-5})
 report['page_errors']=errs;report['checks'].append({'name':'No JavaScript errors','passed':not errs});report['passed']=sum(x['passed'] for x in report['checks']);report['failed']=sum(not x['passed'] for x in report['checks']);(root/'source/web_logic_test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report),flush=True);b.close()
