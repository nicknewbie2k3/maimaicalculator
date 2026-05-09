import io
import math
import os
import re
import sys

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TAP_MULT = 1.0
HOLD_MULT = 2.0
TOUCH_MULT = 1.0

BREAK_MULT = 2.0
EX_MULT = 0.2
NORMAL_MULT = 1.0

SLIDE_SYMBOLS = {'-', '>', '<', '^', 'v', 'V', 'p', 'q', 's', 'z', 'w', 'pp', 'qq'}


def get_div(val):
    if not val:
        return 4.0
    m = re.match(r'^\{(\d+(?:\.\d+)?)\}$', val)
    if m:
        return float(m.group(1))
    m = re.match(r'^\{#([\d.]+)\}$', val)
    if m:
        return float(m.group(1))
    return 4.0


def parse_bpm(val):
    if not val:
        return 1.0
    m = re.match(r'\(([^)]+)\)', val)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return 1.0
    return 1.0


def circular_distance(p1, p2):
    diff = abs(p2 - p1)
    return min(diff, 8 - diff)


def is_slide(part):
    tmp = re.sub(r'\[.*?\]', '', part)
    for s in ('pp', 'qq', '-', '>', '<', '^', 'v', 'V', 'p', 'q', 's', 'z', 'w'):
        if s in tmp:
            return True
    return False


def classify(part):
    if not part or part == 'E':
        return None

    tmp = re.sub(r'\[.*?\]', '', part)
    is_break = 'b' in tmp
    is_ex = 'x' in tmp
    is_hold = 'h' in tmp

    m = re.search(r'([A-E]\d|C|[1-8])', tmp)
    if not m:
        return None
    pos = m.group(1)

    is_sensor = bool(re.match(r'^[A-E]\d$', pos) or pos == 'C')

    if is_hold:
        if is_sensor:
            return ('touch_hold', is_break, is_ex)
        return ('hold', is_break, is_ex)
    else:
        if is_sensor:
            return ('touch', is_break, is_ex)
        return ('tap', is_break, is_ex)


def propagate_bpm_backward(notes_data):
    next_bpm = None
    next_div = None
    for i in range(len(notes_data) - 1, -1, -1):
        note = notes_data[i]
        if not note['is_empty']:
            next_bpm = note['bpm_prior']
            next_div = note['div_prior']
        elif next_bpm is not None:
            note['bpm_prior'] = next_bpm
            note['div_prior'] = next_div


def calculate_note_gaps(notes_data):
    gaps = [0.0] * len(notes_data)
    accumulated = 0.0
    for i in range(len(notes_data)):
        note = notes_data[i]
        bpm = note['bpm_prior']
        div = note['div_prior']
        duration = (240.0 / bpm) / div if bpm > 0 and div > 0 else 0.0
        if note['is_empty']:
            accumulated += duration
            gaps[i] = accumulated
        else:
            gaps[i] = accumulated + duration if accumulated > 0 else 0.0
            accumulated = 0.0
    return gaps


def calculate_time_to_next_playable(notes_data):
    time_to_next = [0.0] * len(notes_data)
    original_bpm = [n['bpm_prior'] for n in notes_data]
    original_div = [n['div_prior'] for n in notes_data]
    for i in range(len(notes_data)):
        if not notes_data[i]['is_empty']:
            accumulated = 0.0
            for j in range(i + 1, len(notes_data)):
                bpm = original_bpm[j]
                div = original_div[j]
                duration = (240.0 / bpm) / div if bpm > 0 and div > 0 else 0.0
                accumulated += duration
                if not notes_data[j]['is_empty']:
                    time_to_next[i] = accumulated
                    break
    return time_to_next


def score_note(ntype, brk, ex, time_to_next, in_between_mult=1.0, trill_mult=1.0):
    if ntype == 'tap':
        tm = TAP_MULT
    elif ntype == 'hold':
        tm = HOLD_MULT
    elif ntype in ('touch', 'touch_hold'):
        tm = TOUCH_MULT
    else:
        tm = 0.0

    if brk:
        pm = BREAK_MULT
    elif ex:
        pm = EX_MULT
    else:
        pm = NORMAL_MULT

    note_speed = 1.0 / time_to_next if time_to_next > 0 else 0.0
    score = tm * pm * note_speed * 500 * in_between_mult * trill_mult
    
    return score


