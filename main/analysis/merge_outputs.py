import re
import json
import os

def parse_slide_output(content):
    results = {}
    current_chart = None
    current_difficulty = None
    current_bpm = None
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Match chart header like "=== =+♂ - Advanced ==="
        chart_match = re.match(r'=== (.+) - (.+) ===', line)
        if chart_match:
            current_chart = chart_match.group(1).strip()
            current_difficulty = chart_match.group(2).strip()
            current_bpm = None
            continue
        
        # Match BPM line like "  90.0 BPM: 56 slides -> 94578.4 pts"
        bpm_match = re.match(r'^\s*([\d.]+)\s*BPM:\s*\d+\s*slides\s*->\s*[\d.]+\s*pts', line)
        if bpm_match:
            current_bpm = float(bpm_match.group(1))
            continue
        
        # Match summary lines
        if current_chart and current_difficulty:
            key = (current_chart, current_difficulty)
            
            # Match "slides points:" line
            total_match = re.match(r'^\s*slides points:\s*([\d.]+)', line)
            if total_match:
                total = float(total_match.group(1))
                if key not in results:
                    results[key] = {'bpm': current_bpm, 'slide_total': total}
                else:
                    results[key]['slide_total'] = total
                continue
            
            # Match "connected points:" line
            connected_match = re.match(r'^\s*connected points:\s*([\d.]+)', line)
            if connected_match:
                if key in results:
                    results[key]['slide_connected'] = float(connected_match.group(1))
                continue
            
            # Match "umiyuri points:" line
            umiyuri_match = re.match(r'^\s*umiyuri points:\s*([\d.]+)', line)
            if umiyuri_match:
                if key in results:
                    results[key]['slide_umiyuri'] = float(umiyuri_match.group(1))
                continue
            
            # Match "delayed points:" line
            delayed_match = re.match(r'^\s*delayed points:\s*([\d.]+)', line)
            if delayed_match:
                if key in results:
                    results[key]['slide_delayed'] = float(delayed_match.group(1))
                continue
            
            # Match "average points per slide:" line
            avg_match = re.match(r'^\s*average points per slide:\s*([\d.]+)', line)
            if avg_match:
                if key in results:
                    results[key]['slide_avg'] = float(avg_match.group(1))
                continue
            
            # Match "estimated slide difficulty:" line
            est_match = re.match(r'^\s*estimated slide difficulty:\s*([\d.]+)', line)
            if est_match:
                if key in results:
                    results[key]['slide_estimated'] = float(est_match.group(1))
                continue
    
    return results

def parse_spin_output(content):
    results = {}
    current_chart = None
    current_difficulty = None
    current_bpm = None
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Match chart header
        chart_match = re.match(r'=== (.+) - (.+) ===', line)
        if chart_match:
            current_chart = chart_match.group(1).strip()
            current_difficulty = chart_match.group(2).strip()
            current_bpm = None
            continue
        
        # Match BPM line like "  8 spin(s) | 28 note(s) | 1 pass(es) | BPM: 181.0"
        bpm_match = re.match(r'.*\|\s*BPM:\s*([\d.]+)', line)
        if bpm_match and current_chart:
            current_bpm = float(bpm_match.group(1))
            continue
        
        # Match "spin points:" line
        if current_chart and current_difficulty:
            key = (current_chart, current_difficulty)
            
            # Skip lines with "No spins detected"
            if 'No spins detected' in line:
                if key not in results:
                    results[key] = {'bpm': current_bpm, 'spin_total': 0.0, 'spin_avg': 0.0}
                continue
            
            points_match = re.match(r'^\s*spin points:\s*([\d.]+)\s*\|\s*avg:\s*([\d.]+)/note', line)
            if points_match:
                total = float(points_match.group(1))
                avg = float(points_match.group(2))
                results[key] = {'bpm': current_bpm, 'spin_total': total, 'spin_avg': avg}
                continue
    
    return results

def parse_tap_output(content):
    results = {}
    current_chart = None
    current_difficulty = None
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Match chart header
        chart_match = re.match(r'=== (.+) - (.+) ===', line)
        if chart_match:
            current_chart = chart_match.group(1).strip()
            current_difficulty = chart_match.group(2).strip()
            continue
        
        # Match tap summary line
        # "  taps: 260 (141994.5) | holds: 28 (11222.0) | touches: 0 (0.0) | total: 288 notes (153216.5 pts) | avg: 532.00/note"
        if current_chart and current_difficulty:
            key = (current_chart, current_difficulty)
            
            # Skip lines that don't have "total:" and "notes"
            if 'total:' not in line or 'notes' not in line:
                continue
            
            # Extract total and avg
            # Try to match total: X notes (Y pts) | avg: Z/note
            total_match = re.search(r'total:\s*(\d+)\s*notes\s*\(([\d.]+)\s*pts\)', line)
            avg_match = re.search(r'avg:\s*([\d.]+)/note', line)
            
            if total_match and avg_match:
                total = float(total_match.group(2))
                avg = float(avg_match.group(1))
                results[key] = {'tap_total': total, 'tap_avg': avg}
                continue
    
    return results

