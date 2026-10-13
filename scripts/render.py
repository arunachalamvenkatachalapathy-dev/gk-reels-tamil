"""Bank-driven bilingual English-first/Tamil-fallback renderer; no uploader."""
import os,json,asyncio,subprocess,shutil
"""Bilingual TNPSC layout proof: English first, Tamil fallback; no publishing."""
import sys,json,base64,math,html
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def b64(p):return base64.b64encode(p.read_bytes()).decode()
def esc(s):return html.escape(s)

ASSETS=str(ROOT/'assets')
BASE=str(ROOT)
def prepare_content(q):
    checked=json.loads((ROOT/'data/reviewed_ta.json').read_text(encoding='utf-8'))
    if q.get('id') not in checked:raise ValueError('Source-checked review required')
    content=dict(q);content.update(checked[q['id']])
    for field in ('question','question_en','explanation','explanation_en','source_url','source_label','source_label_en','memory_key','memory_key_en'):
        if not isinstance(content.get(field),str) or not content[field].strip():raise ValueError('Missing bilingual reviewed field: '+field)
    for field in ('options','options_en'):
        if len(content.get(field,[]))!=4 or any(not isinstance(x,str) or not x.strip() for x in content[field]):raise ValueError('Four bilingual factual options required')
    if not isinstance(content.get('correct_index'),int) or not 0<=content['correct_index']<4:raise ValueError('Invalid answer')
    content['question']=content.get('display_question',content['question'])
    return content

def get_audio_duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',path],text=True))



CTA_TA = "இலவச guide க்கு, follow செய்து gk snippets என்று கமெண்ட் செய்யுங்கள்."
CTA_EN = "Follow and comment GK SNIPPETS for a free guide."

def timing_plan(q_duration, answer_duration, why_duration, cta_duration=0, max_duration=15.5):
    if min(q_duration, answer_duration, why_duration) <= 0:
        raise ValueError('All speech segments must exist')
    timer_start = .15 + q_duration + .15
    reveal = timer_start + 3.0
    why_start = reveal + answer_duration + .18
    cta_start = why_start + why_duration + .18
    total = max(12.0, (cta_start + cta_duration if cta_duration else why_start + why_duration) + .65)
    # Never truncate speech or accelerate it until it is unintelligible.
    if total > max_duration:
        raise ValueError(f'{total:.2f}s is too long: shorten editorial wording before publishing')
    return {'timer_start':timer_start,'reveal':reveal,'why_start':why_start,'total':total,'cta_start':cta_start if cta_duration else None}


