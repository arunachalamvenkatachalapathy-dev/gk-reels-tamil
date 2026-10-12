"""Tamil-only renderer and reviewed-video publisher. Manual and fail-closed."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANNEL = 'UC5ZLfNHUI4z92IW69KVTGxg'

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)

def checked_question(question_id):
    bank = load(ROOT / 'data/questions_ta.json')
    reviews = load(ROOT / 'data/reviewed_ta.json')
    matches = [q for q in bank if q.get('id') == question_id]
    if len(matches) != 1 or question_id not in reviews:
        raise ValueError('One unique source-reviewed Tamil question required')
    q = matches[0]
    review = reviews[question_id]
    if review.get('release_verdict') != 'verified' or not review.get('source_url'):
        raise ValueError('Release verdict and factual source required')
    if not review.get('scan_verified') or not review.get('semantic_dedup_verified'):
        raise ValueError('Scan fidelity and semantic dedup gates required')
    return q

def verify_release(approval, video, metadata, question_id):
    digest = hashlib.sha256(Path(video).read_bytes()).hexdigest()
    if approval.get('channel_id') != CHANNEL:
        raise ValueError('Approval must name exact Tamil channel')
    if approval.get('question_id') != question_id or approval.get('video_sha256') != digest:
        raise ValueError('Approval must match exact video and question')
    if approval.get('metadata') != metadata:
        raise ValueError('Approval must match exact title and description')
    if not approval.get('user_message_id') or not approval.get('approved_at'):
        raise ValueError('Original authenticated user approval evidence required')
    if metadata.get('channel_id') != CHANNEL:
        raise ValueError('Wrong destination channel')
    if not isinstance(metadata.get('title'), str) or not 0 < len(metadata['title']) <= 100:
        raise ValueError('Title must be 1-100 characters')
    if not isinstance(metadata.get('description'), str) or len(metadata['description']) > 5000:
        raise ValueError('Description must be at most 5000 characters')
    return digest

def publish(video, metadata_path, approval_path, state_path, question_id):
    checked_question(question_id)
    metadata, approval = load(metadata_path), load(approval_path)
    digest = verify_release(approval, video, metadata, question_id)
    state = load(state_path) if Path(state_path).exists() else {'publications': {}}
    ledger = state.setdefault('publications', {})
    if question_id in ledger:
        raise RuntimeError('Publication already reserved: reconcile receipt before retry')
    ledger[question_id] = {'status': 'pending', 'video_sha256': digest,
                           'channel_id': CHANNEL, 'metadata': metadata}
    write_atomic(state_path, state)
    # Pending survives failure: do not retry an uncertain external upload.
    from upload_youtube import upload_short
    receipt = upload_short(str(video), metadata['title'], metadata['description'], metadata.get('tags'))
    ledger[question_id].update(status='published', youtube_id=receipt)
    write_atomic(state_path, state)
    print(json.dumps({'youtube_id': receipt, 'question_id': question_id}))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['render', 'publish'], default='render')
    parser.add_argument('--question-id', required=True)
    parser.add_argument('--video', default=str(ROOT / 'output/tamil-preview.mp4'))
    parser.add_argument('--metadata')
    parser.add_argument('--approval')
    parser.add_argument('--state', default=str(ROOT / 'output/publish-state.json'))
    args = parser.parse_args()
    if args.mode == 'render':
        q = checked_question(args.question_id)
        from render import render_video
        Path(args.video).parent.mkdir(parents=True, exist_ok=True)
        render_video(q, '#f5b947', args.video, str(ROOT / 'output/render-temp'))
        print('Review-only render complete. No upload.')
    else:
        if os.environ.get('PUBLISHING_ENABLED') != 'true':
            raise RuntimeError('Publishing disabled')
        if not args.metadata or not args.approval:
            raise ValueError('Reviewed metadata and owner approval files required')
        publish(args.video, args.metadata, args.approval, args.state, args.question_id)

if __name__ == '__main__':
    main()