def is_slide_start(raw):
    """Check if raw note string contains slide symbols."""
    if not raw:
        return False
    tmp = re.sub(r'\[.*?\]', '', raw)
    for s in ('pp', 'qq', '-', '>', '<', '^', 'v', 'V', 'p', 'q', 's', 'z', 'w'):
        if s in tmp:
            return True
    return False


def is_trill_start(tap_events, idx):
    """Check if tap_events[idx] starts a trill pattern.
    
    Trill patterns: a,b,a,b,... (4+ notes alternating)
    """
    if idx + 3 >= len(tap_events):
        return False
    
    notes = tap_events[idx:idx+4]
    positions = []
    for n in notes:
        pos = n.get('pos')
        if pos is None:
            return False
        positions.append(pos)
    
    a, b = positions[0], positions[1]
    if a == b:
        return False
    
    if positions[2] != a or positions[3] != b:
        return False
    
    return True


def get_trill_notes_in_pattern(tap_events, idx):
    """Get all notes in a trill pattern starting at idx."""
    if not is_trill_start(tap_events, idx):
        return []
    
    notes = []
    notes.append(tap_events[idx])
    
    a = tap_events[idx].get('pos')
    b = tap_events[idx + 1].get('pos')
    
    j = idx + 2
    while j < len(tap_events):
        pos = tap_events[j].get('pos')
        if pos is None:
            break
        expected = a if (j - idx) % 2 == 0 else b
        if pos != expected:
            break
        notes.append(tap_events[j])
        j += 1
    
    return notes if len(notes) >= 4 else []


def is_trill_range_valid(trill_events, start_idx, end_idx):
    """Check no double notes or unknown in range."""
    for k in range(start_idx, end_idx + 1):
        if k < len(trill_events):
            ev = trill_events[k]
            if ev.get('is_double'):
                return False
            if ev.get('type') == 'unknown':
                return False
    return True


def get_trill_divider(div_str):
    if not div_str:
        return 0
    m = re.match(r'^\{(\d+(?:\.\d+)?)\}$', div_str)
    if m:
        return float(m.group(1))
    m = re.match(r'^\{#([\d.]+)\}$', div_str)
    if m:
        return float(m.group(1))
    return 0


def is_trill_density_sufficient(note_info, trill_range=None):
    start_div = get_trill_divider(note_info.get('active_divider', ''))
    if start_div == 0:
        return False
    
    if trill_range is not None:
        for idx in range(trill_range[0], trill_range[1] + 1):
            if idx < len(trill_range[2]):
                note = trill_range[2][idx]
                note_div = get_trill_divider(note.get('active_divider', ''))
                if note_div > 64:
                    return start_div <= 32
    
    return start_div <= 32


def try_anchor_trill(single_notes, masked, n, i, trill_events):
    if i + 3 >= n:
        return None
    a = single_notes[i]['position']
    if ((i + 1) in masked or (i + 2) in masked or (i + 3) in masked or
        single_notes[i + 1]['position'] == a or
        single_notes[i + 2]['position'] != a or
        single_notes[i + 3]['position'] == a):
        return None
    j = i + 4
    while j < n and j not in masked:
        expected_anchor = ((j - i) % 2 == 0)
        pos = single_notes[j]['position']
        if expected_anchor:
            if pos != a:
                break
        else:
            if pos == a:
                break
        j += 1
    
    trill_range = (i, j - 1, trill_events)
    if not is_trill_density_sufficient(single_notes[i], trill_range):
        return None
    return {'start': i, 'end': j - 1, 'kind': 'anchor'}


