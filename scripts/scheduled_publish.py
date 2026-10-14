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

def choose_dispatch(queue,state):
    published=set(state.get('published_ids',[]))
    published.update(x.get('question_id') for x in state.get('slots',{}).values() if x.get('status') in ('pending','ambiguous','published'))
    return next((a for a in queue if a.get('slot_key','').startswith('manual:') and a.get('question_id') not in published),None)

def dispatch_mode(event,mode=None):
    if event!='workflow_dispatch':return 'scheduled'
    mode=mode or 'manual'
    if mode not in ('manual','scheduled','catch_up'):raise ValueError('Invalid dispatch mode')
    return mode

def select_run_slot(now,config,state,mode,catch_up_slot=None):
    if mode=='scheduled':return selection(now,config,state)
    local=now.astimezone(IST)
    if mode=='catch_up':
        if catch_up_slot not in config['slots']:raise ValueError('Invalid catch-up slot')
        name=catch_up_slot;h,m=map(int,config['slots'][name].split(':'));opening=local.replace(hour=h,minute=m,second=0,microsecond=0);key=f'{local.date()}:{name}'
        if opening>local:raise ValueError('Catch-up slot has not opened')
        return {'key':key,'slot':name,'opens_at':opening.isoformat(),'drift_seconds':round((local-opening).total_seconds())}
    if mode=='manual':return {'key':f'manual:{local.date()}','slot':'manual','opens_at':now.isoformat(),'drift_seconds':0}
    raise ValueError('Invalid dispatch mode')

def verify_asset(a,config):
    if a.get('channel_id')!=config['channel_id']:raise ValueError('Wrong Tamil channel')
    ap=a.get('approval',{});md=a.get('metadata',{})
    if config.get('per_video_approval_required',True):
        for field in ('user_message_id','approved_at'):
            if not ap.get(field):raise ValueError('Original per-video approval required')
        if ap.get('question_id')!=a.get('question_id') or ap.get('video_sha256')!=a.get('sha256') or ap.get('metadata')!=md or ap.get('channel_id')!=config['channel_id']:
            raise ValueError('Approval must match exact question, video, metadata and destination')
    if not config.get('per_video_approval_required',True):
        quality=a.get('quality_review',{})
        if not ap and (quality.get('voice')!='Charon' or quality.get('audio_language')!='Tamil' or not quality.get('visual_verified')):
            raise ValueError('Automatic asset requires Charon Tamil and visual review')
    if md.get('channel_id')!=config['channel_id'] or not 0<len(md.get('title',''))<=100 or len(md.get('description',''))>5000:raise ValueError('Invalid metadata')
    if not a.get('repo_path') and not a.get('download_url','').startswith('https://'):raise ValueError('HTTPS ready asset or repo_path required')
    return md

def persist(state_dir,state,note):
    save(state_dir/'state.json',state)
    for args in [('add','state.json'),('commit','-m',note),('push','origin','HEAD:tamil-publication-state')]:
        subprocess.run(['git','-C',str(state_dir),*args],check=True,stdout=subprocess.DEVNULL)

