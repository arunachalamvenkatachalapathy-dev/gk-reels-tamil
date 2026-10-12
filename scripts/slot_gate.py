"""IST slot planning only. No network or publishing side effects."""
from datetime import datetime, time, timedelta, timezone
IST = timezone(timedelta(hours=5, minutes=30))

def due_slot(now, state, slot_times):
    """Earliest opened, unfinished slot for this IST date. No backfill."""
    if now.tzinfo is None:
        raise ValueError('Timezone-aware now required')
    local = now.astimezone(IST)
    slots = []
    for name in ('morning', 'afternoon'):
        raw = slot_times.get(name)
        if not raw:
            raise ValueError('Both slot times require owner confirmation')
        try:
            opening = time.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError('Slots must be HH:MM') from exc
        if opening.tzinfo is not None or opening.second or opening.microsecond:
            raise ValueError('Slots must be HH:MM in IST')
        slots.append((opening, name))
    if slots[0][0] >= slots[1][0]:
        raise ValueError('Morning must open before afternoon')
    ledger = state.get('slots', {})
    for opening, name in sorted(slots):
        key = f'{local.date().isoformat()}:{name}'
        status = ledger.get(key, {}).get('status')
        if status in ('pending', 'ambiguous'):
            # A possibly completed external upload must be reconciled, not retried.
            raise RuntimeError('Reconcile pending external publication: ' + key)
        if local.time().replace(tzinfo=None) >= opening and status != 'published':
            return {'key': key, 'date': local.date().isoformat(), 'slot': name,
                    'opens_at': f'{opening.hour:02}:{opening.minute:02}'}
    return None

def reserve(state, selection, question_id):
    """Reserve the same id before any later external call; persist atomically."""
    ledger = state.setdefault('slots', {})
    key = selection['key']
    if key in ledger and ledger[key].get('status') in ('published', 'pending', 'ambiguous'):
        raise RuntimeError('Slot already reserved: ' + key)
    ledger[key] = dict(selection, question_id=question_id, status='pending', destinations={})
    return ledger[key]

def confirm_published(state, key, expected_destinations):
    item = state['slots'][key]
    if not expected_destinations or any(not item['destinations'].get(d, {}).get('id') for d in expected_destinations):
        raise RuntimeError('Publication receipts required before marking a slot complete')
    item['status'] = 'published'
    state.setdefault('published_ids', []).append(item['question_id'])
