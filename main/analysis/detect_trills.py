import io
import os
import re
import sys

# Force UTF-8 output on Windows
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def add_mod_btn(x, y):
    """Add y to button x (1-8) with circular wrap."""
    return ((x - 1 + y) % 8) + 1


def extract_position(remainder):
    """Extract note position from the note part of a beat."""
    if not remainder:
        return None
    m = re.match(r'^(C[12]?)', remainder)
    if m:
        return 'C'
    m = re.match(r'^([A-E]\d)', remainder)
    if m:
        return m.group(1)
    m = re.match(r'^([1-8])', remainder)
    if m:
        return m.group(1)
    return None


def is_double_note(remainder):
    """Check if a beat remainder represents a double note (EACH)."""
    if '/' in remainder or '`' in remainder:
        return True
    if remainder.isdigit() and len(remainder) >= 2:
        return True
    return False


def parse_chart(content):
    """Parse simai chart content into a list of beat events."""
    lines = content.split('\n')

    title = None
    start_line = 0
    for idx, line in enumerate(lines):
        if line.strip().startswith('&title'):
            title = line.strip()[6:].strip()
            start_line = idx + 1
            break

    lines = lines[start_line:]

    cleaned_parts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^\d+:\s*', line)
        if m:
            line = line[m.end():]
        cleaned_parts.append(line)

    full_chart = ''.join(cleaned_parts)
    full_chart = re.sub(r'\s+', '', full_chart)
    beat_fields = full_chart.split(',')

    events = []
    current_divider = None
    current_bpm = None
    leading_re = re.compile(r'^(\{[^}]*\}|\([^)]*\))+')

    for raw_beat in beat_fields:
        raw = raw_beat.strip()
        active_divider = current_divider
        active_bpm = current_bpm
        remainder = raw

        m = leading_re.match(raw)
        if m:
            leading = m.group(0)
            for token in re.findall(r'\{(\d+(?:\.\d+)?)\}|\{#(\d+(?:\.\d+)?)\}|\(([^)]+)\)', leading):
                if token[0] is not None:
                    active_divider = '{' + token[0] + '}'
                    current_divider = active_divider
                elif token[1] is not None:
                    active_divider = '{#' + token[1] + '}'
                    current_divider = active_divider
                elif token[2] is not None:
                    active_bpm = '(' + token[2] + ')'
                    current_bpm = active_bpm
            remainder = raw[m.end():].strip()

        if not remainder:
            events.append({'type': 'empty', 'raw': raw,
                           'active_divider': active_divider, 'active_bpm': active_bpm})
            continue

        if is_double_note(remainder):
            events.append({'type': 'note', 'raw': raw, 'is_double': True,
                           'position': None, 'active_divider': active_divider,
                           'active_bpm': active_bpm})
        else:
            pos = extract_position(remainder)
            if pos:
                events.append({'type': 'note', 'raw': raw, 'is_double': False,
                               'position': pos, 'active_divider': active_divider,
                               'active_bpm': active_bpm})
            else:
                events.append({'type': 'unknown', 'raw': raw,
                               'active_divider': active_divider,
                               'active_bpm': active_bpm})

    return events, title


def is_range_valid(events, start_event_idx, end_event_idx):
    """Check that no double notes or unknown events exist in the inclusive event index range."""
    for k in range(start_event_idx, end_event_idx + 1):
        ev = events[k]
        if ev['type'] == 'note' and ev.get('is_double'):
            return False
        if ev['type'] == 'unknown':
            return False
    return True


def get_divider_value(div_str):
    """Extract numeric value from a divider string like {16}, {8}, {#0.35}."""
    if not div_str:
        return 0
    m = re.match(r'^\{(\d+(?:\.\d+)?)\}$', div_str)
    if m:
        return float(m.group(1))
    m = re.match(r'^\{#([\d.]+)\}$', div_str)
    if m:
        return float(m.group(1))
    return 0


