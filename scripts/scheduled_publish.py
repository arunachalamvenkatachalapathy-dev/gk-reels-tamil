"""Tamil ready-asset publisher. Persist reservation before any upload."""
import hashlib,json,os,subprocess,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IST=timezone(timedelta(hours=5,minutes=30))
def load(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def selection(now,config,state):
    local=now.astimezone(IST)
    for name,clock in config['slots'].items():
        h,m=map(int,clock.split(':'));opening=local.replace(hour=h,minute=m,second=0,microsecond=0)
        lag=(local-opening).total_seconds();key=f'{local.date()}:{name}'
        if 0<=lag<config['window_minutes']*60 and state.get('slots',{}).get(key,{}).get('status')!='published':
            return {'key':key,'slot':name,'opens_at':opening.isoformat(),'drift_seconds':round(lag)}
    return None

def choose(queue,slot,state):
    published=set(state.get('published_ids',[]))
    published.update(x.get('question_id') for x in state.get('slots',{}).values() if x.get('status') in ('pending','ambiguous','published'))
    return next((a for a in queue if a.get('slot_key')==slot['key'] and a.get('question_id') not in published),None)

def verify_asset(a,config):
    if a.get('channel_id')!=config['channel_id']:raise ValueError('Wrong Tamil channel')
    ap=a.get('approval',{});md=a.get('metadata',{})
    for field in ('user_message_id','approved_at'):
        if not ap.get(field):raise ValueError('Original per-video approval required')
    if ap.get('question_id')!=a.get('question_id') or ap.get('video_sha256')!=a.get('sha256') or ap.get('metadata')!=md or ap.get('channel_id')!=config['channel_id']:
        raise ValueError('Approval must match exact question, video, metadata and destination')
    if md.get('channel_id')!=config['channel_id'] or not 0<len(md.get('title',''))<=100 or len(md.get('description',''))>5000:raise ValueError('Invalid metadata')
    if not a.get('download_url','').startswith('https://'):raise ValueError('HTTPS ready asset required')
    return md

def persist(state_dir,state,note):
    save(state_dir/'state.json',state)
    for args in [('add','state.json'),('commit','-m',note),('push','origin','HEAD:tamil-publication-state')]:
        subprocess.run(['git','-C',str(state_dir),*args],check=True,stdout=subprocess.DEVNULL)

def main():
    config=load(ROOT/'data/automation_config.json');sd=Path(os.environ['PUBLICATION_STATE_DIR']);state=load(sd/'state.json')
    now=datetime.now(timezone.utc);slot=selection(now,config,state)
    state.setdefault('checks',[]).append({'at':now.isoformat(),'run_id':os.getenv('GITHUB_RUN_ID'),'scheduled_event':os.getenv('GITHUB_EVENT_NAME'),'slot':slot,'enabled':config['publish_enabled']})
    state['checks']=state['checks'][-500:]
    if not slot:save(sd/'state.json',state);print('No active IST slot');return
    previous=state.setdefault('slots',{}).get(slot['key'],{})
    if previous.get('status') in ('pending','ambiguous'):
        persist(sd,state,'Record blocked pending publication');raise RuntimeError('Reconcile pending receipt before retry')
    asset=choose(load(ROOT/config['ready_queue']),slot,state)
    if not config['publish_enabled'] or not asset:
        persist(sd,state,'Record Tamil gated slot and drift');print('Slot checked; release disabled or no approved ready asset');return
    metadata=verify_asset(asset,config)
    from run_pipeline import checked_question
    checked_question(asset['question_id'])
    for name in ('YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN'):
        if not os.getenv(name):raise RuntimeError('Missing repository secret: '+name)
    os.environ['YT_CHANNEL_ID']=config['channel_id']
    video=ROOT/'output/scheduled.mp4';video.parent.mkdir(exist_ok=True)
    with urllib.request.urlopen(asset['download_url'],timeout=90) as r:video.write_bytes(r.read())
    if hashlib.sha256(video.read_bytes()).hexdigest()!=asset['sha256']:raise ValueError('Ready video hash mismatch')
    state['slots'][slot['key']]=dict(slot,status='pending',question_id=asset['question_id'],sha256=asset['sha256'],run_id=os.getenv('GITHUB_RUN_ID'))
    persist(sd,state,'Reserve exact Tamil asset before external upload')
    from upload_youtube import upload_short
    try:receipt=upload_short(str(video),metadata['title'],metadata['description'],metadata.get('tags'))
    except Exception:
        state['slots'][slot['key']]['status']='ambiguous';persist(sd,state,'Hold uncertain Tamil upload for reconciliation');raise
    state['slots'][slot['key']].update(status='published',youtube_id=receipt,published_at=datetime.now(timezone.utc).isoformat())
    state.setdefault('published_ids',[]).append(asset['question_id']);persist(sd,state,'Record confirmed Tamil publication receipt')
    print(json.dumps({'question_id':asset['question_id'],'youtube_id':receipt,'drift_seconds':slot['drift_seconds']}))
if __name__=='__main__':main()
