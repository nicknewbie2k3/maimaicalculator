import io
import os
import re
import sys

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
    """Parse simai chart content into a list of beat events with line tracking."""
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
    leading_re = re.compile(r'^(\{[^}]*\}|\([^)]*\))+')

    for line_num, line in enumerate(lines, start=start_line+1):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^\d+:\s*', line)
        if m:
            line = line[m.end():]

        beat_fields = line.split(',')
        for raw_beat in beat_fields:
            raw = raw_beat.strip()
            active_divider = current_divider
            active_bpm = current_bpm
            remainder = raw

            m = leading_re.match(raw)
            if m:
                leading = m.group(0)
                for token in re.findall(r'\{(\d+(?:\.\d+)?)\}|\{#(\d+(?:\.\d+)?)\}|\(([^)]+)\)', leading):
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

            event_idx = len(events)
            if not remainder:
                events.append({'type': 'empty', 'raw': raw, 'event_idx': event_idx,
                               'active_divider': active_divider, 'active_bpm': active_bpm,
                               'h1': None, 'h2': None, 'line': line_num})
                continue

            if is_double_note(remainder):
                if '/' in remainder or '`' in remainder:
                    parts = re.split(r'[/`]', remainder)
                    h1 = parts[0] if len(parts) > 0 else None
                    h2 = parts[1] if len(parts) > 1 else None
                else:
                    h1 = remainder[0] if len(remainder) >= 1 else None
                    h2 = remainder[1] if len(remainder) >= 2 else None
                pos1 = extract_position(h1)
                pos2 = extract_position(h2) if h2 else None
                events.append({'type': 'note', 'raw': raw, 'is_double': True, 'event_idx': event_idx,
                               'position': None, 'h1': pos1, 'h2': pos2,
                               'active_divider': active_divider, 'active_bpm': active_bpm,
                               'line': line_num})
            else:
                pos = extract_position(remainder)
                events.append({'type': 'note', 'raw': raw, 'is_double': False, 'event_idx': event_idx,
                               'position': pos, 'h1': pos, 'h2': None,
                               'active_divider': active_divider, 'active_bpm': active_bpm,
                               'line': line_num})
    return events, title


def detect_spins(events):
    """Detect spins in the chart.

    Spins are sequences of notes where button positions increase (+1) or decrease (-1)
    consecutively for 3 or more notes. Each half of each note (h1, h2) is tracked
    independently.

    Args:
        events: List of parsed beat events from parse_chart()

    Returns:
        List of spin dicts with keys:
            - start_event_index: index in events of first note
            - end_event_index: index in events of last note
            - direction: '+' for clockwise, '-' for counter-clockwise
            - length: number of notes in spin
            - positions: tuple of button positions in the spin
    """
    n = len(events)

    # Track consumed half-notes to prevent double-counting within spin detection
    # Key: (event_index, half) where half is 'h1' or 'h2'
    consumed = {}

    all_spins = []

    # Process each event
    for i in range(n):
        ev = events[i]
        if ev['type'] != 'note':
            continue

        for half in ('h1', 'h2'):
            pos = ev.get(half)
            if pos is None:
                continue
            if consumed.get((i, half)):
                continue
            if pos not in '12345678':
                continue

            # Start tracking potential spin from this note
            potential_spin = {
                'start_event_index': i,
                'half': half,
                'direction': None,
                'count': 0,
                'positions': [],
                'consumed_indices': []
            }

            j = i
            while j < n:
                ev_j = events[j]
                if ev_j['type'] != 'note':
                    break

                pos_j = ev_j.get(half)
                if pos_j is None:
                    break
                if consumed.get((j, half)):
                    break
                if pos_j not in '12345678':
                    break

                current_pos = int(pos_j)

                if potential_spin['count'] == 0:
                    # First note in potential spin
                    potential_spin['positions'].append(pos_j)
                    potential_spin['consumed_indices'].append((j, half))
                    potential_spin['count'] = 1
                    consumed[(j, half)] = True
                    j += 1
                    continue

                prev_pos = int(potential_spin['positions'][-1])
                diff = current_pos - prev_pos

                # Normalize diff to handle wraparound (e.g., 8->1 is +1, 1->8 is -1)
                if diff == 1 or diff == -7:
                    direction = '+'
                elif diff == -1 or diff == 7:
                    direction = '-'
                else:
                    # Not adjacent - spin ends
                    break

                # Check if direction matches or sets direction
                if potential_spin['direction'] is None:
                    potential_spin['direction'] = direction
                elif potential_spin['direction'] != direction:
                    # Direction changed - spin ends
                    break

                # Valid continuation
                potential_spin['positions'].append(pos_j)
                potential_spin['consumed_indices'].append((j, half))
                potential_spin['count'] += 1
                consumed[(j, half)] = True
                j += 1

            # After exiting the loop, check if we have a valid spin
            if potential_spin['count'] >= 3:
                spin = {
                    'start_event_index': potential_spin['start_event_index'],
                    'end_event_index': j - 1,
                    'direction': potential_spin['direction'],
                    'length': potential_spin['count'],
                    'positions': tuple(potential_spin['positions']),
                    'half': potential_spin['half']
                }
                all_spins.append(spin)
            else:
                # Spin too short - unmark consumed notes
                for idx_tuple in potential_spin['consumed_indices']:
                    consumed[idx_tuple] = False

    all_spins.sort(key=lambda s: s['start_event_index'])
    return all_spins


