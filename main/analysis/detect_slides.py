import io
import json
import math
import os
import re
import sys

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# Load adjacent sensor data
ADJACENT_SENSORS = {}
adjacent_file = os.path.join(os.path.dirname(__file__), 'adjacent_note.txt')
if os.path.exists(adjacent_file):
    with open(adjacent_file, 'r', encoding='utf-8') as f:
        ADJACENT_SENSORS = json.load(f)


def is_sensor_nearby(sensor_a, sensor_b):
    """Check if two sensors are the same or adjacent."""
    a_key = '{}{}'.format(sensor_a[0].upper(), sensor_a[1])
    b_key = '{}{}'.format(sensor_b[0].upper(), sensor_b[1])
    if a_key == b_key:
        return True
    adj = ADJACENT_SENSORS.get(a_key, [])
    return b_key in adj


def get_last_sensor_for_slide(slide):
    """Get the last sensor of a slide event."""
    for s in slide['slides']:
        segments = s['segments']
        sensors = get_slide_sensors_for_path(segments, s['start'])
        if sensors:
            return sensors[-1]
    return None


def get_all_sensors_for_slide(slide):
    """Get all unique sensors of a slide event."""
    all_sensors = set()
    for s in slide['slides']:
        segments = s['segments']
        sensors = get_slide_sensors_for_path(segments, s['start'])
        for sensor in sensors:
            all_sensors.add(sensor)
    return all_sensors


SLIDE_NODE_SEQUENCE = {
    'straightLine': [  # - symbol
        None,  # 0 dist
        None,  # 1 dist
        [['a1'], ['a2', 'b2'], ['a3']],  # 2 dist
        [['a1'], ['b2'], ['b3'], ['a4']],  # 3 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b5'], ['a5']],  # 4 dist
        None,  # 5 dist
        None,  # 6 dist
        None  # 7 dist
    ],
    'circumferenceCW': [  # > symbol
        [['a1'], ['a2'], ['a3'], ['a4'], ['a5'], ['a6'], ['a7'], ['a8'], ['a1']],  # 0 dist
        [['a1'], ['a2']],  # 1 dist
        [['a1'], ['a2'], ['a3']],  # 2 dist
        [['a1'], ['a2'], ['a3'], ['a4']],  # 3 dist
        [['a1'], ['a2'], ['a3'], ['a4'], ['a5']],  # 4 dist
        [['a1'], ['a2'], ['a3'], ['a4'], ['a5'], ['a6']],  # 5 dist
        [['a1'], ['a2'], ['a3'], ['a4'], ['a5'], ['a6'], ['a7']],  # 6 dist
        [['a1'], ['a2'], ['a3'], ['a4'], ['a5'], ['a6'], ['a7'], ['a8']]  # 7 dist
    ],
    'circumferenceCCW': [  # < symbol
        [['a1'], ['a8'], ['a7'], ['a6'], ['a5'], ['a4'], ['a3'], ['a2'], ['a1']],  # 0 dist
        [['a1'], ['a8']],  # 1 dist
        [['a1'], ['a8'], ['a7']],  # 2 dist
        [['a1'], ['a8'], ['a7'], ['a6']],  # 3 dist
        [['a1'], ['a8'], ['a7'], ['a6'], ['a5']],  # 4 dist
        [['a1'], ['a8'], ['a7'], ['a6'], ['a5'], ['a4']],  # 5 dist
        [['a1'], ['a8'], ['a7'], ['a6'], ['a5'], ['a4'], ['a3']],  # 6 dist
        [['a1'], ['a8'], ['a7'], ['a6'], ['a5'], ['a4'], ['a3'], ['a2']]  # 7 dist
    ],
    'arcAlongCenterCW': [  # p symbol
        [['a1'], ['b2'], ['b3'], ['b4'], ['b5'], ['b6'], ['b7'], ['b8'], ['a1']],  # 0 dist
        [['a1'], ['b2'], ['b3'], ['b4'], ['b5'], ['b6'], ['b7'], ['b8'], ['b1'], ['a2']],  # 1 dist
        [['a1'], ['b2'], ['b3'], ['b4'], ['b5'], ['b6'], ['b7'], ['b8'], ['b1'], ['b2'], ['a3']],  # 2 dist
        [['a1'], ['b2'], ['b3'], ['b4'], ['b5'], ['b6'], ['b7'], ['b8'], ['b1'], ['b2'], ['b3'], ['a4']],  # 3 dist
        [['a1'], ['b2'], ['b3'], ['b4'], ['a5']],  # 4 dist
        [['a1'], ['b2'], ['b3'], ['b4'], ['b5'], ['a6']],  # 5 dist
        [['a1'], ['b2'], ['b3'], ['b4'], ['b5'], ['b6'], ['a7']],  # 6 dist
        [['a1'], ['b2'], ['b3'], ['b4'], ['b5'], ['b6'], ['b7'], ['a8']]  # 7 dist
    ],
    'arcAlongCenterCCW': [  # q symbol
        [['a1'], ['b8'], ['b7'], ['b6'], ['b5'], ['b4'], ['b3'], ['b2'], ['a1']],  # 0 dist
        [['a1'], ['b8'], ['b7'], ['b6'], ['b5'], ['b4'], ['b3'], ['a2']],  # 1 dist
        [['a1'], ['b8'], ['b7'], ['b6'], ['b5'], ['b4'], ['a3']],  # 2 dist
        [['a1'], ['b8'], ['b7'], ['b6'], ['b5'], ['a4']],  # 3 dist
        [['a1'], ['b8'], ['b7'], ['b6'], ['a5']],  # 4 dist
        [['a1'], ['b8'], ['b7'], ['b6'], ['b5'], ['b4'], ['b3'], ['b2'], ['b1'], ['b8'], ['b7'], ['a6']],  # 5 dist
        [['a1'], ['b8'], ['b7'], ['b6'], ['b5'], ['b4'], ['b3'], ['b2'], ['b1'], ['b8'], ['a7']],  # 6 dist
        [['a1'], ['b8'], ['b7'], ['b6'], ['b5'], ['b4'], ['b3'], ['b2'], ['b1'], ['a8']]  # 7 dist
    ],
    'centerBounce': [  # v symbol
        None,  # 0 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b2'], ['a2']],  # 1 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b3'], ['a3']],  # 2 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b4'], ['a4']],  # 3 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b5'], ['a5']],  # 4 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b6'], ['a6']],  # 5 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b7'], ['a7']],  # 6 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b8'], ['a8']]  # 7 dist
    ],
    'arcToSideCW': [  # pp symbol
        [['a1'], ['b1'], ['c1', 'c2'], ['b6'], ['a7'], ['a8'], ['a1']],  # 0 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b6'], ['a7'], ['a8'], ['a1', 'b1'], ['a2']],  # 1 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b6'], ['a7'], ['a8'], ['b1'], ['b2'], ['a3']],  # 2 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b6'], ['a7'], ['a8'], ['b1'], ['c1', 'c2'], ['b3', 'b4'], ['a4']],  # 3 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b6'], ['a7'], ['a8'], ['b1'], ['c1', 'c2'], ['b5'], ['a5']],  # 4 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b6'], ['a7'], ['a8'], ['b1'], ['c1', 'c2'], ['b6'], ['a6']],  # 5 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b6'], ['a7']],  # 6 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b6'], ['a7'], ['a8']]  # 7 dist
    ],
    'arcToSideCCW': [  # qq symbol
        [['a1'], ['b1'], ['c1', 'c2'], ['b4'], ['a3'], ['a2'], ['a1']],  # 0 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b4'], ['a3'], ['a2']],  # 1 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b4'], ['a3']],  # 2 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b4'], ['a3'], ['a2'], ['b1'], ['c1', 'c2'], ['b4'], ['a4']],  # 3 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b4'], ['a3'], ['a2'], ['b1'], ['c1', 'c2'], ['b5'], ['a5']],  # 4 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b4'], ['a3'], ['a2'], ['b1'], ['b8', 'c1', 'c2'], ['b7', 'b6'], ['a6']],  # 5 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b4'], ['a3'], ['a2'], ['b1'], ['b8'], ['a7']],  # 6 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b4'], ['a3'], ['a2'], ['a1', 'b1'], ['a8']]  # 7 dist
    ],
    'fanSegments': [  # w symbol
        None,  # 0 dist
        None,  # 1 dist
        None,  # 2 dist
        [['a1'], ['b8'], ['b7'], ['a6', 'd6']],  # 3 dist
        [['a1'], ['b1'], ['c1', 'c2'], ['b5'], ['a5']],  # 4 dist
        [['a1'], ['b2'], ['b3'], ['a4', 'd5']],  # 5 dist
        None,  # 6 dist
        None,  # 7 dist
        None   # 8 dist
    ],
    'zigzagS': [  # s symbol
        None,  # 0 dist
        None,  # 1 dist
        None,  # 2 dist
        None,  # 3 dist
        [['a1'], ['b8'], ['b7'], ['c1', 'c2'], ['b3'], ['b4'], ['a5']],  # 4 dist
        None,  # 5 dist
        None,  # 6 dist
        None   # 7 dist
    ],
    'zigzagZ': [  # z symbol
        None,  # 0 dist
        None,  # 1 dist
        None,  # 2 dist
        None,  # 3 dist
        [['a1'], ['b2'], ['b3'], ['c1', 'c2'], ['b7'], ['b6'], ['a5']],  # 4 dist
        None,  # 5 dist
        None,  # 6 dist
        None   # 7 dist
    ]
}


