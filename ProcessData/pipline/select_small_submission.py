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