def mask_events(events, consumed_set):
    """Create a copy of events with consumed half-notes marked as empty."""
    masked = []
    for ev in events:
        new_ev = ev.copy()
        if ev['type'] == 'note':
            if consumed_set.get((ev['event_idx'], 'h1')):
                new_ev['h1'] = None
            if consumed_set.get((ev['event_idx'], 'h2')):
                new_ev['h2'] = None
        masked.append(new_ev)
    return masked


def detect_spins_iterative(content):
    """Detect spins iteratively: detect -> mask consumed -> re-detect until no new spins found."""
    title = None
    start_line = 0
    for idx, line in enumerate(content.split('\n')):
        if line.strip().startswith('&title'):
            title = line.strip()[6:].strip()
            start_line = idx + 1
            break

    content = '\n'.join(content.split('\n')[start_line:])

    events, _ = parse_chart(content)

    all_passes = []
    current_events = events
    pass_num = 1

    while True:
        spins = detect_spins(current_events)
        if not spins:
            break

        consumed_set = {}
        for spin in spins:
            half = spin['half']
            for idx in range(spin['start_event_index'], spin['end_event_index'] + 1):
                consumed_set[(idx, half)] = True

        all_passes.append({
            'pass': pass_num,
            'spins': spins,
            'events': current_events,
        })

        current_events = mask_events(current_events, consumed_set)
        pass_num += 1

    final_events = current_events
    return all_passes, final_events, title


def format_spin(spin, events):
    """Format a spin for display with line numbers and density."""
    half = spin['half'].upper()
    start_line = events[spin['start_event_index']]['line']
    end_line = events[spin['end_event_index']]['line']
    if start_line == end_line:
        line_str = f"Line {start_line}"
    else:
        line_str = f"Line {start_line}-{end_line}"

    divider_counts = {}
    for k in range(spin['start_event_index'], spin['end_event_index'] + 1):
        div = events[k].get('active_divider')
        if div:
            divider_counts[div] = divider_counts.get(div, 0) + 1

    density_parts = []
    for d, c in sorted(divider_counts.items(), key=lambda x: float(re.match(r'^\{#?(\d+(?:\.\d+)?)\}', x[0]).group(1))):
        density_parts.append(f"{d}:{c}")

    density_str = ""
    if density_parts:
        density_str = " [" + ", ".join(density_parts) + "]"

    return (f"{line_str} "
            f"({half}, {spin['direction']}, {spin['length']} notes){density_str}: "
            f"{','.join(spin['positions'])}")