def get_symbol_key(symbol):
    """Map slide symbol to node sequence key."""
    symbol_map = {
        '-': 'straightLine',
        'V': 'straightLine',
        '>': 'circumferenceCW',
        '<': 'circumferenceCCW',
        'p': 'arcAlongCenterCW',
        'q': 'arcAlongCenterCCW',
        'v': 'centerBounce',
        'pp': 'arcToSideCW',
        'qq': 'arcToSideCCW',
        'w': 'fanSegments',
        's': 'zigzagS',
        'z': 'zigzagZ'
    }
    return symbol_map.get(symbol)


def wrap_id(id_val):
    """Wrap sensor ID to 1-8 range."""
    return ((id_val - 1) % 8) + 1


def shift_sensor(sensor, shift):
    """Shift a sensor by the given amount."""
    group, gid = sensor
    if group in ('a', 'b', 'd', 'e'):
        new_id = wrap_id(int(gid) + shift)
        return (group, new_id)
    elif group == 'c':
        return sensor  # c1, c2 don't shift
    return sensor


def parse_duration(dur_str):
    """Parse duration string like '[8:3]' into (denominator, numerator) tuple."""
    if not dur_str:
        return None
    m = re.match(r'\[(\d+):(\d+)\]', dur_str)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return None


def sum_durations(path_segments):
    """Sum durations of all segments in a path.

    Duration format is [denominator:numerator].
    All durations are converted to the first segment's denominator.
    Segments without explicit duration default to [4:1] ONLY if
    multiple segments have explicit durations (each segment is timed).
    If only the last segment has a duration, that duration applies
    to the entire path.
    Example: [8:3] + [4:2] = [8:7]  (3 + 2*2 = 7 eighth-notes)
    Returns combined duration string.
    """
    durations = []
    explicit_count = 0
    for seg in path_segments:
        dur = parse_duration(seg.get('duration'))
        if dur:
            durations.append(dur)
            explicit_count += 1
        else:
            durations.append(None)

    if explicit_count == 0:
        return '[4:1]'

    # If only one segment has duration (typically the last), use it as total
    if explicit_count == 1:
        for dur in durations:
            if dur:
                return '[{}:{}]'.format(dur[0], dur[1])

    # Multiple segments have durations - sum them with defaults for missing ones
    valid_durations = []
    for dur in durations:
        if dur:
            valid_durations.append(dur)
        else:
            valid_durations.append((4, 1))

    # Use first segment's denominator as base
    base_denom = valid_durations[0][0]
    total_num = 0

    for denom, num in valid_durations:
        # Convert to base denominator
        if denom == 0:
            continue
        if base_denom % denom == 0:
            factor = base_denom // denom
            total_num += num * factor
        elif denom % base_denom == 0:
            factor = denom // base_denom
            total_num += num // factor
        else:
            # Find LCM for incompatible denominators
            def gcd(a, b):
                while b:
                    a, b = b, a % b
                return a
            def lcm(a, b):
                return a * b // gcd(a, b)
            l = lcm(base_denom, denom)
            base_factor = l // base_denom
            total_num *= base_factor
            total_num += num * (l // denom)
            base_denom = l

    return '[{}:{}]'.format(base_denom, total_num)


def get_slide_sensors_for_path(path_segments, start):
    """Calculate all sensors that a single path goes through.

    path_segments: list of segments forming one continuous path.
    Returns a list of (group, id) tuples for all sensors in the path.
    """
    sensors = []
    current_pos = int(start)

    for seg in path_segments:
        sym = seg['symbol']
        key = get_symbol_key(sym)
        if not key:
            continue

        ends = seg['ends']
        for end in ends:
            end_pos = int(end)

            # Calculate distance and determine correct data key based on symbol
            # and which half the current button is in.
            # Upper half (7,8,1,2): > = CW, < = CCW
            # Lower half (3,4,5,6): > = CCW, < = CW
            # p, pp are always CW; q, qq are always CCW
            is_upper = current_pos in (7, 8, 1, 2)
            use_key = key

            if sym == '>':
                if is_upper:
                    dist = (end_pos - current_pos) % 8  # CW
                else:
                    # > for lower half means CCW, use circumferenceCCW data
                    dist = (current_pos - end_pos) % 8
                    use_key = 'circumferenceCCW'
            elif sym == '<':
                if is_upper:
                    dist = (current_pos - end_pos) % 8  # CCW
                else:
                    # < for lower half means CW, use circumferenceCW data
                    dist = (end_pos - current_pos) % 8
                    use_key = 'circumferenceCW'
            elif sym in ('p', 'pp'):
                dist = (end_pos - current_pos) % 8  # Always CW
            elif sym in ('q', 'qq'):
                dist = (current_pos - end_pos) % 8  # Always CCW
            else:
                # Direction-independent (-, V, v, w, s, z): use shorter path
                raw_diff = abs(end_pos - current_pos)
                dist = min(raw_diff, 8 - raw_diff)

            if dist == 0:
                dist = 8

            seq = SLIDE_NODE_SEQUENCE.get(use_key, [])
            if dist < len(seq) and seq[dist]:
                shift = current_pos - 1
                for pos_sensors in seq[dist]:
                    for sensor in pos_sensors:
                        shifted = shift_sensor(sensor, shift)
                        sensors.append(shifted)

            current_pos = end_pos

    return sensors


def format_sensors(sensors):
    """Format sensors for display."""
    if not sensors:
        return ''
    return ', '.join(['{}{}'.format(g, i) for g, i in sensors])


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


def get_divider_value(divider_str):
    """Extract denominator from divider string like '{16}' -> 16."""
    if not divider_str:
        return 4  # Default quarter note
    m = re.match(r'\{#?(\d+(?:\.\d+)?)\}', divider_str)
    if m:
        return float(m.group(1))
    return 4


def get_beat_duration(divider_str):
    """Get the duration of one beat in beat units."""
    div = get_divider_value(divider_str)
    if div > 0:
        return 1.0 / div
    return 0.25


def parse_chart(content):
    """Parse simai chart content into a list of beat events with line tracking and time positions.

    In simai, each line is a measure (4 beats by default).
    After each line, time advances to the next measure boundary.
    """
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
    current_divider = None
    current_bpm = None
    current_time = 0.0
    measure_length = 4.0  # Default 4/4 measure = 4 beats
    leading_re = re.compile(r'^(\{[^}]*\}|\([^)]*\))+')

    for line_num, line in enumerate(lines, start=start_line+1):
        line = line.strip()
        if not line or line.startswith('||'):
            continue
        m = re.match(r'^\d+:\s*', line)
        if m:
            line = line[m.end():]

        measure_start = current_time
        beat_fields = line.split(',')
        has_content = False
        for raw_beat in beat_fields:
            raw = raw_beat.strip()
            active_divider = current_divider
            active_bpm = current_bpm
            remainder = raw
            beat_duration = get_beat_duration(active_divider)

            m = leading_re.match(raw)
            if m:
                leading = m.group(0)
                for token in re.findall(r'\{(\d+(?:\.\d+)?)\}|\{ #(\d+(?:\.\d+)?)\}|\(([^)]+)\)', leading):
                    if token[0]:
                        active_divider = '{' + token[0] + '}'
                        current_divider = active_divider
                    elif token[1]:
                        active_divider = '{#' + token[1] + '}'
                        current_divider = active_divider
                    elif token[2]:
                        active_bpm = '(' + token[2] + ')'
                        current_bpm = active_bpm
                remainder = raw[m.end():].strip()
                # Recalculate beat duration after potential divider change
                beat_duration = get_beat_duration(current_divider)

            event_idx = len(events)
            event_time = current_time
            if not remainder:
                # Check if this field is pure metadata (BPM/divider only)
                # vs an actual empty beat position within a measure
                leading_match = leading_re.match(raw)
                is_metadata_only = leading_match and leading_match.group(0) == raw
                events.append({'type': 'empty', 'raw': raw, 'event_idx': event_idx,
                               'active_divider': active_divider, 'active_bpm': active_bpm,
                               'h1': None, 'h2': None, 'line': line_num,
                               'time': event_time, 'note_count': 0, 'hold_count': 0})
                if not is_metadata_only:
                    current_time += beat_duration
                continue

            has_content = True
            slides = extract_slides(remainder)
            if slides:
                nc, hc = count_notes_and_holds(remainder)
                events.append({'type': 'slide', 'raw': raw, 'event_idx': event_idx,
                               'slides': slides,
                               'active_divider': active_divider, 'active_bpm': active_bpm,
                               'line': line_num, 'time': event_time,
                               'note_count': nc, 'hold_count': hc})
            else:
                is_double = '/' in remainder or '`' in remainder or (remainder.isdigit() and len(remainder) >= 2)
                if is_double:
                    if '/' in remainder or '`' in remainder:
                        parts = re.split(r'[/`]', remainder)
                        h1 = parts[0] if len(parts) > 0 else None
                        h2 = parts[1] if len(parts) > 1 else None
                    else:
                        h1 = remainder[0] if len(remainder) >= 1 else None
                        h2 = remainder[1] if len(remainder) >= 2 else None
                    pos1 = extract_position(h1)
                    pos2 = extract_position(h2) if h2 else None
                    nc, hc = count_notes_and_holds(remainder)
                    events.append({'type': 'note', 'raw': raw, 'is_double': True, 'event_idx': event_idx,
                                   'position': None, 'h1': pos1, 'h2': pos2,
                                   'active_divider': active_divider, 'active_bpm': active_bpm,
                                   'line': line_num, 'time': event_time,
                                   'note_count': nc, 'hold_count': hc})
                else:
                    pos = extract_position(remainder)
                    nc, hc = count_notes_and_holds(remainder)
                    events.append({'type': 'note', 'raw': raw, 'is_double': False, 'event_idx': event_idx,
                                   'position': pos, 'h1': pos, 'h2': None,
                                   'active_divider': active_divider, 'active_bpm': active_bpm,
                                   'line': line_num, 'time': event_time,
                                   'note_count': nc, 'hold_count': hc})
            current_time += beat_duration

        # After each line with actual content, advance to next measure boundary.
        # Use max so that long lines don't cause time to reset backwards.
        if has_content:
            current_time = max(current_time, measure_start + measure_length)
    return events, title


def extract_slides(remainder):
    """Extract slide information from a beat remainder.

    A beat may contain slides mixed with non-slide notes (e.g., '1s5/Cf').
    Only the parts that parse as valid slides are returned.
    """
    if not remainder:
        return None

    parts = re.split(r'/', remainder)
    slides = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        slide = parse_single_slide(part)
        if slide:
            slides.append(slide)

    return slides if slides else None


def get_slide_duration(slides):
    """Get total duration of a slide event in beat units.

    Returns the maximum duration across all slide paths.
    If only one segment has a duration, that's the total duration.
    """
    max_dur = 0.0
    for s in slides:
        segments = s['segments']
        explicit_count = sum(1 for seg in segments if parse_duration(seg.get('duration')))

        if explicit_count == 0:
            dur = 0.25  # Default [4:1]
        elif explicit_count == 1:
            # Only one segment has duration - use it as total
            dur = 0.0
            for seg in segments:
                parsed = parse_duration(seg.get('duration'))
                if parsed:
                    dur = parsed[1] / parsed[0]
                    break
        else:
            # Multiple segments have durations - sum them
            dur = 0.0
            for seg in segments:
                parsed = parse_duration(seg.get('duration'))
                if parsed:
                    dur += parsed[1] / parsed[0]
                else:
                    dur += 0.25  # Default [4:1] for timed segments
        max_dur = max(max_dur, dur)
    return max_dur


def detect_slides(events):
    """Detect slides in the chart."""
    slide_events = []

    for ev in events:
        if ev['type'] == 'slide':
            slide_events.append({
                'start_event_index': ev['event_idx'],
                'end_event_index': ev['event_idx'],
                'slides': ev['slides'],
                'line': ev['line'],
                'raw': ev['raw'],
                'active_divider': ev.get('active_divider'),
                'active_bpm': ev.get('active_bpm'),
                'time': ev.get('time', 0.0)
            })

    return slide_events


def detect_overlaps(slide_events):
    """Detect overlapping slides.

    A slide's total duration = delay + slide_duration.
    Another slide that starts before this one finishes is a potential splash.
    But we only mark it as splashy if the other slide's sensors overlap or
    are adjacent to the current slide's ending sensor.
    """
    overlaps = []
    delay = 0.25  # [4:1]

    for i, slide_a in enumerate(slide_events):
        dur_a = get_slide_duration(slide_a['slides'])
        end_a = slide_a['time'] + delay + dur_a
        last_sensor_a = get_last_sensor_for_slide(slide_a)

        for j, slide_b in enumerate(slide_events):
            if i == j:
                continue
            # Check if slide B starts after A but before A finishes
            if slide_a['time'] < slide_b['time'] < end_a:
                # Check if any sensor in B overlaps or is adjacent to A's ending sensor
                if last_sensor_a:
                    sensors_b = get_all_sensors_for_slide(slide_b)
                    is_splashy = any(is_sensor_nearby(last_sensor_a, s) for s in sensors_b)
                    if is_splashy:
                        overlaps.append({
                            'slide_a': slide_a,
                            'slide_b': slide_b,
                            'end_a': end_a,
                            'time_b': slide_b['time'],
                            'splashy': True
                        })
                else:
                    overlaps.append({
                        'slide_a': slide_a,
                        'slide_b': slide_b,
                        'end_a': end_a,
                        'time_b': slide_b['time'],
                        'splashy': True
                    })

    return overlaps


def detect_umiyuri(slide_events, events):
    """Detect umiyuri-style patterns.

    Umiyuri pattern (original):
    1. Slide A starts at position X at time T
    2. At time T + delay (when Slide A starts moving), a note appears at position X
    3. At that same time T + delay, Slide B also appears
    4. The slides don't connect (no shared start/end buttons)

    Umiyuri pattern (extended - case 2):
    1. Slide A starts at position X at time T
    2. At time T + delay, another slide B starts at position X
    3. There are notes during slide A's duration [T, T+delay+dur]
    4. The slides don't connect (no shared start/end buttons)
    """
    umiyuris = []
    delay = 0.25  # [4:1]

    def get_slide_buttons(slide):
        buttons = set()
        for s in slide['slides']:
            buttons.add(s['start'])
            for seg in s['segments']:
                for end in seg['ends']:
                    buttons.add(end)
        return buttons

    def has_notes_during(slide_a):
        """Check if there are notes during slide A's active duration."""
        dur_a = get_slide_duration(slide_a['slides'])
        start_a = slide_a['time']
        end_a = start_a + delay + dur_a
        for ev in events:
            ev_time = ev['time']
            if start_a <= ev_time < end_a:
                if ev['type'] == 'note':
                    return True
                elif ev['type'] == 'slide':
                    # Check if slide event contains note parts
                    raw = ev['raw']
                    parts = raw.split('/')
                    for part in parts:
                        part = part.strip()
                        if not part or part.startswith('{') or part.startswith('('):
                            continue
                        if not any(sym in part for sym in SLIDE_SYMBOLS):
                            return True
        return False

    for i, slide_a in enumerate(slide_events):
        a_start_time = slide_a['time']
        a_move_time = a_start_time + delay  # When slide A starts moving
        a_idx = slide_a['start_event_index']

        # Get slide A's start position
        a_start_pos = None
        for s in slide_a['slides']:
            a_start_pos = s['start']
            break

        if not a_start_pos:
            continue

        # Check if there's a note at the exact move time at position X
        # Also check slide events that may contain notes (e.g., "7/8^3[8:1]")
        note_at_move = False
        for ev in events:
            if ev['line'] != slide_a['line']:
                continue
            if abs(ev['time'] - a_move_time) > 0.001:
                continue
            
            if ev['type'] == 'note':
                # Direct note event
                if ev.get('h1') == a_start_pos or ev.get('h2') == a_start_pos:
                    note_at_move = True
                    break
            elif ev['type'] == 'slide':
                # Slide event may contain notes before the slide
                raw = ev['raw']
                parts = raw.split('/')
                for part in parts:
                    part = part.strip()
                    if not part or part.startswith('{') or part.startswith('('):
                        continue
                    if not any(sym in part for sym in SLIDE_SYMBOLS):
                        m = re.match(r'^(\d+)', part)
                        if m and m.group(1) == a_start_pos:
                            note_at_move = True
                            break
                if note_at_move:
                    break

        # Find all slides that appear at the same move time
        all_slides_at_move = []
        for j, slide_b in enumerate(slide_events):
            if i == j:
                continue
            if abs(slide_b['time'] - a_move_time) > 0.001:
                continue
            all_slides_at_move.append(slide_b)

        # Filter to disjoint-button slides for original umiyuri
        disjoint_slides = []
        for slide_b in all_slides_at_move:
            buttons_a = get_slide_buttons(slide_a)
            buttons_b = get_slide_buttons(slide_b)
            if buttons_a.isdisjoint(buttons_b):
                disjoint_slides.append(slide_b)

        # Case 1: Original umiyuri - note at move time + another slide (disjoint)
        if note_at_move and disjoint_slides:
            for slide_b in disjoint_slides:
                umiyuris.append({
                    'slide_a': slide_a,
                    'slide_b': slide_b,
                    'move_time': a_move_time,
                    'type': 1
                })

        # Case 2: Extended umiyuri - another slide starts at same position + notes during duration
        # For this case, we check ALL slides at move time (not just disjoint ones)
        for slide_b in all_slides_at_move:
            b_start_pos = None
            for s in slide_b['slides']:
                b_start_pos = s['start']
                break
            if b_start_pos == a_start_pos:
                if has_notes_during(slide_a):
                    umiyuris.append({
                        'slide_a': slide_a,
                        'slide_b': slide_b,
                        'move_time': a_move_time,
                        'type': 2
                    })
                break  # Only need one match for case 2

    return umiyuris


def detect_connected_slides(slide_events):
    """Detect connected slides.

    A connected slide is one that starts at the end position of another slide
    and begins moving exactly when the first slide finishes.
    """
    connected = []
    delay = 0.25  # [4:1]

    for i, slide_a in enumerate(slide_events):
        dur_a = get_slide_duration(slide_a['slides'])
        end_time_a = slide_a['time'] + delay + dur_a

        # Get slide A's ending position(s)
        a_end_positions = set()
        for s in slide_a['slides']:
            for seg in s['segments']:
                for end in seg['ends']:
                    a_end_positions.add(end)

        if not a_end_positions:
            continue

        # Find slides that start at A's end position and begin moving when A finishes
        for j, slide_b in enumerate(slide_events):
            if i == j:
                continue

            # Slide B's move time
            move_time_b = slide_b['time'] + delay

            # Must start moving close to when A finishes
            if abs(move_time_b - end_time_a) > 0.001:
                continue

            # Check if B starts at any of A's end positions
            b_start = None
            for s in slide_b['slides']:
                b_start = s['start']
                break

            if b_start and b_start in a_end_positions:
                connected.append({
                    'slide_a': slide_a,
                    'slide_b': slide_b,
                    'end_time': end_time_a
                })

    return connected


def detect_delayed_slides(slides, events):
    """Detect delayed slides.

    A slide is considered delayed if there are 3 or more note entities or
    slide entities inside the duration of the entire slide (from appearance to finish).

    Counting rules:
    - Each note event counts as 1 note entity.
    - A slide event with mixed notes counts as 1 note entity (the note part only).
    - A pure slide event counts each individual slide it contains.
    - Double notes count as 1 note entity.
    """
    delayed = []
    delay = 0.25  # [4:1]

    for slide in slides:
        dur = get_slide_duration(slide['slides'])
        slide_start = slide['time']
        slide_end = slide['time'] + delay + dur

        count = 0
        for ev in events:
            ev_time = ev['time']
            # Event must be within the slide's entire duration
            if slide_start <= ev_time < slide_end:
                if ev['event_idx'] == slide['start_event_index']:
                    continue
                if ev['type'] == 'note':
                    count += 1
                elif ev['type'] == 'slide':
                    nc = ev.get('note_count', 0)
                    hc = ev.get('hold_count', 0)
                    if nc > 0 or hc > 0:
                        # Mixed event: count only the note part as 1 entity
                        count += 1
                    else:
                        # Pure slide event: count each individual slide
                        count += len(ev['slides'])

        if count >= 3:
            delayed.append({
                'slide': slide,
                'count': count
            })

    return delayed


def get_events_in_slide_duration(slide, events, slide_umiyuris=None):
    """Return a list of event descriptions inside a slide's duration.

    Includes notes, holds, and other slides between the slide's appearance
    and its end time, excluding the slide itself.
    """
    if slide_umiyuris is None:
        slide_umiyuris = {}

    delay = 0.25
    dur = get_slide_duration(slide['slides'])
    slide_start = slide['time']
    slide_end = slide_start + delay + dur

    # Get umiyuri type 2 paired slides
    umiyuri_type2_slides = set()
    for um in slide_umiyuris.get(slide['start_event_index'], []):
        if um.get('type') == 2:
            umiyuri_type2_slides.add(um['slide_b']['start_event_index'])

    items = []
    for ev in events:
        ev_time = ev['time']
        if ev['event_idx'] == slide['start_event_index']:
            continue

        include = False
        if slide_start <= ev_time < slide_end:
            include = True
        elif abs(ev_time - slide_end) < 0.001 and ev['type'] == 'slide':
            if ev['event_idx'] in umiyuri_type2_slides:
                include = True

        if include:
            if ev['type'] == 'note':
                h1 = ev.get('h1')
                h2 = ev.get('h2')
                if h1 and h2:
                    items.append(f"{h1}/{h2}")
                elif h1:
                    items.append(h1)
                else:
                    items.append(ev.get('raw', ''))
            elif ev['type'] == 'slide':
                items.append(ev.get('raw', ''))
    return items


def get_in_between_multiplier(slide, events, slide_umiyuris=None):
    """Calculate in-between multiplier for a slide.

    Counts notes, holds, and other slides during the slide's duration.
    General rule: exclude events at exactly slide_end time.
    Exception: for umiyuri type 2, count the paired slide even if at end time.
    """
    if slide_umiyuris is None:
        slide_umiyuris = {}

    delay = 0.25
    dur = get_slide_duration(slide['slides'])
    slide_start = slide['time']
    slide_end = slide_start + delay + dur

    # Get umiyuri type 2 paired slides
    umiyuri_type2_slides = set()
    for um in slide_umiyuris.get(slide['start_event_index'], []):
        if um.get('type') == 2:
            umiyuri_type2_slides.add(um['slide_b']['start_event_index'])

    note_count = 0
    hold_count = 0
    slide_count = 0

    for ev in events:
        ev_time = ev['time']
        if ev['event_idx'] == slide['start_event_index']:
            continue

        if slide_start <= ev_time < slide_end:
            if ev['type'] == 'note':
                note_count += ev.get('note_count', 0)
                hold_count += ev.get('hold_count', 0)
            elif ev['type'] == 'slide':
                slide_count += 1
                note_count += ev.get('note_count', 0)
                hold_count += ev.get('hold_count', 0)
        elif abs(ev_time - slide_end) < 0.001 and ev['type'] == 'slide':
            # Event exactly at slide_end
            if ev['event_idx'] in umiyuri_type2_slides:
                slide_count += 1
                note_count += ev.get('note_count', 0)
                hold_count += ev.get('hold_count', 0)

    base = 0.5 * note_count + 0.75 * hold_count + 1 * slide_count
    # Use 1 + base so that log is always >= 0, keeping multiplier >= 1.0
    log_part = math.log(1 + base, 3)
    multiplier = 1.0 + log_part
    return multiplier


SLIDE_SYMBOLS = {'pp', 'qq', 'w', 'p', 'q', 'v', 'V', '-', '>', '<', '^'}


def count_notes_and_holds(text):
    """Count regular notes/touch notes and holds in a text string.

    Returns (note_count, hold_count).
    Ignores slide parts and metadata tokens.
    """
    notes = 0
    holds = 0
    parts = re.split(r'[/`]', text)
    for part in parts:
        part = part.strip()
        if not part or part.startswith('{') or part.startswith('('):
            continue
        tmp = re.sub(r'\[.*?\]', '', part)
        if any(sym in tmp for sym in SLIDE_SYMBOLS):
            continue
        is_hold = 'h' in tmp
        matches = re.findall(r'([A-E]\d|C[12]?|[1-8])', tmp)
        if is_hold:
            holds += len(matches)
        else:
            notes += len(matches)
    return notes, holds


def parse_single_slide(text):
    """Parse a single slide string.

    Format: start_button + (symbol + button + [duration])+ + (*symbol + button + [duration])*
    Each segment has its own duration in [duration] format.
    '*' means the following segment branches from the start button.
    'b' marks start as break note, 'x' marks start as EX note.
    
    Tree model: Each '*' outputs a complete branch immediately, then we reset to start.
    Example: 1-2*-3-4*-5 -> 1-2 / 1-3-4 / 1-3-5
    """
    if not text or len(text) < 2:
        return None

    start_idx = 0
    break_start = False
    ex_start = False
    break_inline = False
    ex_inline = False
    if text[0] == 'b':
        break_start = True
        start_idx = 1
    if text[0] == 'x':
        ex_start = True
        start_idx = 1
    if text[0] in ('b', 'x') and len(text) > 1 and text[1] in ('b', 'x'):
        if text[1] == 'b':
            break_start = True
        if text[1] == 'x':
            ex_start = True
        start_idx = 2

    start = text[start_idx]
    if start not in '12345678':
        return None
    rest = text[start_idx+1:]

    segments = []
    current_symbol = None
    current_ends = []
    current_duration = None
    pending_star = False
    segment_connect = 'prev'

    i = 0
    while i < len(rest):
        if rest[i] == '*':
            if current_symbol and current_ends:
                segments.append({
                    'symbol': current_symbol,
                    'ends': list(current_ends),
                    'duration': current_duration,
                    'connect_to': segment_connect,
                    'has_star_after': True
                })
                current_symbol = None
                current_ends = []
                current_duration = None
            pending_star = True
            segment_connect = 'start'
            i += 1
        elif rest[i] == 'b':
            if not current_symbol and not current_ends and not segments:
                break_inline = True
            i += 1
        elif rest[i] == 'x':
            if not current_symbol and not current_ends and not segments:
                ex_inline = True
            i += 1
        elif rest[i:i+2] in ('pp', 'qq'):
            if current_symbol and current_ends:
                segments.append({
                    'symbol': current_symbol,
                    'ends': list(current_ends),
                    'duration': current_duration,
                    'connect_to': segment_connect,
                    'has_star_after': False
                })
                current_ends = []
                current_duration = None
            current_symbol = rest[i:i+2]
            if pending_star:
                segment_connect = 'start'
                pending_star = False
            i += 2
        elif rest[i] in 'wpqvV-sz><^':
            if current_symbol and current_ends:
                segments.append({
                    'symbol': current_symbol,
                    'ends': list(current_ends),
                    'duration': current_duration,
                    'connect_to': segment_connect,
                    'has_star_after': False
                })
                current_ends = []
                current_duration = None
            current_symbol = rest[i]
            if pending_star:
                segment_connect = 'start'
                pending_star = False
            i += 1
        elif rest[i] == '[':
            j = rest.find(']', i)
            if j > i:
                current_duration = rest[i:j+1]
                i = j + 1
            else:
                i += 1
        elif rest[i] in '12345678':
            if current_symbol:
                current_ends.append(rest[i])
            i += 1
        else:
            i += 1

    if current_symbol and current_ends:
        segments.append({
            'symbol': current_symbol,
            'ends': list(current_ends),
            'duration': current_duration,
            'connect_to': segment_connect,
            'has_star_after': False
        })

    if not segments:
        return None

    # Convert ^ to > or < based on shortest arc distance
    # Upper half (7,8,1,2): > = clockwise, < = counter-clockwise
    # Bottom half (3,4,5,6): > = counter-clockwise, < = clockwise
    prev_end = start
    for seg in segments:
        if seg['symbol'] == '^':
            end_btn = int(seg['ends'][0])
            if seg['connect_to'] == 'start':
                start_btn = int(start)
            else:
                start_btn = int(prev_end)
            cw_dist = (end_btn - start_btn) % 8
            ccw_dist = (start_btn - end_btn) % 8
            if cw_dist == 0:
                cw_dist = 8
            if ccw_dist == 0:
                ccw_dist = 8
            # Determine which half the start button is in
            start_num = int(start_btn)
            is_upper = start_num in (7, 8, 1, 2)
            # ^ cannot be used when distance is exactly 4 (half circle)
            if cw_dist == 4 and ccw_dist == 4:
                # Keep as ^ or convert to default
                seg['symbol'] = '^'
            elif cw_dist < ccw_dist:
                # Shorter path is clockwise
                seg['symbol'] = '>' if is_upper else '<'
            elif ccw_dist < cw_dist:
                # Shorter path is counter-clockwise
                seg['symbol'] = '<' if is_upper else '>'
            else:
                # Equal distance - default to clockwise (upper half: >, bottom half: <)
                seg['symbol'] = '>' if is_upper else '<'
        if seg['ends']:
            prev_end = seg['ends'][-1]

    return {
        'start': start,
        'break_start': break_start,
        'ex_start': ex_start,
        'break_inline': break_inline,
        'ex_inline': ex_inline,
        'segments': segments
    }

    if not segments:
        return None

    return {
        'start': start,
        'break_start': break_start,
        'ex_start': ex_start,
        'segments': segments
    }


def format_slide(slide, overlap_warnings=None, umiyuri_warnings=None, connected_warnings=None, delayed=False, in_between_events=None, score=None):
    """Format a slide for display."""
    line = slide['line']
    raw = slide['raw']

    slide_parts = []
    for s in slide['slides']:
        segments = s['segments']
        break_str = 'b' if s.get('break_start') else ''
        ex_str = 'x' if s.get('ex_start') else ''
        break_inline_str = 'b' if s.get('break_inline') else ''
        ex_inline_str = 'x' if s.get('ex_inline') else ''

        def format_symbol(sym):
            return '-' if sym == 'V' else sym

        def get_end_slide(path_segments):
            """Extract the end slide from a path - the last 2 buttons.

            For a path like 1-3p4, the end slide is 3p4 (last 2 buttons).
            For a path like 1-5-2, the end slide is 5-2.
            For a path like 1w5, the end slide is 1w5 (last 2 buttons).
            For a path like 4-7V51, the end slide is 5-1 (V chains from 7, so last 2 are 5 and 1).
            """
            if not path_segments:
                return ''
            if len(path_segments) == 1:
                seg = path_segments[0]
                sym = format_symbol(seg['symbol'])
                prefix = break_inline_str + ex_inline_str
                if len(seg['ends']) == 1:
                    return s['start'] + prefix + sym + seg['ends'][0]
                else:
                    # Multiple ends like V27 - return just the chain ends (5-1 for V51)
                    return seg['ends'][0] + '-' + '-'.join(seg['ends'][1:])
            # Get the last segment
            last_seg = path_segments[-1]
            sym = format_symbol(last_seg['symbol'])
            if len(last_seg['ends']) == 1:
                # Single end - get prev button too
                if len(path_segments) >= 2:
                    prev_end = path_segments[-2]['ends'][-1]
                    return prev_end + sym + last_seg['ends'][0]
                else:
                    return s['start'] + sym + last_seg['ends'][0]
            else:
                # Multiple ends like V - return just the chain ends
                return last_seg['ends'][0] + '-' + '-'.join(last_seg['ends'][1:])

        def get_last_sensor(path_segments):
            """Get the last sensor that a path goes through."""
            sensors = get_slide_sensors_for_path(path_segments, s['start'])
            if sensors:
                last = sensors[-1]
                return '{}{}'.format(last[0], last[1])
            return ''

        def format_path(path_segments):
            """Format a list of segments into a path string.

            For multi-segment paths, individual durations are omitted and
            a combined duration is appended at the end.
            """
            if break_str or ex_str:
                parts = [break_str + ex_str + s['start']]
            else:
                parts = [s['start'] + break_inline_str + ex_inline_str]
            for seg in path_segments:
                sym = format_symbol(seg['symbol'])
                if len(seg['ends']) == 1:
                    parts.append(sym + seg['ends'][0])
                else:
                    parts.append(sym + seg['ends'][0])
                    for e in seg['ends'][1:]:
                        parts.append('-' + e)
            # Append combined duration for multi-segment paths
            combined_dur = sum_durations(path_segments)
            if combined_dur:
                parts.append(combined_dur)
            return ''.join(parts)

        if len(segments) == 1:
            slide_str = format_path(segments)
            end_name = get_end_slide(segments)
            last_sensor = get_last_sensor(segments)
            end_slides = ['{}({})'.format(end_name, last_sensor)] if last_sensor else [end_name]
        else:
            paths = []
            end_slides = []
            current_path = []

            for seg in segments:
                current_path.append(seg)

                if seg.get('has_star_after'):
                    paths.append(format_path(current_path))
                    end_name = get_end_slide(current_path)
                    last_sensor = get_last_sensor(current_path)
                    end_slides.append('{}({})'.format(end_name, last_sensor) if last_sensor else end_name)
                    current_path.pop()

            if current_path:
                paths.append(format_path(current_path))
                end_name = get_end_slide(current_path)
                last_sensor = get_last_sensor(current_path)
                end_slides.append('{}({})'.format(end_name, last_sensor) if last_sensor else end_name)

            slide_str = ' / '.join(paths)

        slide_parts.append((slide_str, end_slides))

    divider_str = slide.get('active_divider') or ''
    bpm_str = slide.get('active_bpm') or ''
    prefix = divider_str + bpm_str
    if prefix:
        prefix = prefix + ' '
    # Only add divider/BPM to raw if not already present
    raw_prefix = ''
    if divider_str and not raw.startswith(divider_str):
        raw_prefix = divider_str
    if bpm_str and not raw.startswith(bpm_str) and not raw.startswith(divider_str + bpm_str):
        raw_prefix = raw_prefix + bpm_str
    formatted_parts = [p[0] for p in slide_parts]
    all_end_slides = []
    for p in slide_parts:
        all_end_slides.extend(p[1])
    end_slides_str = ', '.join(all_end_slides) if all_end_slides else ''
    if end_slides_str:
        end_slides_str = ' [Ends: ' + end_slides_str + ']'

    # Calculate sensors for each path separately
    sensor_groups = []
    for s in slide['slides']:
        segments = s['segments']
        if len(segments) == 1:
            sensors = get_slide_sensors_for_path(segments, s['start'])
            if sensors:
                sensor_groups.append(format_sensors(sensors))
        else:
            current_path = []
            for seg in segments:
                current_path.append(seg)
                if seg.get('has_star_after'):
                    sensors = get_slide_sensors_for_path(current_path, s['start'])
                    if sensors:
                        sensor_groups.append(format_sensors(sensors))
                    current_path.pop()
            if current_path:
                sensors = get_slide_sensors_for_path(current_path, s['start'])
                if sensors:
                    sensor_groups.append(format_sensors(sensors))
    sensors_str = ' | '.join(sensor_groups) if sensor_groups else ''
    if sensors_str:
        sensors_str = ' [Sensors: ' + sensors_str + ']'

    overlap_str = ''
    if overlap_warnings:
        overlap_str = ' [Splashy with "{}"]'.format('", "'.join(overlap_warnings))

    umiyuri_str = ''
    if umiyuri_warnings:
        umiyuri_str = ' [Umiyuri with "{}"]'.format('", "'.join(umiyuri_warnings))

    connected_str = ''
    if connected_warnings:
        connected_str = ' [Connected to "{}"]'.format('", "'.join(connected_warnings))

    delayed_str = ''
    if delayed:
        delayed_str = ' [Delayed]'

    score_str = ''
    if score is not None:
        score_str = f' [Score: {score:.1f}]'

    events_str = ''
    if in_between_events:
        events_str = ' [Events: ' + ', '.join(in_between_events) + ']'

    return f"Line {line}: {prefix}{' / '.join(formatted_parts)} ({raw_prefix}{raw}){end_slides_str}{sensors_str}{overlap_str}{umiyuri_str}{connected_str}{delayed_str}{score_str}{events_str}"


def parse_bpm(bpm_str):
    """Extract numeric BPM from string like '(150.00)'."""
    if not bpm_str:
        return 0.0
    m = re.match(r'\(([^)]+)\)', bpm_str)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return 0.0
    return 0.0


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    debug_dir = os.path.join(base_dir, 'debugcharts')
    charts_dir = os.path.join(base_dir, 'charts')
    output_file = os.path.join(base_dir, 'slide_output.txt')

    # Use debugcharts directory if it exists and contains .txt files
    if os.path.isdir(debug_dir) and any(f.endswith('.txt') for f in os.listdir(debug_dir)):
        charts_dir = debug_dir
        print(f"Using debug directory: {charts_dir}")

    if not os.path.isdir(charts_dir):
        print(f"Directory not found: {charts_dir}")
        return

    file_lines = []
    grand_total_slides = 0
    grand_total_umiyuri = 0
    grand_total_delayed = 0
    grand_total_connected = 0
    grand_total_splashy = 0
    grand_total_points = 0.0
    grand_total_delayed_points = 0.0
    grand_total_umiyuri_points = 0.0
    grand_total_connected_points = 0.0
    grand_total_splashy_points = 0.0
    grand_total_normal_points = 0.0
    all_slide_points = []

    for filename in sorted(os.listdir(charts_dir)):
        if not filename.endswith('.txt') or filename in ('trill_output.txt', 'spin_output.txt', 'slide_output.txt'):
            continue
        filepath = os.path.join(charts_dir, filename)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        events, chart_title = parse_chart(content)
        display_title = chart_title if chart_title else filename
        diff_match = re.search(r' - ([^.]+)\.txt$', filename)
        if diff_match:
            display_title = f"{display_title} - {diff_match.group(1)}"

        print(f"\n=== {display_title} ===")
        file_lines.append(f"=== {display_title} ===")
        slides = detect_slides(events)

        if not slides:
            print("  No slides detected.")
            file_lines.append("  No slides detected.")
            continue

        total_slides = len(slides)
        grand_total_slides += total_slides

        # Pre-compute overlaps per slide
        overlaps = detect_overlaps(slides)
        slide_overlaps = {}
        for ov in overlaps:
            a_idx = ov['slide_a']['start_event_index']
            b_idx = ov['slide_b']['start_event_index']
            # Add B as overlapping A
            if a_idx not in slide_overlaps:
                slide_overlaps[a_idx] = []
            slide_overlaps[a_idx].append(ov['slide_b']['raw'])

        # Pre-compute umiyuri patterns per slide
        umiyuris = detect_umiyuri(slides, events)
        slide_umiyuri_warnings = {}
        slide_umiyuris = {}
        for um in umiyuris:
            a_idx = um['slide_a']['start_event_index']
            b_idx = um['slide_b']['start_event_index']
            if a_idx not in slide_umiyuris:
                slide_umiyuris[a_idx] = []
            slide_umiyuris[a_idx].append({
                'raw': um['slide_b']['raw'],
                'type': um['type'],
                'slide_b': um['slide_b']
            })
            if a_idx not in slide_umiyuri_warnings:
                slide_umiyuri_warnings[a_idx] = set()
            slide_umiyuri_warnings[a_idx].add(um['slide_b']['raw'])
            if b_idx not in slide_umiyuris:
                slide_umiyuris[b_idx] = []
            slide_umiyuris[b_idx].append({
                'raw': um['slide_a']['raw'],
                'type': um['type'],
                'slide_b': um['slide_a']
            })
            if b_idx not in slide_umiyuri_warnings:
                slide_umiyuri_warnings[b_idx] = set()
            slide_umiyuri_warnings[b_idx].add(um['slide_a']['raw'])
        # Convert sets to lists
        for idx in slide_umiyuri_warnings:
            slide_umiyuri_warnings[idx] = list(slide_umiyuri_warnings[idx])

        # Pre-compute connected slides per slide
        connected_slides = detect_connected_slides(slides)
        slide_connected = {}
        for conn in connected_slides:
            a_idx = conn['slide_a']['start_event_index']
            b_idx = conn['slide_b']['start_event_index']
            if a_idx not in slide_connected:
                slide_connected[a_idx] = set()
            slide_connected[a_idx].add(conn['slide_b']['raw'])
            if b_idx not in slide_connected:
                slide_connected[b_idx] = set()
            slide_connected[b_idx].add(conn['slide_a']['raw'])
        # Convert sets to lists
        for idx in slide_connected:
            slide_connected[idx] = list(slide_connected[idx])

        # Pre-compute delayed slides
        delayed_slides = detect_delayed_slides(slides, events)
        delayed_indices = set()
        for d in delayed_slides:
            delayed_indices.add(d['slide']['start_event_index'])

        # Count unique slides with each pattern and calculate points
        umiyuri_count = len(slide_umiyuris)
        delayed_count = len(delayed_indices)
        connected_count = len(slide_connected)
        splashy_indices = set()

        file_total_points = 0.0
        file_delayed_points = 0.0
        file_umiyuri_points = 0.0
        file_connected_points = 0.0
        file_splashy_points = 0.0
        file_normal_points = 0.0
        file_slide_points = []

        for slide in slides:
            idx = slide['start_event_index']
            overlap_warnings = slide_overlaps.get(idx, [])
            umiyuri_warnings = slide_umiyuri_warnings.get(idx, [])
            connected_warnings = slide_connected.get(idx, [])
            is_delayed = idx in delayed_indices
            # Remove splashy warnings for slides that are connected
            if connected_warnings:
                connected_set = set(connected_warnings)
                overlap_warnings = [w for w in overlap_warnings if w not in connected_set]
            if overlap_warnings:
                splashy_indices.add(idx)

            # Calculate points for this slide
            # Count total sensors across all paths
            sensor_count = 0
            for s in slide['slides']:
                segments = s['segments']
                if len(segments) == 1:
                    sensors = get_slide_sensors_for_path(segments, s['start'])
                    if sensors:
                        sensor_count += len(sensors)
                else:
                    current_path = []
                    for seg in segments:
                        current_path.append(seg)
                        if seg.get('has_star_after'):
                            sensors = get_slide_sensors_for_path(current_path, s['start'])
                            if sensors:
                                sensor_count += len(sensors)
                            current_path.pop()
                    if current_path:
                        sensors = get_slide_sensors_for_path(current_path, s['start'])
                        if sensors:
                            sensor_count += len(sensors)
            if sensor_count == 0:
                sensor_count = 1

            has_delayed = is_delayed
            has_umiyuri = bool(umiyuri_warnings)
            has_connected = bool(connected_warnings)
            has_splashy = bool(overlap_warnings)

            in_between = get_in_between_multiplier(slide, events, slide_umiyuris)
            in_between_events = get_events_in_slide_duration(slide, events, slide_umiyuris)

            multiplier = 1.0
            if has_splashy:
                multiplier += 2.0
            if has_umiyuri:
                multiplier += 2.0
            if has_connected:
                multiplier += 2.0
            if has_delayed:
                multiplier += 1.0

            slide_points = multiplier * (1 + 0.2 * sensor_count) * in_between * 400
            file_slide_points.append(slide_points)
            all_slide_points.append(slide_points)
            file_total_points += slide_points

            if has_splashy:
                file_splashy_points += slide_points
            if not (has_delayed or has_umiyuri or has_connected or has_splashy):
                file_normal_points += slide_points

            try:
                slide_line = f"    {format_slide(slide, overlap_warnings, umiyuri_warnings, connected_warnings, is_delayed, in_between_events, slide_points)}"
                file_lines.append(slide_line)
            except UnicodeEncodeError:
                slide_enc = format_slide(slide, overlap_warnings, umiyuri_warnings, connected_warnings, is_delayed, in_between_events, slide_points).encode('utf-8', 'replace').decode('utf-8')
                file_lines.append(f"    {slide_enc}")

        splashy_count = len(splashy_indices)
        grand_total_umiyuri += umiyuri_count
        grand_total_delayed += delayed_count
        grand_total_connected += connected_count
        grand_total_splashy += splashy_count
        grand_total_points += file_total_points
        grand_total_splashy_points += file_splashy_points
        grand_total_normal_points += file_normal_points

        # Build BPM breakdown
        bpm_stats = {}
        for slide in slides:
            bpm = parse_bpm(slide.get('active_bpm'))
            bpm_key = f"{bpm:.1f}"
            if bpm_key not in bpm_stats:
                bpm_stats[bpm_key] = {'count': 0, 'points': 0.0}
            bpm_stats[bpm_key]['count'] += 1
            # Recalculate this slide's points
            idx = slide['start_event_index']
            overlap_warnings = slide_overlaps.get(idx, [])
            umiyuri_warnings = slide_umiyuri_warnings.get(idx, [])
            connected_warnings = slide_connected.get(idx, [])
            is_delayed = idx in delayed_indices
            if connected_warnings:
                connected_set = set(connected_warnings)
                overlap_warnings = [w for w in overlap_warnings if w not in connected_set]
            has_delayed = is_delayed
            has_umiyuri = bool(umiyuri_warnings)
            has_connected = bool(connected_warnings)
            has_splashy = bool(overlap_warnings)
            sensor_count = 0
            for s in slide['slides']:
                segments = s['segments']
                if len(segments) == 1:
                    sensors = get_slide_sensors_for_path(segments, s['start'])
                    if sensors:
                        sensor_count += len(sensors)
                else:
                    current_path = []
                    for seg in segments:
                        current_path.append(seg)
                        if seg.get('has_star_after'):
                            sensors = get_slide_sensors_for_path(current_path, s['start'])
                            if sensors:
                                sensor_count += len(sensors)
                            current_path.pop()
                    if current_path:
                        sensors = get_slide_sensors_for_path(current_path, s['start'])
                        if sensors:
                            sensor_count += len(sensors)
            if sensor_count == 0:
                sensor_count = 1
            in_between = get_in_between_multiplier(slide, events, slide_umiyuris)

            multiplier = 1.0
            if has_splashy:
                multiplier += 0.2
            if has_umiyuri:
                multiplier += 0.1
            if has_connected:
                multiplier += 0.1
            if has_delayed:
                multiplier += 0.1

            sp = multiplier * (1 + 0.2 * sensor_count) * in_between * 400
            bpm_stats[bpm_key]['points'] += sp

        # Output new format
        file_avg = file_total_points / total_slides if total_slides > 0 else 0.0
        above_avg_points = [p for p in file_slide_points if p > file_avg]
        file_estimated = sum(above_avg_points) / len(above_avg_points) if above_avg_points else 0.0
        file_connected_points = file_avg * connected_count
        file_umiyuri_points = file_avg * umiyuri_count
        file_delayed_points = file_avg * delayed_count
        summary_lines = [
            f"{total_slides} slides ! {splashy_count} splash ! {connected_count} connected ! {umiyuri_count} umiyuri ! {delayed_count} delayed !",
            f"slides points: {file_total_points:.1f}",
            f"connected points: {file_connected_points:.1f}",
            f"umiyuri points: {file_umiyuri_points:.1f}",
            f"delayed points: {file_delayed_points:.1f}",
            f"average points per slide: {file_avg:.1f}",
            f"estimated slide difficulty: {file_estimated:.1f}",
        ]
        for bpm_key in sorted(bpm_stats.keys(), key=float):
            stats = bpm_stats[bpm_key]
            summary_lines.append(f"{bpm_key} BPM: {stats['count']} slides -> {stats['points']:.1f} pts")

        for line in summary_lines:
            print(f"  {line}")
            file_lines.append(f"  {line}")

    # Grand totals
    grand_avg = grand_total_points / grand_total_slides if grand_total_slides > 0 else 0.0
    grand_above_avg = [p for p in all_slide_points if p > grand_avg]
    grand_estimated = sum(grand_above_avg) / len(grand_above_avg) if grand_above_avg else 0.0
    grand_delayed_points = grand_avg * grand_total_delayed
    grand_umiyuri_points = grand_avg * grand_total_umiyuri
    grand_connected_points = grand_avg * grand_total_connected
    totals_line = (
        f"\n=== GRAND TOTALS ===\n"
        f"  Slides: {grand_total_slides} | Splashy: {grand_total_splashy} | Umiyuri: {grand_total_umiyuri} | "
        f"Delayed: {grand_total_delayed} | Connected: {grand_total_connected}\n"
        f"  Total Points: {grand_total_points:.1f} (Delayed: {grand_delayed_points:.1f}, Umiyuri: {grand_umiyuri_points:.1f}, "
        f"Connected: {grand_connected_points:.1f}, Splashy: {grand_total_splashy_points:.1f}, Normal: {grand_total_normal_points:.1f})\n"
        f"  Average Points per Slide: {grand_avg:.1f}\n"
        f"  Estimated Slide Difficulty: {grand_estimated:.1f}\n"
        f"\n--- METHOD ---\n"
        f"  Points = (1 + status_bonus) * (1 + 0.2 * sensor_count) * in_between_multiplier * 400\n"
        f"  Status bonus: splashy +2.0 | umiyuri +2.0 | connected +2.0 | delayed +1.0\n"
        f"  Category points = average_points * category_count\n"
        f"  Estimated difficulty = average of slides with score > average"
    )
    print(totals_line)
    file_lines.append(totals_line)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(file_lines))


if __name__ == '__main__':
    main()