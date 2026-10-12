"""Music-only layout proof. Never claims speech generation succeeded."""
import json,sys,math,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render import prepare_content,studio_html
q=prepare_content(json.loads((ROOT/'data/questions_ta.json').read_text())[0])
plan={'timer_start':4.0,'reveal':7.0,'why_start':8.5,'total':13.0}
out=Path('/tmp/tamil-visual');out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(args=['--no-sandbox']);page=b.new_page(viewport={'width':1080,'height':1920})
 for i in range(195):
  html=studio_html(q,i/15,plan)
  html=html.replace('</main>','</main><div style="position:absolute;bottom:300px;left:72px;font:26px Arial;color:#b7c6db">VISUAL DRY-RUN · MUSIC ONLY · NO VOICE</div>')
  page.set_content(html);page.evaluate('document.fonts.ready')
  if i in [0,100,150]:
   info=page.evaluate("() => [...document.querySelectorAll('main *')].filter(e=>{let r=e.getBoundingClientRect();return r.right>900||r.bottom>1480}).map(e=>({text:e.innerText,right:e.getBoundingClientRect().right,bottom:e.getBoundingClientRect().bottom}))")
   print('overflow',i,info)
  page.screenshot(path=str(out/f'{i:04d}.png'))
 b.close()
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-framerate','15','-i',str(out/'%04d.png'),'-stream_loop','-1','-i',str(ROOT/'assets/audio/slot1_one_answer_left.mp3'),'-t','13','-vf','fps=30,format=yuv420p','-af','volume=0.05,afade=t=out:st=12.4:d=0.6','-c:v','libx264','-crf','23','-preset','fast','-c:a','aac','-movflags','+faststart','/downloads/tamil-visual-dry-run.mp4'],check=True)