def main():
    config=load(ROOT/'data/automation_config.json');sd=Path(os.environ['PUBLICATION_STATE_DIR']);state=load(sd/'state.json')
    now=datetime.now(timezone.utc);mode=dispatch_mode(os.getenv('GITHUB_EVENT_NAME'),os.getenv('DISPATCH_MODE'));slot=select_run_slot(now,config,state,mode,os.getenv('CATCH_UP_SLOT'))
    state.setdefault('checks',[]).append({'at':now.isoformat(),'run_id':os.getenv('GITHUB_RUN_ID'),'scheduled_event':os.getenv('GITHUB_EVENT_NAME'),'slot':slot,'enabled':config['publish_enabled'],'dispatch_mode':mode})
    state['checks']=state['checks'][-500:]
    if not slot:save(sd/'state.json',state);print('No active IST slot');return
    previous=state.setdefault('slots',{}).get(slot['key'],{})
    if previous.get('status') in ('pending','ambiguous'):
        persist(sd,state,'Record blocked pending publication');raise RuntimeError('Reconcile pending receipt before retry')
    queue=load(ROOT/config['ready_queue'])
    asset=choose_dispatch(queue,state) if mode=='manual' else choose(queue,slot,state)
    if not config['publish_enabled'] or not asset:
        persist(sd,state,'Record Tamil gated slot and drift');print('Slot checked; release disabled or no approved ready asset');return
    metadata=verify_asset(asset,config)
    from run_pipeline import checked_question
    checked_question(asset['question_id'])
    for name in ('YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN'):
        if not os.getenv(name):raise RuntimeError('Missing repository secret: '+name)
    os.environ['YT_CHANNEL_ID']=config['channel_id']
    from upload_youtube import get_youtube_client
    from meta_publish import preflight, public_video, publish_reel, publish_facebook_reel
    get_youtube_client()  # YouTube is the active destination; verify before uploading.
    destinations={'youtube': True, 'instagram': False, 'facebook': False}
    caption=metadata['description']
    meta_ready=all(os.getenv(k) for k in ('IG_ACCESS_TOKEN','IG_USER_ID','FB_PAGE_ID'))
    if meta_ready:
        destinations=preflight()
        destinations={'youtube': True, 'instagram': True, 'facebook': True}
    public_bytes=None
    if meta_ready: public_bytes=public_video(asset.get('download_url',''),asset['sha256'])
    if asset.get('repo_path'):
        video=ROOT/asset['repo_path']
        if not video.is_file():raise ValueError('Ready asset file missing: '+asset['repo_path'])
    else:
        video=ROOT/'output/scheduled.mp4';video.parent.mkdir(exist_ok=True)
        if public_bytes is None:
            request=urllib.request.Request(asset['download_url'])
            with urllib.request.urlopen(request,timeout=90) as response:public_bytes=response.read()
        video.write_bytes(public_bytes)
    if hashlib.sha256(video.read_bytes()).hexdigest()!=asset['sha256']:raise ValueError('Ready video hash mismatch')
    state['slots'][slot['key']]=dict(slot,status='pending',question_id=asset['question_id'],sha256=asset['sha256'],metadata=metadata,destinations=destinations,run_id=os.getenv('GITHUB_RUN_ID'),receipts={})
    persist(sd,state,'Reserve exact Tamil asset before external upload')
    from upload_youtube import upload_short
    entry=state['slots'][slot['key']]
    def checkpoint(platform,details):
        entry['receipts'].setdefault(platform,{}).update(details)
        persist(sd,state,'Record Tamil '+platform+' upload checkpoint')
    publishers=[('youtube',lambda: {'id':upload_short(str(video),metadata['title'],metadata['description'],metadata.get('tags')),'status':'published'})]
    if destinations.get('instagram'):
        publishers.append(('instagram',lambda:publish_reel(asset['download_url'],caption,lambda d:checkpoint('instagram',d))))
    if destinations.get('facebook'):
        publishers.append(('facebook',lambda:publish_facebook_reel(str(video),metadata['title'],metadata['description'],lambda d:checkpoint('facebook',d))))
    for platform,publish in publishers:
        checkpoint(platform,{'status':'pending','phase':'submitting'})
        try:
            receipt=publish()
            if not receipt.get('id') or receipt.get('status')!='published':
                raise RuntimeError('Confirmed publication receipt missing')
        except Exception:
            entry['status']='ambiguous'
            if entry['receipts'][platform].get('status')!='published':
                entry['receipts'][platform]['status']='ambiguous'
            persist(sd,state,'Hold uncertain Tamil '+platform+' upload for reconciliation')
            raise RuntimeError('Tamil '+platform+' publication needs reconciliation; no automatic retry') from None
        checkpoint(platform,dict(receipt,published_at=datetime.now(timezone.utc).isoformat()))
        if platform=='youtube':entry['youtube_id']=receipt['id']
    entry.update(status='published',published_at=datetime.now(timezone.utc).isoformat())
    state.setdefault('published_ids',[]).append(asset['question_id'])
    persist(sd,state,'Record confirmed Tamil cross-platform publication receipts')
    print(json.dumps({'question_id':asset['question_id'],'receipts':entry['receipts'],'drift_seconds':slot['drift_seconds']}))
if __name__=='__main__':main()