def is_density_sufficient(note_info):
    """Check if the note density is >= 8."""
    return get_divider_value(note_info['active_divider']) >= 8


def reconstruct_trill(trill_notes):
    """Reconstruct a trill string with dividers preserved.
    
    If any note has a beat divisor > 64, use the starting beat divisor for all notes in output.
    """
    if not trill_notes:
        return ''
    
    start_div = trill_notes[0]['active_divider']
    start_div_val = get_divider_value(start_div)
    
    has_high_div = any(get_divider_value(note['active_divider']) > 64 for note in trill_notes)
    
    parts = []
    for idx_in_trill, note_info in enumerate(trill_notes):
        raw = note_info['raw']
        div = note_info['active_divider']
        
        if idx_in_trill == 0:
            if has_high_div and start_div_val > 0:
                stripped = re.sub(r'^(\{[^}]*\}|\([^)]*\))+(.*)$', r'\2', raw)
                if stripped:
                    parts.append(start_div)
                    parts.append(stripped)
                else:
                    parts.append(raw)
            else:
                if div and not raw.startswith(div):
                    parts.append(div)
                parts.append(raw)
        else:
            if has_high_div and start_div_val > 0:
                stripped = re.sub(r'^(\{[^}]*\}|\([^)]*\))+(.*)$', r'\2', raw)
                parts.append(',')
                if stripped:
                    parts.append(start_div)
                    parts.append(stripped)
                else:
                    parts.append(raw)
            else:
                parts.append(',')
                if div and not raw.startswith(div):
                    parts.append(div)
                parts.append(raw)
    
    return ''.join(parts)


def _can_extend(single_notes, consumed, start, end):
    """Verify that all single-note indices from start to end (inclusive) are unconsumed."""
    for k in range(start, end + 1):
        if consumed[k]:
            return False
    return True


def verify_trill_in_chart(events, trill):
    """Verify that the trill exists in the chart at the reported event indices.

    The first beat may have a leading divider token that was added by reconstruction.
    Strip it and compare the remaining note parts with the actual event raws.
    """
    start = trill['start_event_index']
    end = trill['end_event_index']

    output = trill['output']
    parts = output.split(',')
    actual_raws = [events[k]['raw'] for k in range(start, end + 1)]

    if len(parts) != len(actual_raws):
        return False

    for part, actual in zip(parts, actual_raws):
        if part == actual:
            continue
        m = re.match(r'^(\{[^}]*\}|\([^)]*\))+(.*)$', part)
        if m:
            stripped = m.group(2)
        else:
            stripped = part
        m2 = re.match(r'^(\{[^}]*\}|\([^)]*\))+(.*)$', actual)
        if m2:
            actual_stripped = m2.group(2)
        else:
            actual_stripped = actual
        if stripped != actual_stripped:
            return False

    return True