def studio_html(q,t,plan):
 EN=q["question_en"];TA=q["question"];OPTS=list(zip(q["options_en"],q["options"]))
 reveal=t>=plan["reveal"];why=t>=plan["why_start"];cta=plan.get("cta_start") is not None and t>=plan["cta_start"]
 styles=f'''@font-face{{font-family:Quiz;src:url(data:font/ttf;base64,{b64(ROOT/'assets/fonts/3-QuizSans.ttf')});font-weight:400}}@font-face{{font-family:Tamil;src:url(data:font/ttf;base64,{b64(ROOT/'assets/fonts/5-QuizTamil.ttf')});font-weight:100 900}}*{{box-sizing:border-box}}body{{margin:0;width:1080px;height:1920px;background:#080f1e;color:#f5f6fa;font-family:Quiz,Arial;overflow:hidden}}.glow{{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 0%,#14264d,transparent 55%),radial-gradient(ellipse at 50% 100%,#f5a62325,transparent 55%)}}main{{position:absolute;top:195px;left:72px;width:824px}}header{{display:flex;align-items:center;gap:16px;font-size:27px;font-weight:700}}header img{{width:60px;height:60px;border-radius:15px}}header b{{margin-left:auto;font-family:Tamil;font-size:24px;color:#f5b947}}.kicker{{font-size:27px;color:#f5b947;letter-spacing:1px;margin-top:32px;margin-bottom:20px}}h1{{font-size:52px;line-height:1.22;font-weight:700;letter-spacing:0;margin:0 0 20px}}.ta{{font-family:Tamil;font-size:34px;line-height:1.55;font-weight:500;color:#c8d2df;letter-spacing:0}}.question-ta{{font-size:30px;margin-bottom:22px}}.choices{{display:grid;gap:14px}}.choice{{display:flex;align-items:center;gap:22px;border:2px solid #354660;background:#14253f;padding:12px 24px;border-radius:22px;min-height:110px}}.letter{{background:#f5b947;color:#080f1e;width:47px;height:47px;border-radius:11px;font:700 28px Arial;display:flex;align-items:center;justify-content:center;flex-shrink:0}}.en-option{{font-size:42px;line-height:1.2;font-weight:700}}.choice .ta{{font-size:30px;margin-top:5px}}.correct{{background:#d6f5e5;color:#124e37;border-color:#16a46b}}.correct .ta{{color:#24634e}}.wrong{{opacity:.42}}.timer{{border-top:2px solid #354660;margin-top:20px;padding-top:16px;display:flex;justify-content:space-between;align-items:center}}.timer strong{{font-size:30px;color:#f5b947;line-height:1.4;display:block}}.timer .ta{{font-size:26px}}.ring{{border:9px solid #f5b947;border-radius:50%;width:130px;height:130px;text-align:center;line-height:112px;font:700 70px/112px Arial}}.answer{{font-size:76px;color:#f5b947;font-weight:700;line-height:1.3}}.answer-ta{{font-size:44px;color:#f5b947}}.memory{{background:#d6f5e5;color:#124e37;border-radius:20px;padding:24px;margin-top:30px;font-size:37px;line-height:1.3}}.memory .ta{{color:#24634e;font-size:29px}}.explain{{font-size:43px;line-height:1.35;margin:32px 0 16px}}.source{{font-size:25px;color:#b7c6db;margin-top:24px;line-height:1.45}}.source .ta{{font-size:24px}}.cta{{background:#f5b947;color:#182435;border-radius:16px;margin-top:36px;padding:24px;font-size:35px;line-height:1.3}}.cta .ta{{color:#182435;font-size:27px}}.preview{{position:absolute;left:72px;bottom:285px;font:26px Arial;color:#b7c6db}}'''
 if cta:
  inner=f'<div class="kicker">FREE GK GUIDE</div><div class="answer" style="font-size:62px;margin-top:100px">GK SNIPPETS</div><div class="cta">{esc(CTA_EN)}<div class="ta">{esc(CTA_TA)}</div></div><div class="source">Comment keyword: gk snippets</div>'
 elif why:
  inner=f'<div class="kicker">THE ANSWER, EXPLAINED</div><div class="answer">{esc(q["options_en"][q["correct_index"]])}</div><div class="ta answer-ta">{esc(q["options"][q["correct_index"]])}</div><div class="memory">{esc(q["memory_key_en"])}<div class="ta">{esc(q["memory_key"])}</div></div><div class="explain">{esc(q["explanation_en"])}</div><div class="ta">{esc(q["explanation"])}</div><div class="source">{esc(q["source_label_en"])}</div><div class="cta">One question. One reason. Every day.<div class="ta">தினமும் ஒரு கேள்வி. விடையும் காரணமும்.</div></div>'
 else:
  options=''.join(f'<div class="choice {"correct" if reveal and i==q["correct_index"] else ("wrong" if reveal else "")}"><div class="letter">{"ABCD"[i]}</div><div><div class="en-option">{esc(en)}</div><div class="ta">{esc(ta)}</div></div></div>' for i,(en,ta) in enumerate(OPTS))
  inner=f'<div class="kicker">CHOOSE YOUR ANSWER</div><h1>{esc(EN)}</h1><div class="ta question-ta">{esc(TA)}</div><div class="choices">{options}</div><div class="timer"><div><strong>{"THE ANSWER" if reveal else ("LOCK IT IN" if t>=plan["timer_start"] else "READ. THEN CHOOSE.")}</strong><div class="ta">{"சரியான விடை" if reveal else "விடையை தேர்வு செய்க"}</div></div><div class="ring">{"✓" if reveal else max(1,3-int(t-plan["timer_start"])) if t>=plan["timer_start"] else "?"}</div></div>'
 return f'<meta charset="utf-8"><style>{styles}</style><div class="glow"></div><main><header><img src="data:image/jpeg;base64,{b64(ROOT/"assets/logo.jpg")}"><span>GK SNIPPETS TAMIL</span><b>{esc(q.get("verified_topic",""))}</b></header>{inner}</main>'
