import detect_taps

content = open('debugcharts/testchart.txt', 'r', encoding='utf-8').read()
evs, all_notes, title = detect_taps.parse_notes(content)

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

print('Div values:')
for i in [9, 10, 11, 12, 13]:
    n = all_notes[i]
    print(f'Index {i}: raw={repr(n["raw"]):10s} div={n["div_prior"]:.0f}')