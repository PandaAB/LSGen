import json
import random
from collections import defaultdict
from utils.jsonTools import load_json, tojson

data = load_json("final_selected_records.json")

error_count_groups = defaultdict(list)
for item in data:
    error_count_groups[item["error_count"]].append(item)

target_counts = {1: 10, 2: 20, "3+": 20}
selected_data = []

for count, target in target_counts.items():
    if count == "3+":
        candidates = [item for ec, lst in error_count_groups.items() if ec >= 3 for item in lst]
    else:
        candidates = error_count_groups.get(count, [])

    selected_data.extend(random.sample(candidates, min(target, len(candidates))))


unique_problem_ids = {item["problem_id"] for item in selected_data}

tojson(selected_data, "sampled_records.json")

print(f"最终筛选数据 {len(selected_data)} 条，其中 error_count=1: {target_counts[1]} 条，error_count=2: {target_counts[2]} 条，error_count>=3: {target_counts['3+']} 条。")
print(f"总共涉及 {len(unique_problem_ids)} 道不同的题目。")