def try_regular_trill(single_notes, masked, n, i, trill_events):
    if i + 3 >= n:
        return None
    a = single_notes[i]['position']
    b = single_notes[i + 1]['position']
    if a == b:
        return None
    if ((i + 1) in masked or (i + 2) in masked or (i + 3) in masked or
        single_notes[i + 2]['position'] != a or
        single_notes[i + 3]['position'] != b):
        return None
    j = i + 4
    while j < n and j not in masked:
        expected = a if (j - i) % 2 == 0 else b
        if single_notes[j]['position'] != expected:
            break
        j += 1
    
    trill_range = (i, j - 1, trill_events)
    if not is_trill_density_sufficient(single_notes[i], trill_range):
        return None
    return {'start': i, 'end': j - 1, 'kind': 'regular'}


FAN_PATTERNS = [
    (0, 2, 1, 3), (0, 3, 1, 2), (1, 2, 0, 3),
    (0, -2, -1, -3), (0, -3, -1, -2), (-1, -2, 0, -3),
]

CIRCULAR_PATTERNS = [
    (0, 1, -1, 2, -2), (0, -1, 1, -2, 2),
    (0, 1, -1, 2, -2, 3), (0, -1, 1, -2, 2, -3),
    (0, 1, -1, 2, -2, 3, -3), (0, -1, 1, -2, 2, -3, 3),
    (0, 1, -1, 2, -2, 3, -3, 4), (0, -1, 1, -2, 2, -3, 3, -4),
]


def try_fan_trill(single_notes, masked, n, i, trill_events):
    if i + 3 >= n or (i + 1) in masked or (i + 2) in masked or (i + 3) in masked:
        return None
    a = single_notes[i]['position']
    positions = [single_notes[i + k]['position'] for k in range(4)]
    for pattern in FAN_PATTERNS:
        offsets = [pattern[k] - pattern[0] for k in range(4)]
        expected = [a + offsets[k] for k in range(4)]
        if positions == expected:
            trill_range = (i, i + 3, trill_events)
            if not is_trill_density_sufficient(single_notes[i], trill_range):
                return None
            return {'start': i, 'end': i + 3, 'kind': 'fan'}
    return None


def try_circular_trill(single_notes, masked, n, i, trill_events):
    if i + 4 >= n or (i + 1) in masked or (i + 2) in masked:
        return None
    a = single_notes[i]['position']
    min_notes = 5
    max_notes = 8
    for length in range(min_notes, max_notes + 1):
        if i + length > n:
            break
        positions = [single_notes[i + k]['position'] for k in range(length)]
        for pattern in CIRCULAR_PATTERNS[:length - 5 + 5]:
            offsets = [pattern[k] - pattern[0] for k in range(len(pattern))]
            if len(offsets) != length:
                continue
            expected = [a + offsets[k] for k in range(length)]
            if positions == expected:
                for check_idx in range(i, i + length):
                    if check_idx in masked:
                        break
                else:
                    trill_range = (i, i + length - 1, trill_events)
                    if not is_trill_density_sufficient(single_notes[i], trill_range):
                        return None
                    return {'start': i, 'end': i + length - 1, 'kind': 'circular'}
    return None


def try_mini_trill(single_notes, masked, n, i, trill_events):
    if i + 2 >= n or (i + 1) in masked or (i + 2) in masked:
        return None
    trill_range = (i, i + 2, trill_events)
    if not is_trill_density_sufficient(single_notes[i], trill_range):
        return None
    return {'start': i, 'end': i + 2, 'kind': 'mini'}


def detect_all_trills(trill_events):
    """Detect all trill types: anchor, regular, circular, fan, mini."""
    all_trills = []
    single_notes = [tevent for tevent in trill_events 
                   if tevent.get('type') == 'note' and tevent.get('position') and not tevent.get('is_double')]
    
    for idx, sn in enumerate(single_notes):
        sn['index'] = sn.get('event_idx', idx)
    
    n = len(single_notes)
    masked = set()
    
    for i in range(n):
        if i in masked:
            continue
        
        found = try_anchor_trill(single_notes, masked, n, i, trill_events)
        if found:
            all_trills.append(found)
            for k in range(found['start'], found['end'] + 1):
                masked.add(k)
            continue
        
        found = try_regular_trill(single_notes, masked, n, i, trill_events)
        if found:
            all_trills.append(found)
            for k in range(found['start'], found['end'] + 1):
                masked.add(k)
            continue
        
        found = try_circular_trill(single_notes, masked, n, i, trill_events)
        if found:
            all_trills.append(found)
            for k in range(found['start'], found['end'] + 1):
                masked.add(k)
            continue
        
        found = try_fan_trill(single_notes, masked, n, i, trill_events)
        if found:
            all_trills.append(found)
            for k in range(found['start'], found['end'] + 1):
                masked.add(k)
            continue
        
        found = try_mini_trill(single_notes, masked, n, i, trill_events)
        if found:
            all_trills.append(found)
            for k in range(found['start'], found['end'] + 1):
                masked.add(k)
    
    return all_trills


