import json
import re
from collections import defaultdict

def parse_stat_string(stat_str):
    result = {}
    parts = stat_str.split(';')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if ':' in part:
            key, value = part.split(':', 1)
            key = key.strip()
            value = value.strip()
            try:
                result[key] = float(value)
            except ValueError:
                result[key] = value
    return result

with open('merged_output.json', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f]

grouped = defaultdict(list)

for item in data:
    chart_name = item['chart']
    if chart_name.startswith('='):
        chart_name = chart_name[1:]
    chart_name = chart_name.replace('Remaster', 'Re:Master')
    difficulty = item['difficulty type']
    difficulty = difficulty.replace('Remaster', 'Re:Master')
    new_item = {
        "difficulty type": difficulty,
        "Slide": parse_stat_string(item["Slide"]),
        "Spin": parse_stat_string(item["Spin"]),
        "Taps": parse_stat_string(item["Taps"]),
        "Trills": parse_stat_string(item["Trills"])
    }
    grouped[chart_name].append(new_item)

result = [{"chart": name, "difficulties": diffs} for name, diffs in grouped.items()]

with open('merged_output_reformatted.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Created reformatted file with {len(result)} charts")