def main():
    import re as re_module
    base_dir = os.path.dirname(os.path.abspath(__file__))
    debug_dir = os.path.join(base_dir, 'debugcharts')
    charts_dir = os.path.join(base_dir, 'charts')
    output_file = os.path.join(base_dir, 'spin_output.txt')

    if os.path.isdir(debug_dir) and any(f.endswith('.txt') for f in os.listdir(debug_dir)):
        charts_dir = debug_dir
        print(f"Using debug directory: {charts_dir}")

    if not os.path.isdir(charts_dir):
        print(f"Directory not found: {charts_dir}")
        return

    file_lines = []

    for filename in sorted(os.listdir(charts_dir)):
        if not filename.endswith('.txt') or filename in ('trill_output.txt', 'spin_output.txt'):
            continue
        filepath = os.path.join(charts_dir, filename)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        bpm_match = re.search(r'^\s*\((\d+(?:\.\d+)?)\)', content, re.MULTILINE)
        bpm = float(bpm_match.group(1)) if bpm_match else 1

        all_passes, final_events, chart_title = detect_spins_iterative(content)
        display_title = chart_title if chart_title else filename
        diff_match = re.search(r' - ([^.]+)\.txt$', filename)
        if diff_match:
            display_title = f"{display_title} - {diff_match.group(1)}"

        print(f"\n=== {display_title} ===")
        file_lines.append(f"=== {display_title} ===")

        if not all_passes:
            print("  No spins detected.")
            file_lines.append("  No spins detected.")
            continue

        total_spins = 0
        total_notes = 0
        divider_counts = {}
        for pass_data in all_passes:
            events = pass_data['events']
            total_spins += len(pass_data['spins'])
            for spin in pass_data['spins']:
                start = spin['start_event_index']
                end = spin['end_event_index']
                count = end - start + 1
                total_notes += count
                for k in range(start, end + 1):
                    div = events[k].get('active_divider')
                    if div:
                        divider_counts[div] = divider_counts.get(div, 0) + 1

        points = sum(float(re.match(r'^\{#?(\d+(?:\.\d+)?)\}$', d).group(1)) * c
                     for d, c in divider_counts.items()) * bpm

        summary = f"  {total_spins} spin(s) | {total_notes} note(s) | {len(all_passes)} pass(es) | BPM: {bpm}"
        points_line = f"  spin points: {points:.1f} | avg: {points/total_notes:.2f}/note" if total_notes > 0 else f"  0 notes"
        print(summary)
        print(points_line)
        file_lines.append(summary)
        file_lines.append(points_line)

        for d in sorted(divider_counts, key=lambda x: float(re.match(r'^\{#?(\d+(?:\.\d+)?)\}$', x).group(1))):
            c = divider_counts[d]
            pts = float(re.match(r'^\{#?(\d+(?:\.\d+)?)\}$', d).group(1)) * c * bpm
            divider_line = f"    {d}: {c} note(s) -> {pts:.1f} pts"
            file_lines.append(divider_line)

        for pass_data in all_passes:
            pass_line = f"  --- pass {pass_data['pass']} ({len(pass_data['spins'])} spin(s)) ---"
            file_lines.append(pass_line)
            for spin in pass_data['spins']:
                try:
                    spin_line = f"    {format_spin(spin, pass_data['events'])}"
                    file_lines.append(spin_line)
                except UnicodeEncodeError:
                    spin_enc = format_spin(spin, pass_data['events']).encode('utf-8', 'replace').decode('utf-8')
                    file_lines.append(f"    {spin_enc}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(file_lines))

    print(f"\n--- METHOD ---")
    print(f"  Points = sum(divider_value * note_count) * BPM")


if __name__ == '__main__':
    main()