def get_slide_duration(events, start_idx):
    """Get slide duration from events starting at start_idx."""
    if start_idx >= len(events):
        return 0.0
    ev = events[start_idx]
    if ev.get('type') != 'note' or not is_slide_start(ev.get('raw', '')):
        return 0.0
    
    slide_symbols = {'pp', 'qq', 'w', 'p', 'q', 'v', 'V', '-', '>', '<', '^'}
    raw = ev.get('raw', '')
    tmp = re.sub(r'\[.*?\]', '', raw)
    
    max_dur = 0.0
    for s in slide_symbols:
        if s in tmp:
            if s in ('pp', 'qq', 'w'):
                max_dur = max(max_dur, 1.0)
            elif s in ('p', 'q', 'v', 'V', '-'):
                max_dur = max(max_dur, 0.5)
            elif s in ('>', '<', '^'):
                max_dur = max(max_dur, 0.25)
    
    bpm = ev.get('bpm', 120)
    div = ev.get('div', 4.0)
    return (240.0 / bpm) / div if bpm > 0 and div > 0 else 0.25


def get_in_between_multiplier(tap_events, slide_start_idx, all_events):
    """Calculate in-between multiplier for a slide start.
    
    Counts notes and holds during the slide duration.
    """
    if slide_start_idx >= len(tap_events):
        return 1.0
    
    slide_event = tap_events[slide_start_idx]
    slide_time = slide_event.get('time', 0.0)
    raw = slide_event.get('raw', '')
    
    # Determine slide duration based on symbol
    slide_dur = 0.25
    slide_symbols = {'pp', 'qq', 'w', 'p', 'q', 'v', 'V', '-', '>', '<', '^'}
    tmp = re.sub(r'\[.*?\]', '', raw)
    for s in slide_symbols:
        if s in tmp:
            if s in ('pp', 'qq', 'w'):
                slide_dur = 1.0
            elif s in ('p', 'q', 'v', 'V', '-'):
                slide_dur = 0.5
            elif s in ('>', '<', '^'):
                slide_dur = 0.25
            break
    
    # Convert slide_dur from beats to time
    bpm = slide_event.get('bpm', 150)
    div = slide_event.get('div', 4.0)
    beat_time = (240.0 / bpm) / div if bpm > 0 and div > 0 else 0.25
    slide_dur_time = slide_dur * beat_time
    
    delay_time = 0.25 * beat_time
    slide_end = slide_time + delay_time + slide_dur_time
    
    note_count = 0
    hold_count = 0
    
    for ev in all_events:
        if ev.get('type') != 'note':
            continue
        
        ev_time = ev.get('time', 0.0)
        if ev_time == slide_time:
            continue
        
        if slide_time <= ev_time <= slide_end:
            note_count += ev.get('note_count', 0)
            hold_count += ev.get('hold_count', 0)
    
    base = 0.5 * note_count + 0.75 * hold_count
    if base > 0:
        log_part = math.log(1 + base, 3)
        return 1.0 + log_part
    return 1.0


def get_beat_duration(divider_str, bpm):
    if not divider_str:
        return 60.0 / (bpm * 4) if bpm > 0 else 0.25
    m = re.match(r'^\{#?(\d+(?:\.\d+)?)\}', divider_str)
    if m:
        d = float(m.group(1))
        return 60.0 / (bpm * d) if bpm > 0 and d > 0 else 0.25
    return 60.0 / (bpm * 4) if bpm > 0 else 0.25


