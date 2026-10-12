"""Check bilingual bank structure; never grant factual or publishing clearance."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def validate(rows, expected_count=None):
    if not isinstance(rows, list):
        raise ValueError('Bank must be a list')
    ids = [q.get('id') for q in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('Nonempty unique question IDs required')
    if expected_count is not None and len(rows) != expected_count:
        raise ValueError('Question count mismatch')
    for q in rows:
        for field in ('question', 'question_en', 'answer', 'answer_en'):
            if not isinstance(q.get(field), str) or not q[field].strip():
                raise ValueError('Missing bilingual text: ' + q['id'])
        for field in ('options', 'options_en'):
            choices = q.get(field)
            if not isinstance(choices, list) or len(choices) != 4 or any(not isinstance(v, str) or not v.strip() for v in choices):
                raise ValueError('Four nonempty options required: ' + q['id'])
        key = q.get('correct_index')
        if type(key) is not int or not 0 <= key < 4:
            raise ValueError('Invalid key: ' + q['id'])
        if q['answer'] != q['options'][key] or q['answer_en'] != q['options_en'][key]:
            raise ValueError('Answer-option mismatch: ' + q['id'])
    return len(rows)

if __name__ == '__main__':
    status = json.loads((ROOT / 'data/bank_release_status.json').read_text())
    rows = json.loads((ROOT / status['checkpoint_file']).read_text())
    print('Structural check only:', validate(rows, status['question_count']), 'questions')
    print('Release final:', status['release_final'])