def detect_patterns(events):
    """Detect trills in order: anchor, regular, circular, fan, mini.

    Trills are masked as empty beats as they are found. When an empty beat
    is encountered, parsing restarts at the next non-empty note.
    Verification is done to ensure reconstructed trill matches the chart.
    """
    single_notes = []
    for idx, event in enumerate(events):
        if event['type'] == 'note' and not event.get('is_double') and event['position'] is not None:
            single_notes.append({
                'index': idx,
                'position': event['position'],
                'raw': event['raw'],
                'active_divider': event['active_divider'],
            })

    n = len(single_notes)
    masked = set()
    all_trills = []

    i = 0
    while i < n:
        if i in masked:
            i = next_unmasked(i + 1, masked, n)
            continue

        a = single_notes[i]['position']

        # --- Step 1: Anchor trills (a, x1, a, x2, ...) n >= 2 pairs ---
        found = try_anchor_trill(single_notes, masked, n, i, events)
        if found:
            trill, consumed_end = found
            if not verify_trill_in_chart(events, trill):
                i = next_unmasked(i + 1, masked, n)
                continue
            all_trills.append(trill)
            for k in range(trill['start_note_index'], trill['end_note_index'] + 1):
                masked.add(k)
            i = next_unmasked(consumed_end + 1, masked, n)
            continue

        # --- Step 2: Regular trills (a, b, a, b, ...) 4+ notes ---
        found = try_regular_trill(single_notes, masked, n, i, events)
        if found:
            trill, consumed_end = found
            if not verify_trill_in_chart(events, trill):
                i = next_unmasked(i + 1, masked, n)
                continue
            all_trills.append(trill)
            for k in range(trill['start_note_index'], trill['end_note_index'] + 1):
                masked.add(k)
            i = next_unmasked(consumed_end + 1, masked, n)
            continue

        # --- Step 3: Circular trills (5-8 notes) ---
        found = try_circular_trill(single_notes, masked, n, i, events)
        if found:
            trill, consumed_end = found
            if not verify_trill_in_chart(events, trill):
                i = next_unmasked(i + 1, masked, n)
                continue
            all_trills.append(trill)
            for k in range(trill['start_note_index'], trill['end_note_index'] + 1):
                masked.add(k)
            i = next_unmasked(consumed_end + 1, masked, n)
            continue

        # --- Step 4: Fan trills (4 notes) ---
        found = try_fan_trill(single_notes, masked, n, i, events)
        if found:
            trill, consumed_end = found
            if not verify_trill_in_chart(events, trill):
                i = next_unmasked(i + 1, masked, n)
                continue
            all_trills.append(trill)
            for k in range(trill['start_note_index'], trill['end_note_index'] + 1):
                masked.add(k)
            i = next_unmasked(consumed_end + 1, masked, n)
            continue

        # --- Step 5: Mini trills (3 notes) ---
        found = try_mini_trill(single_notes, masked, n, i, events)
        if found:
            trill, consumed_end = found
            if not verify_trill_in_chart(events, trill):
                i = next_unmasked(i + 1, masked, n)
                continue
            all_trills.append(trill)
            for k in range(trill['start_note_index'], trill['end_note_index'] + 1):
                masked.add(k)
            i = next_unmasked(consumed_end + 1, masked, n)
            continue

        i = next_unmasked(i + 1, masked, n)

    all_trills.sort(key=lambda t: t['start_event_index'])
    return all_trills


def next_unmasked(start, masked, n):
    """Return the first unmasked index >= start, or n if none found."""
    i = start
    while i < n:
        if i not in masked:
            return i
        i += 1
    return n