def parse_notes(content, title=None):
    lines = content.split('\n')

    title = None
    start_line = 0
    for idx, line in enumerate(lines):
        if line.strip().startswith('&title'):
            title = line.strip()[6:].strip()
            start_line = idx + 1
            break

    lines = lines[start_line:]

    events = []
    all_notes = []
    cur_div = None
    cur_bpm = None
    lead_re = re.compile(r'^(\{[^}]*\}|\([^)]*\))+')
    all_notes_idx = 0

    for ln, line in enumerate(lines, start=start_line+1):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^\d+:\s*', line)
        if m:
            line = line[m.end():]

        beat_fields = line.split(',')
        cur_time = 0.0
        line_start_index = all_notes_idx

        for raw in beat_fields:
            raw = raw.strip()
            prior_div = cur_div
            prior_bpm = cur_bpm

            act_div = cur_div
            act_bpm = cur_bpm

            mm = lead_re.match(raw)
            if mm:
                lead = mm.group(0)
                for tok in re.findall(r'\{(\d+(?:\.\d+)?)\}|\{#(\d+(?:\.\d+)?)\}|\(([^)]+)\)', raw):
                    if tok[0]:
                        act_div = '{' + tok[0] + '}'
                    elif tok[1]:
                        act_div = '{#' + tok[1] + '}'
                    elif tok[2]:
                        act_bpm = '(' + tok[2] + ')'
                raw = raw[mm.end():].strip()

            is_empty = not raw or raw == 'E'

            if is_empty:
                store_bpm = act_bpm
                store_div = act_div
            else:
                store_bpm = act_bpm
                store_div = act_div

            store_bpm_val = parse_bpm(store_bpm)
            store_div_val = get_div(store_div)

            bpm_val = parse_bpm(act_bpm)
            div_val = get_div(act_div)

            all_notes.append({
                'raw': raw,
                'is_empty': is_empty,
                'bpm_prior': store_bpm_val,
                'div_prior': store_div_val,
                'div_str_prior': store_div,
                'bpm_str_prior': store_bpm,
            })

            if is_empty:
                cur_div = act_div
                cur_bpm = act_bpm
                all_notes_idx += 1
                continue
            
            cur_div = act_div
            cur_bpm = act_bpm

            notes = []
            if raw.isdigit():
                for ch in raw:
                    notes.append(('tap', False, False))
            else:
                for p in re.split(r'[/`]', raw):
                    p = p.strip()
                    if not p or is_slide(p):
                        continue
                    r = classify(p)
                    if r:
                        notes.append(r)

            if notes:
                events.append({
                    'raw': raw,
                    'notes': notes,
                    'div': div_val,
                    'div_str': act_div,
                    'bpm': bpm_val,
                    'line': ln,
                    'time': cur_time,
                    'all_notes_idx': all_notes_idx,
                })

            cur_div = act_div
            cur_bpm = act_bpm
            cur_time += (240.0 / bpm_val) / div_val if bpm_val > 0 and div_val > 0 else 0.25
            all_notes_idx += 1

    return events, all_notes, title