def parse_trill_output(content):
    results = {}
    current_chart = None
    current_difficulty = None
    current_bpm = None
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Match chart header
        chart_match = re.match(r'=== (.+) - (.+) ===', line)
        if chart_match:
            current_chart = chart_match.group(1).strip()
            current_difficulty = chart_match.group(2).strip()
            current_bpm = None
            continue
        
        # Match BPM line
        bpm_match = re.match(r'.*\|\s*BPM:\s*([\d.]+)', line)
        if bpm_match and current_chart:
            current_bpm = float(bpm_match.group(1))
            continue
        
        # Match "trill points:" line
        if current_chart and current_difficulty:
            key = (current_chart, current_difficulty)
            
            if 'No trills detected' in line:
                if key not in results:
                    results[key] = {'bpm': current_bpm, 'trill_total': 0.0, 'trill_avg': 0.0}
                continue
            
            points_match = re.match(r'^\s*trill points:\s*([\d.]+)\s*\|\s*avg:\s*([\d.]+)/note', line)
            if points_match:
                total = float(points_match.group(1))
                avg = float(points_match.group(2))
                results[key] = {'bpm': current_bpm, 'trill_total': total, 'trill_avg': avg}
                continue
    
    return results

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Read all output files
    with open(os.path.join(base_dir, 'slide_output.txt'), 'r', encoding='utf-8') as f:
        slide_content = f.read()
    
    with open(os.path.join(base_dir, 'spin_output.txt'), 'r', encoding='utf-8') as f:
        spin_content = f.read()
    
    with open(os.path.join(base_dir, 'tap_output.txt'), 'r', encoding='utf-8') as f:
        tap_content = f.read()
    
    with open(os.path.join(base_dir, 'trill_output.txt'), 'r', encoding='utf-8') as f:
        trill_content = f.read()
    
    # Parse each file
    slide_data = parse_slide_output(slide_content)
    spin_data = parse_spin_output(spin_content)
    tap_data = parse_tap_output(tap_content)
    trill_data = parse_trill_output(trill_content)
    
    # Merge all data
    all_charts = set()
    all_charts.update(slide_data.keys())
    all_charts.update(spin_data.keys())
    all_charts.update(tap_data.keys())
    all_charts.update(trill_data.keys())
    
    # Build merged results
    merged = []
    for chart, difficulty in sorted(all_charts):
        entry = {
            'chart': chart,
            'difficulty_type': difficulty,
            'bpm': None,
            'slide_total': 0.0,
            'slide_connected': 0.0,
            'slide_umiyuri': 0.0,
            'slide_delayed': 0.0,
            'slide_estimated': 0.0,
            'spin_total': 0.0,
            'spin_avg': 0.0,
            'tap_total': 0.0,
            'tap_avg': 0.0,
            'trill_total': 0.0,
            'trill_avg': 0.0
        }
        
        # Merge slide data
        if (chart, difficulty) in slide_data:
            sd = slide_data[(chart, difficulty)]
            entry['bpm'] = sd.get('bpm')
            entry['slide_total'] = sd.get('slide_total', 0.0)
            entry['slide_connected'] = sd.get('slide_connected', 0.0)
            entry['slide_umiyuri'] = sd.get('slide_umiyuri', 0.0)
            entry['slide_delayed'] = sd.get('slide_delayed', 0.0)
            entry['slide_estimated'] = sd.get('slide_estimated', 0.0)
        
        # Merge spin data
        if (chart, difficulty) in spin_data:
            sd = spin_data[(chart, difficulty)]
            if entry['bpm'] is None:
                entry['bpm'] = sd.get('bpm')
            entry['spin_total'] = sd.get('spin_total', 0.0)
            entry['spin_avg'] = sd.get('spin_avg', 0.0)
        
        # Merge tap data
        if (chart, difficulty) in tap_data:
            td = tap_data[(chart, difficulty)]
            entry['tap_total'] = td.get('tap_total', 0.0)
            entry['tap_avg'] = td.get('tap_avg', 0.0)
        
        # Merge trill data
        if (chart, difficulty) in trill_data:
            td = trill_data[(chart, difficulty)]
            if entry['bpm'] is None:
                entry['bpm'] = td.get('bpm')
            entry['trill_total'] = td.get('trill_total', 0.0)
            entry['trill_avg'] = td.get('trill_avg', 0.0)
        
        merged.append(entry)
    
    # Write results to file
    output_file = os.path.join(base_dir, 'merged_output.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in merged:
            # Calculate skills (total of slide, spin, tap, trill)
            
            f.write(json.dumps({
                'chart': entry['chart'],
                'difficulty type': entry['difficulty_type'],
                'BPM': entry['bpm'] if entry['bpm'] else 0.0,
                'Slide': f"Total: {entry['slide_total']:.1f}; connected total: {entry['slide_connected']:.1f}; umiyuri total: {entry['slide_umiyuri']:.1f}; delayed total: {entry['slide_delayed']:.1f}; estimated difficulty: {entry['slide_estimated']:.1f}",
                'Spin': f"Total: {entry['spin_total']:.1f}; avg: {entry['spin_avg']:.1f}",
                'Taps': f"Total: {entry['tap_total']:.1f}; avg: {entry['tap_avg']:.1f}",
                'Trills': f"Total: {entry['trill_total']:.1f}; avg: {entry['trill_avg']:.1f}"
            }, ensure_ascii=False) + '\n')
    
    print(f"Written to {output_file}")

if __name__ == '__main__':
    main()