def fit_safe_area(page):
    # Preserve text. Fit the whole card to the Shorts safe area before capture.
    bottom=page.evaluate("() => Math.max(...[...document.querySelectorAll('main *')].map(e=>e.getBoundingClientRect().bottom))")
    scale=min(1.0,(1470-195)/max(1,bottom-195))
    if scale < .68:raise ValueError('Reviewed content too long for readable safe-area fit')
    page.evaluate("s => {const m=document.querySelector('main');m.style.transformOrigin='top left';m.style.transform='scale('+s+')'}",scale)
    return scale

def render_video(question_obj, accent, out_mp4, tmp_dir, bg_music=None, day=1, slot=1, topic_name=None, viral_badge=None, speech_paths=None, include_cta=False, review_only=True, max_duration=15.5):
    from pathlib import Path
    import math
    q=prepare_content(question_obj)
    d=Path(tmp_dir);d.mkdir(parents=True,exist_ok=True)
    if include_cta and not review_only:
        raise ValueError('Guide fulfillment must be resolved before a live CTA release')
    if speech_paths is not None:
        paths=list(map(str,speech_paths))
        if len(paths)!=(4 if include_cta else 3):
            raise ValueError('Supply question, answer, explanation and optional CTA speech files')
    else:
        raise ValueError('Approved Charon speech files required; no fallback voice')
    lengths=[get_audio_duration(p) for p in paths]
    plan=timing_plan(*lengths[:3],cta_duration=lengths[3] if include_cta else 0,max_duration=max_duration)
    fps=2
    with sync_playwright() as p:
        b=p.chromium.launch(args=['--no-sandbox']);page=b.new_page(viewport={'width':1080,'height':1920});cache={}
        for i in range(math.ceil(plan['total']*fps)):
            markup=studio_html(q,i/fps,plan)
            target=d/f'{i:04d}.png'
            if markup in cache:
                shutil.copyfile(cache[markup],target);continue
            page.set_content(markup);page.evaluate('document.fonts.ready');fit_safe_area(page)
            if i in (0,math.ceil(plan['why_start']*fps)+1, math.ceil((plan.get('cta_start') or 0)*fps)+1):
                overflow=page.evaluate("() => [...document.querySelectorAll('main *')].some(e=>{let r=e.getBoundingClientRect();return r.right>900||r.bottom>1480})")
                if overflow:raise ValueError('Shorts safe-area overflow; shorten reviewed wording')
            page.screenshot(path=str(target));cache[markup]=target
        b.close()
    music=bg_music if bg_music and os.path.isfile(bg_music) else os.path.join(ASSETS,'audio','slot1_one_answer_left.mp3')
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(fps),'-i',str(d/'%04d.png')]
    for path in paths:cmd+=['-i',path]
    cmd+=['-stream_loop','-1','-i',music]
    f=[f'[1:a]adelay=150:all=1[q]',f'[2:a]adelay={round(plan["reveal"]*1000)}:all=1[a]',f'[3:a]adelay={round(plan["why_start"]*1000)}:all=1[w]']
    mix=['q','a','w']
    if include_cta:
        f.append(f'[4:a]adelay={round(plan["cta_start"]*1000)}:all=1[c]')
        mix.append('c')
    music_index=len(paths)+1
    f.append(f'[{music_index}:a]atrim=duration={plan["total"]},volume=0.10,afade=t=out:st={plan["total"]-.6}:d=0.6[bed]')
    mix.append('bed')
    for i in range(3):
        f.append(f'sine=frequency=1000:duration=0.08,volume=0.12,afade=t=out:d=0.08,adelay={round((plan["timer_start"]+i)*1000)}:all=1[t{i}]')
        mix.append(f't{i}')
    f.append(''.join('['+x+']' for x in mix)+f'amix=inputs={len(mix)}:duration=longest:normalize=0,apad,alimiter=limit=0.95[mix]')
    cmd+=['-filter_complex',';'.join(f),'-map','0:v','-map','[mix]','-t',str(plan['total']),'-vf','fps=30,format=yuv420p','-c:v','libx264','-crf','18','-preset','fast','-c:a','aac','-b:a','192k','-movflags','+faststart',out_mp4]
    subprocess.run(cmd,check=True)
    (d/'timing.json').write_text(json.dumps(dict(plan,source_url=q['source_url'],question_id=q['id'],style='studio-arena'),indent=2))
    print(f"Studio arena ta: {plan['total']:.2f}s")