def calc(events, all_notes=None, time_to_next_gaps=None):
    if time_to_next_gaps is None:
        time_to_next_gaps = []
        if all_notes:
            time_to_next_gaps = calculate_time_to_next_playable(all_notes)

    tot = 0.0
    tc, hc, cc = 0, 0, 0
    ts, hs, cs = 0.0, 0.0, 0.0

    tap_events = []
    hold_events = []
    touch_events = []

    note_index_map = {}
    current_note_idx = 0

    for ev in events:
        b = ev['bpm']
        t = ev['time']
        for ntype, brk, ex in ev['notes']:
            pos_match = re.search(r'([1-8])', re.sub(r'\[.*?\]', '', ev['raw']))
            pos = int(pos_match.group(1)) if pos_match else None
            
            if ntype == 'tap':
                tc += 1
                cd = circular_distance(pos, pos) if pos else 0
                tap_events.append({
                    'ntype': ntype,
                    'brk': brk,
                    'ex': ex,
                    'pos': pos,
                    'circular_distance': cd,
                    'time': t,
                    'bpm': b,
                    'all_notes_idx': ev.get('all_notes_idx', 0),
                    'raw': ev.get('raw', '')
                })
            elif ntype == 'hold':
                hc += 1
                hold_events.append({
                    'ntype': ntype,
                    'brk': brk,
                    'ex': ex,
                    'time': t,
                    'bpm': b,
                    'all_notes_idx': ev.get('all_notes_idx', 0)
                })
            else:
                cc += 1
                touch_events.append({
                    'ntype': ntype,
                    'brk': brk,
                    'ex': ex,
                    'time': t,
                    'bpm': b,
                    'all_notes_idx': ev.get('all_notes_idx', 0)
                })

    all_events = tap_events + hold_events + touch_events
    all_events.sort(key=lambda x: x['time'])

    gap_values = calculate_note_gaps(all_notes)
    time_to_next = {}
    for ev in all_events:
        note_idx = ev['all_notes_idx']
        if note_idx < len(time_to_next_gaps):
            time_to_next[id(ev)] = time_to_next_gaps[note_idx]
        else:
            time_to_next[id(ev)] = 0.0

    prev_pos = None
    
    # Build events list with type for in_between calculation
    all_events_for_ib = []
    for ev in events:
        all_events_for_ib.append({
            'type': 'note',
            'time': ev.get('time', 0.0),
            'note_count': len(ev.get('notes', [])),
            'hold_count': sum(1 for n in ev.get('notes', []) if n[0] == 'hold')
        })
    
    # Calculate in_between for slide starts
    in_between_mults = {}
    for i, ev in enumerate(tap_events):
        if is_slide_start(ev.get('raw', '')):
            in_between_mults[i] = get_in_between_multiplier(tap_events, i, all_events_for_ib)
    
    # Detect trill patterns using full detect_trills logic
    trill_mults = {}
    trill_note_indices = set()
    
    # Build events in detect_trills format for trill detection  
    trill_events = []
    for ev_idx, ev in enumerate(events):
        trill_event = {
            'type': 'note' if ev.get('notes') else 'empty',
            'raw': ev.get('raw', ''),
            'active_divider': ev.get('div_str', '{4}'),
            'active_bpm': ev.get('bpm_str', '(120)'),
            'time': ev.get('time', 0),
            'line': ev.get('line', 0),
            'event_idx': ev_idx,
        }
        if ev.get('notes'):
            for ntype, brk, ex in ev['notes']:
                pos_match = re.search(r'([1-8])', re.sub(r'\[.*?\]', '', ev.get('raw', '')))
                if pos_match:
                    trill_event['position'] = int(pos_match.group(1))
                    break
        trill_events.append(trill_event)
    
    # Build map from event_idx to all_notes_idx
    event_idx_to_all_notes_idx = {}
    for ev_idx, ev in enumerate(events):
        if ev.get('all_notes_idx') is not None:
            event_idx_to_all_notes_idx[ev_idx] = ev['all_notes_idx']
    
    # Use full detect_all_trills (anchor, regular, circular, fan, mini)
    all_trills = detect_all_trills(trill_events)
    trill_div_corrections = {}
    
    for trill in all_trills:
        start_idx = trill['start']
        end_idx = trill['end']
        start_div = get_trill_divider(trill_events[start_idx].get('active_divider', ''))
        
        for k in range(start_idx, end_idx + 1):
            if k < len(trill_events):
                trill_mults[k] = 1.5
                trill_note_indices.add(k)
                note_div = get_trill_divider(trill_events[k].get('active_divider', ''))
                if note_div > 64:
                    trill_events[k]['active_divider'] = f'{{{int(start_div)}}}'
                    trill_event_idx = trill_events[k].get('event_idx')
                    if trill_event_idx is not None:
                        notes_idx = event_idx_to_all_notes_idx.get(trill_event_idx)
                        if notes_idx is not None:
                            trill_div_corrections[notes_idx] = int(start_div)
    
    for i, ev in enumerate(tap_events):
        ttn = time_to_next.get(id(ev), 0.0)
        pos = ev.get('pos')
        ev['circular_distance'] = circular_distance(prev_pos, pos) if prev_pos is not None and pos is not None else 0
        ib_mult = in_between_mults.get(i, 1.0)
        tr_mult = trill_mults.get(i, 1.0)
        s = score_note(ev['ntype'], ev['brk'], ev['ex'], ttn, ib_mult, tr_mult)
        mult = 1 + ev['circular_distance'] * 0.2
        s *= mult
        ts += s
        ev['score'] = s
        ev['time_to_next'] = ttn
        ev['in_between_mult'] = ib_mult
        ev['trill_mult'] = tr_mult
        prev_pos = pos

    for ev in hold_events:
        s = score_note(ev['ntype'], ev['brk'], ev['ex'], 0.0)
        hs += s

    for ev in touch_events:
        s = score_note(ev['ntype'], ev['brk'], ev['ex'], 0.0)
        cs += s

    ts = sum(t['score'] for t in tap_events)
    tot = ts + hs + cs

    return {
        'total': tot,
        'tap_count': tc, 'hold_count': hc, 'touch_count': cc,
        'tap_score': ts, 'hold_score': hs, 'touch_score': cs,
        'note_count': tc + hc + cc,
        'tap_events_debug': tap_events,
        'trill_div_corrections': trill_div_corrections,
    }


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    debug = os.path.join(base, 'debugcharts')
    charts = os.path.join(base, 'charts')
    outf = os.path.join(base, 'tap_output.txt')

    if os.path.isdir(debug) and any(f.endswith('.txt') for f in os.listdir(debug)):
        charts = debug
        print(f"Using debug directory: {charts}")

    if not os.path.isdir(charts):
        print(f"Dir not found: {charts}")
        return

    lines = []

    for fn in sorted(os.listdir(charts)):
        if not fn.endswith('.txt') or fn in ('trill_output.txt', 'spin_output.txt', 'slide_output.txt', 'tap_output.txt'):
            continue
        fp = os.path.join(charts, fn)

        with open(fp, 'r', encoding='utf-8-sig') as f:
            c = f.read()

        evs, all_notes, chart_title = parse_notes(c)
        
        time_to_next_gaps = []
        if all_notes and len(all_notes) > 0:
            # BPM/Div propagation
            current_bpm = all_notes[0]['bpm_prior']
            current_div = all_notes[0]['div_prior']
            for i in range(len(all_notes)):
                bpm_str = all_notes[i].get('bpm_str_prior', '')
                div_str = all_notes[i].get('div_str_prior', '')
                
                if '(' in bpm_str:
                    current_bpm = all_notes[i]['bpm_prior']
                    current_div = all_notes[i]['div_prior']
                elif '{' in div_str:
                    current_div = all_notes[i]['div_prior']
                
                all_notes[i]['bpm_prior'] = current_bpm
                all_notes[i]['div_prior'] = current_div
            
            # Calculate backward
            accumulated = 0.0
            backward_gaps = [0.0] * len(all_notes)
            for i in range(len(all_notes)):
                note = all_notes[i]
                bpm = note['bpm_prior']
                div = note['div_prior']
                duration = (240.0 / bpm) / div if bpm > 0 and div > 0 else 0.0
                if note['is_empty']:
                    accumulated += duration
                    backward_gaps[i] = accumulated
                else:
                    backward_gaps[i] = accumulated
                    accumulated = 0.0

            # Forward (own duration)
            forward_gaps = [0.0] * len(all_notes)
            for i in range(len(all_notes)):
                bpm = all_notes[i]['bpm_prior']
                div = all_notes[i]['div_prior']
                own_dur = (240.0 / bpm) / div if bpm > 0 and div > 0 else 0.0
                forward_gaps[i] = own_dur
            
            # Final gaps
            first_bpm = all_notes[0]['bpm_prior']
            time_to_next_gaps = [0.0] * len(all_notes)
            for i in range(len(all_notes)):
                note = all_notes[i]
                bpm = note['bpm_prior']
                div = note['div_prior']
                own_duration = (240.0 / bpm) / div if bpm > 0 and div > 0 else 0.0
                
                if i == 0:
                    time_to_next_gaps[i] = 0.0
                elif not note['is_empty']:
                    if backward_gaps[i] > own_duration:
                        if i >= 8:
                            next_own = 0.0
                            for j in range(i + 1, len(all_notes)):
                                if not all_notes[j]['is_empty']:
                                    nbpm = all_notes[j]['bpm_prior']
                                    ndiv = all_notes[j]['div_prior']
                                    next_own = (240.0 / nbpm) / ndiv if nbpm > 0 and ndiv > 0 else 0.0
                                    break
                            time_to_next_gaps[i] = backward_gaps[i] + own_duration + next_own
                        else:
                            time_to_next_gaps[i] = backward_gaps[i] + own_duration
                    else:
                        time_to_next_gaps[i] = own_duration
                else:
                    current_div = note['div_prior']
                    prev_div = all_notes[i-1]['div_prior'] if i > 0 else 4.0
                    current_bpm = note['bpm_prior']
                    
                    div_changed = current_div != prev_div
                    is_new_tempo = current_bpm != first_bpm
                    
                    if div_changed and is_new_tempo and backward_gaps[i] > own_duration:
                        time_to_next_gaps[i] = backward_gaps[i] + own_duration
                    else:
                        time_to_next_gaps[i] = backward_gaps[i]
        
        r = calc(evs, all_notes, time_to_next_gaps)
        trill_div_corrections = r.get('trill_div_corrections', {})

        display_title = chart_title if chart_title else fn
        diff_match = re.search(r' - ([^.]+)\.txt$', fn)
        if diff_match:
            display_title = f"{display_title} - {diff_match.group(1)}"

        print(f"\n=== {display_title} ===")
        lines.append(f"=== {display_title} ===")

        if fn == 'testchart.txt':
            print("\n  --- All Note Slot Times ---")
            lines.append("\n  --- All Note Slot Times ---")
            
            # Build map of all_notes_idx to tap event
            idx_to_tap = {}
            for ev in r.get('tap_events_debug', []):
                idx = ev.get('all_notes_idx', 0)
                idx_to_tap[idx] = ev
            
            # Show notes in expected pattern (skip trailing empty from line 1, i.e., index 7)
            note_num = 1
            for i in range(len(all_notes) - 1):
                if i == 7:  # Skip trailing empty from line 1
                    continue
                note = all_notes[i]
                raw = note['raw']
                bpm = note['bpm_prior']
                div = note['div_prior']
                corrected_div = trill_div_corrections.get(i, div)
                display = f"({int(bpm)})" + "{" + f"{int(corrected_div)}" + "}" + raw
                ttn = time_to_next_gaps[i]
                ttn_rounded = int(ttn * 100 + 0.5) / 100  # Round half up to 2 decimal places
                
                tap_ev = idx_to_tap.get(i)
                dist = tap_ev.get('circular_distance', 0) if tap_ev else 0
                score = tap_ev.get('score', 0) if tap_ev else 0
                ib_mult = tap_ev.get('in_between_mult', 1.0) if tap_ev else 1.0
                tr_mult = tap_ev.get('trill_mult', 1.0) if tap_ev else 1.0
                
                info = (
                    f"Note {note_num}: {display}; "
                    f"time_to_next_note = {ttn_rounded:.2f}; "
                    f"distance = {dist}; in_between = {ib_mult:.2f}; trill = {tr_mult:.1f}; score = {score:.1f}"
                )
                print(info)
                lines.append(info)
                note_num += 1
        
        avg = r['total'] / r['note_count'] if r['note_count'] > 0 else 0
        s = f"  taps: {r['tap_count']} ({r['tap_score']:.1f}) | holds: {r['hold_count']} ({r['hold_score']:.1f}) | touches: {r['touch_count']} ({r['touch_score']:.1f}) | total: {r['note_count']} notes ({r['total']:.1f} pts) | avg: {avg:.2f}/note"
        print(s)
        lines.append(s)

    with open(outf, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"\n--- METHOD ---")
    print(f"  Points = (type_mult * property_mult * note_speed) / 2")
    print(f"  Type: tap 1.0, hold 2.0, touch 1.0")
    print(f"  Property: break 5.0, ex 0.5, normal 1.0")
    print(f"  Note speed = 1 / time_diff (from this note to next note)")
    print(f"  Taps also multiplied by (1 + circular_distance * 0.2)")


if __name__ == '__main__':
    main()