def try_anchor_trill(single_notes, masked, n, i, events):
    """Try to detect an anchor trill starting at single_notes[i].

    Returns (trill_dict, consumed_end_note_index) on success, or None.
    """
    a = single_notes[i]['position']

    if (i + 3 >= n or
        (i + 1) in masked or (i + 2) in masked or (i + 3) in masked or
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

    start_event_idx = single_notes[i]['index']
    end_event_idx = single_notes[j - 1]['index']

    if not is_range_valid(events, start_event_idx, end_event_idx):
        return None

    if not is_density_sufficient(single_notes[i]):
        return None

    output = reconstruct_trill(single_notes[i:j])
    alternates = tuple(single_notes[k]['position'] for k in range(i + 1, j, 2))
    return ({
        'kind': 'anchor',
        'output': output,
        'anchor': a,
        'alternates': alternates,
        'length': j - i,
        'start_event_index': start_event_idx,
        'end_event_index': end_event_idx,
        'start_note_index': i,
        'end_note_index': j - 1,
    }, j - 1)


def try_regular_trill(single_notes, masked, n, i, events):
    """Try to detect a regular trill (a, b, a, b, ...) starting at single_notes[i].

    Returns (trill_dict, consumed_end_note_index) on success, or None.
    """
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

    start_event_idx = single_notes[i]['index']
    end_event_idx = single_notes[j - 1]['index']

    if not is_range_valid(events, start_event_idx, end_event_idx):
        return None

    if not is_density_sufficient(single_notes[i]):
        return None

    output = reconstruct_trill(single_notes[i:j])
    return ({
        'kind': 'regular',
        'output': output,
        'positions': (a, b),
        'length': j - i,
        'start_event_index': start_event_idx,
        'end_event_index': end_event_idx,
        'start_note_index': i,
        'end_note_index': j - 1,
    }, j - 1)


FAN_PATTERNS = [
    (0, 2, 1, 3, "a,a+2,a+1,a+3"),
    (0, 3, 1, 2, "a,a+3,a+1,a+2"),
    (1, 2, 0, 3, "a+1,a+2,a,a+3"),
    (0, -2, -1, -3, "a,a-2,a-1,a-3"),
    (0, -3, -1, -2, "a,a-3,a-1,a-2"),
    (-1, -2, 0, -3, "a-1,a-2,a,a-3"),
]

CIRCULAR_PATTERNS = [
    (0, 1, -1, 2, -2, "a,a+1,a-1,a+2,a-2"),
    (0, -1, 1, -2, 2, "a,a-1,a+1,a-2,a+2"),
    (0, 1, -1, 2, -2, 3, "a,a+1,a-1,a+2,a-2,a+3"),
    (0, -1, 1, -2, 2, -3, "a,a-1,a+1,a-2,a+2,a-3"),
    (0, 1, -1, 2, -2, 3, -3, "a,a+1,a-1,a+2,a-2,a+3,a-3"),
    (0, -1, 1, -2, 2, -3, 3, "a,a-1,a+1,a-2,a+2,a-3,a+3"),
    (0, 1, -1, 2, -2, 3, -3, 4, "a,a+1,a-1,a+2,a-2,a+3,a-3,a+4"),
    (0, -1, 1, -2, 2, -3, 3, -4, "a,a-1,a+1,a-2,a+2,a-3,a+3,a-4"),
]


def try_fan_trill(single_notes, masked, n, i, events):
    """Try to detect a fan trill (4 notes) starting at single_notes[i].

    Fan trill patterns (4 notes): a,a+2,a+1,a+3 / a,a+3,a+1,a+2 / a+1,a+2,a,a+3
                                  a,a-2,a-1,a-3 / a,a-3,a-1,a-2 / a-1,a-2,a,a-3

    Returns (trill_dict, consumed_end_note_index) on success, or None.
    """
    if i + 3 >= n:
        return None

    if (i + 1) in masked or (i + 2) in masked or (i + 3) in masked:
        return None

    p0 = single_notes[i]['position']
    p1 = single_notes[i + 1]['position']
    p2 = single_notes[i + 2]['position']
    p3 = single_notes[i + 3]['position']

    if not all(pos in '12345678' for pos in [p0, p1, p2, p3]):
        return None

    a = int(p0)
    b0, b1, b2, b3 = int(p0), int(p1), int(p2), int(p3)

    fan_name = None
    for off0, off1, off2, off3, name in FAN_PATTERNS:
        if (b0 == add_mod_btn(a, off0) and
            b1 == add_mod_btn(a, off1) and
            b2 == add_mod_btn(a, off2) and
            b3 == add_mod_btn(a, off3)):
            fan_name = name
            break

    if not fan_name:
        return None

    j = i + 4

    start_event_idx = single_notes[i]['index']
    end_event_idx = single_notes[j - 1]['index']

    if not is_range_valid(events, start_event_idx, end_event_idx):
        return None

    if not is_density_sufficient(single_notes[i]):
        return None

    output = reconstruct_trill(single_notes[i:j])
    return ({
        'kind': 'fan',
        'output': output,
        'positions': (p0, p1, p2, p3),
        'pattern': fan_name,
        'length': j - i,
        'start_event_index': start_event_idx,
        'end_event_index': end_event_idx,
        'start_note_index': i,
        'end_note_index': j - 1,
    }, j - 1)


def try_circular_trill(single_notes, masked, n, i, events):
    """Try to detect a circular trill (5-8 notes) starting at single_notes[i].

    Circular trill patterns wind around the anchor: a,a+1,a-1,a+2,a-2 / a,a-1,a+1,a-2,a+2 etc.

    Returns (trill_dict, consumed_end_note_index) on success, or None.
    """
    if i + 4 >= n:
        return None

    p0 = single_notes[i]['position']
    if p0 not in '12345678':
        return None

    a = int(p0)

    circular_name = None
    circular_len = 0

    for pattern in CIRCULAR_PATTERNS:
        offsets = pattern[:-1]
        name = pattern[-1]
        m = len(offsets)

        if i + m > n:
            continue

        if any(i + k in masked for k in range(1, m)):
            continue

        positions = [single_notes[i + k]['position'] for k in range(m)]
        if not all(pos in '12345678' for pos in positions):
            continue

        ints = [int(pos) for pos in positions]

        match = True
        for k, off in enumerate(offsets):
            if ints[k] != add_mod_btn(a, off):
                match = False
                break

        if match and m > circular_len:
            circular_name = name
            circular_len = m

    if not circular_name:
        return None

    j = i + circular_len

    start_event_idx = single_notes[i]['index']
    end_event_idx = single_notes[j - 1]['index']

    if not is_range_valid(events, start_event_idx, end_event_idx):
        return None

    if not is_density_sufficient(single_notes[i]):
        return None

    output = reconstruct_trill(single_notes[i:j])
    return ({
        'kind': 'circular',
        'output': output,
        'positions': tuple(single_notes[k]['position'] for k in range(i, j)),
        'pattern': circular_name,
        'length': j - i,
        'start_event_index': start_event_idx,
        'end_event_index': end_event_idx,
        'start_note_index': i,
        'end_note_index': j - 1,
    }, j - 1)


def try_mini_trill(single_notes, masked, n, i, events):
    """Try to detect a mini trill (3 notes) starting at single_notes[i].

    Returns (trill_dict, consumed_end_note_index) on success, or None.
    """
    if i + 2 >= n:
        return None

    if (i + 1) in masked or (i + 2) in masked:
        return None

    p0 = single_notes[i]['position']
    p1 = single_notes[i + 1]['position']
    p2 = single_notes[i + 2]['position']

    is_type1 = (p0 == p2 and p0 != p1)

    is_type2 = False
    type2_name = None
    if p0 in '12345678' and p1 in '12345678' and p2 in '12345678':
        a = int(p0)
        b1 = int(p1)
        b2 = int(p2)
        checks = [
            (2, 1, "a,a+2,a+1"),
            (3, 1, "a,a+3,a+1"),
            (3, 2, "a,a+3,a+2"),
            (-2, -1, "a,a-2,a-1"),
            (-3, -1, "a,a-3,a-1"),
            (-3, -2, "a,a-3,a-2"),
        ]
        for off1, off2, name in checks:
            if b1 == add_mod_btn(a, off1) and b2 == add_mod_btn(a, off2):
                is_type2 = True
                type2_name = name
                break

    is_type3 = False
    type3_name = None
    if p0 in '12345678' and p1 in '12345678' and p2 in '12345678':
        a = int(p1)
        b0 = int(p0)
        b2 = int(p2)
        checks = [
            (1, 2, "a+1,a,a+2"),
            (-1, -2, "a-1,a,a-2"),
            (2, 3, "a+2,a,a+3"),
            (1, 3, "a+1,a,a+3"),
            (-2, -3, "a-2,a,a-3"),
            (-1, -3, "a-1,a,a-3"),
        ]
        for off0, off2, name in checks:
            if b0 == add_mod_btn(a, off0) and b2 == add_mod_btn(a, off2):
                is_type3 = True
                type3_name = name
                break

    if not (is_type1 or is_type2 or is_type3):
        return None

    start_event_idx = single_notes[i]['index']
    end_event_idx = single_notes[i + 2]['index']

    if not is_range_valid(events, start_event_idx, end_event_idx):
        return None

    if not is_density_sufficient(single_notes[i]):
        return None

    output = reconstruct_trill(single_notes[i:i + 3])
    if is_type1:
        pattern_label = 'type1'
    elif is_type2:
        pattern_label = 'type2'
    else:
        pattern_label = 'type3'

    return ({
        'kind': 'mini',
        'output': output,
        'positions': (p0, p1, p2),
        'pattern': pattern_label,
        'type2_name': type2_name,
        'type3_name': type3_name,
        'start_event_index': start_event_idx,
        'end_event_index': end_event_idx,
        'start_note_index': i,
        'end_note_index': i + 2,
    }, i + 2)


def mask_chart(events, trills):
    """Rebuild the chart string with every trill note replaced by an empty beat."""
    masked = set()
    for trill in trills:
        for idx in range(trill['start_event_index'], trill['end_event_index'] + 1):
            masked.add(idx)

    parts = []
    for i, ev in enumerate(events):
        if i in masked and ev['type'] == 'note' and not ev.get('is_double'):
            # Preserve any leading divider / BPM tokens, drop the note body
            raw = ev['raw']
            m = re.match(r'^(\{[^}]*\}|\([^)]*\))+', raw)
            if m:
                parts.append(m.group(0))
            else:
                parts.append('')
        else:
            parts.append(ev['raw'])

    return ','.join(parts)


def detect_trills_iterative(filepath):
    """Detect trills iteratively: detect -> mask -> re-detect until no new trills found."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    title = None
    start_line = 0
    for idx, line in enumerate(content.split('\n')):
        if line.strip().startswith('&title'):
            title = line.strip()[6:].strip()
            start_line = idx + 1
            break

    content = '\n'.join(content.split('\n')[start_line:])

    bpm_match = re.match(r'^\s*\((\d+(?:\.\d+)?)\)', content)
    bpm = float(bpm_match.group(1)) if bpm_match else 1

    all_passes = []
    current_content = content
    pass_num = 1

    while True:
        events, _ = parse_chart(current_content)
        trills = detect_patterns(events)
        if not trills:
            break
        masked = mask_chart(events, trills)
        all_passes.append({
            'pass': pass_num,
            'trills': trills,
            'events': events,
        })
        current_content = masked
        pass_num += 1

    return all_passes, current_content, bpm, title


def format_trill(trill):
    note_range = f"note {trill['start_note_index']}-{trill['end_note_index']}"
    if trill['kind'] == 'anchor':
        return f"{note_range}: anchor={trill['anchor']} alternates={trill['alternates']} ({trill['length']} notes): {trill['output']}"
    elif trill['kind'] == 'regular':
        return f"{note_range}: {trill['positions']} ({trill['length']} notes): {trill['output']}"
    elif trill['kind'] == 'fan':
        return f"{note_range}: {trill['positions']} [{trill['pattern']}]: {trill['output']}"
    elif trill['kind'] == 'circular':
        return f"{note_range}: {trill['positions']} [{trill['pattern']}]: {trill['output']}"
    else:
        info = f"{note_range}: {trill['positions']} [{trill['pattern']}"
        if trill.get('type2_name'):
            info += f": {trill['type2_name']}"
        if trill.get('type3_name'):
            info += f": {trill['type3_name']}"
        info += f"]: {trill['output']}"
        return info


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    debug_dir = os.path.join(base_dir, 'debugcharts')
    charts_dir = os.path.join(base_dir, 'charts')
    output_file = os.path.join(base_dir, 'trill_output.txt')

    if os.path.isdir(debug_dir) and any(f.endswith('.txt') for f in os.listdir(debug_dir)):
        charts_dir = debug_dir
        print(f"Using debug directory: {charts_dir}")

    if not os.path.isdir(charts_dir):
        print(f"Directory not found: {charts_dir}")
        return

    file_lines = []

    for filename in sorted(os.listdir(charts_dir)):
        if not filename.endswith('.txt') or filename == 'trill_output.txt':
            continue
        filepath = os.path.join(charts_dir, filename)
        all_passes, final_masked, bpm, chart_title = detect_trills_iterative(filepath)
        display_title = chart_title if chart_title else filename
        diff_match = re.search(r' - ([^.]+)\.txt$', filename)
        if diff_match:
            display_title = f"{display_title} - {diff_match.group(1)}"
        try:
            print(f"\n=== {display_title} ===")
            file_lines.append(f"=== {display_title} ===")
        except UnicodeEncodeError:
            print(f"\n=== {display_title.encode('utf-8', 'replace').decode('utf-8')} ===")
            file_lines.append(f"=== {display_title} ===")
        if not all_passes:
            print("  No trills detected.")
            file_lines.append("  No trills detected.")
            continue

        total_trills = 0
        total_notes = 0
        divider_counts = {}
        for pass_data in all_passes:
            events = pass_data['events']
            total_trills += len(pass_data['trills'])
            for trill in pass_data['trills']:
                start = trill['start_event_index']
                end = trill['end_event_index']
                count = end - start + 1
                total_notes += count
                start_div = events[start].get('active_divider')
                start_div_val = get_divider_value(start_div) if start_div else 0
                has_high_div = any(get_divider_value(events[k].get('active_divider', '')) > 64 
                                   for k in range(start, end + 1))
                for k in range(start, end + 1):
                    div = events[k].get('active_divider')
                    if div:
                        if has_high_div and start_div_val > 0:
                            div = start_div
                        divider_counts[div] = divider_counts.get(div, 0) + 1

        points = 0.0
        for d, c in divider_counts.items():
            m = re.match(r'^\{(\d+(?:\.\d+)?)\}$', d)
            if m:
                points += float(m.group(1)) * c
            else:
                start_m = re.match(r'^\{#(\d+(?:\.\d+)?)\}$', d)
                if start_m:
                    points += float(start_m.group(1)) * c
        points *= bpm

        summary = f"  {total_trills} trill(s) | {total_notes} note(s) | {len(all_passes)} pass(es) | BPM: {bpm}"
        points_line = f"  trill points: {points:.1f} | avg: {points/total_notes:.2f}/note"
        print(summary)
        print(points_line)
        file_lines.append(summary)
        file_lines.append(points_line)

        sorted_dividers = []
        for d in divider_counts:
            m = re.match(r'^\{(\d+(?:\.\d+)?)\}$', d)
            if m:
                sorted_dividers.append((float(m.group(1)), d))
            else:
                sm = re.match(r'^\{#(\d+(?:\.\d+)?)\}$', d)
                if sm:
                    sorted_dividers.append((float(sm.group(1)), d))
                else:
                    sorted_dividers.append((0.0, d))
        
        for _, d in sorted(sorted_dividers):
            c = divider_counts[d]
            m = re.match(r'^\{(\d+(?:\.\d+)?)\}$', d)
            if m:
                pts = float(m.group(1)) * c * bpm
            else:
                sm = re.match(r'^\{#(\d+(?:\.\d+)?)\}$', d)
                if sm:
                    pts = float(sm.group(1)) * c * bpm
                else:
                    pts = 0.0
            divider_line = f"    {d}: {c} note(s) -> {pts:.1f} pts"
            file_lines.append(divider_line)

        for pass_data in all_passes:
            pass_line = f"  --- pass {pass_data['pass']} ({len(pass_data['trills'])} trill(s)) ---"
            file_lines.append(pass_line)
            for trill in pass_data['trills']:
                try:
                    trill_line = f"    {format_trill(trill)}"
                    file_lines.append(trill_line)
                except UnicodeEncodeError:
                    trill_enc = format_trill(trill).encode('utf-8', 'replace').decode('utf-8')
                    file_lines.append(f"    {trill_enc}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(file_lines))

    print(f"\n--- METHOD ---")
    print(f"  Points = sum(divider_value * note_count) * BPM")


if __name__ == '__main__':
    main()
