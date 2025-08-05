#!/usr/bin/env python3
import json
import random
from collections import defaultdict
import argparse
from utils.jsonTools import CustomEncoder, load_json, tojson
try:
    from extract_diff_sequence import process_all_diff_folders
except ImportError:
    process_all_diff_folders = None

def filter_and_partition(diff_data, retrieval_data, min_count = 1, max_count = 10):
    filtered = []
    for record in retrieval_data:
        sub_id = record.get("submission1_id")
        if sub_id in diff_data:
            ec = diff_data[sub_id].get("error_count")
            if ec is not None and min_count <= ec <= max_count and record["problem_id"] != "p02974":
                record["error_count"] = ec
                filtered.append(record)
    group1 = [r for r in filtered if r["error_count"] == 1]
    group2 = [r for r in filtered if r["error_count"] == 2]
    group3 = [r for r in filtered if r["error_count"] >= 3]
    return group1, group2, group3, filtered

def select_with_diversity(records, required_count):

    by_problem = defaultdict(list)
    for r in records:
        pid = r.get("problem_id")
        by_problem[pid].append(r)
    for pid in by_problem:
        random.shuffle(by_problem[pid])
    selected = []
    for pid, rec_list in by_problem.items():
        selected.append(rec_list.pop(0))
    if len(selected) < required_count:
        remaining = []
        for rec_list in by_problem.values():
            remaining.extend(rec_list)
        random.shuffle(remaining)
        need = required_count - len(selected)
        selected.extend(remaining[:need])
    if len(selected) > required_count:
        selected = random.sample(selected, required_count)
    random.shuffle(selected)
    return selected

def ensure_min_problem_diversity(final_records, all_filtered, min_problem_count):

    selected = final_records.copy()
    current_pids = {r["problem_id"] for r in selected}
    if len(current_pids) >= min_problem_count:
        return selected
    candidates = [r for r in all_filtered if r["problem_id"] not in current_pids]
    random.shuffle(candidates)
    for cand in candidates:
        if len({r["problem_id"] for r in selected}) >= min_problem_count:
            break
        replace_idx = random.randrange(len(selected))
        selected[replace_idx] = cand
        current_pids = {r["problem_id"] for r in selected}
    return selected

def main():
    parser = argparse.ArgumentParser(description="Select submissions with diversity")
    parser.add_argument("--mode", type=str, choices=["file", "direct"], default="file")
    parser.add_argument("--diff_json_path", type=str, default="diff_error_counts.json")
    parser.add_argument("--diff_root", type=str, default="dataset/diff_code")
    parser.add_argument("--direct_diff_output", type=str, default="temp_diff_error_counts.json")
    parser.add_argument("--retrieval_json_path", type=str, default="dataset/RetrievaledData/Retrievaled_1011_test_Top3.json")
    parser.add_argument("--group1_count", type=int, default=100, help="error_count==1 select numbers")
    parser.add_argument("--group2_count", type=int, default=200, help="error_count==2 select numbers")
    parser.add_argument("--group3_count", type=int, default=200, help="error_count>=3 select numberss")
    parser.add_argument("--total_count", type=int, default=500, help="Final recorded total")
    parser.add_argument("--min_problem_count", type=int, default=85, help="Minimum number of different problems to cover")
    parser.add_argument("--output_file", type=str, default="final_selected_records.json", help="The final output JSON file")
    parser.add_argument("--min_error_count", type=int, default=1)
    parser.add_argument("--max_error_count", type=int, default=10)
    args = parser.parse_args()

    if args.mode == "direct":
        if process_all_diff_folders is None:
            print("Error: process_all_diff_folders in the extract_diff_sequence module cannot be imported")
            return
        process_all_diff_folders(args.diff_root, args.direct_diff_output)
        diff_data = load_json(args.direct_diff_output)
    else:
        diff_data = load_json(args.diff_json_path)

    retrieval_data = load_json(args.retrieval_json_path)

    group1, group2, group3, all_filtered = filter_and_partition(diff_data, retrieval_data, min_count=args.min_error_count, max_count=args.max_error_count)
    print(">>> The numbers of each group:", len(group1), len(group2), len(group3))
    
    selected_group1 = select_with_diversity(group1, args.group1_count)
    selected_group2 = select_with_diversity(group2, args.group2_count)
    selected_group3 = select_with_diversity(group3, args.group3_count)
    
    final_records = selected_group1 + selected_group2 + selected_group3
    print(">>> Initial selection total number:", len(final_records))
    
    final_records = ensure_min_problem_diversity(final_records, all_filtered, args.min_problem_count)
    
    if len(final_records) > args.total_count:
        final_records = random.sample(final_records, args.total_count)
    elif len(final_records) < args.total_count:
        pool = [r for r in all_filtered if r not in final_records]
        random.shuffle(pool)
        need = args.total_count - len(final_records)
        final_records.extend(pool[:need])
    
    distinct_problem_ids = {r["problem_id"] for r in final_records}
    print(">>> Final records number:", len(final_records))
    print(">>> Number of covered problems:", len(distinct_problem_ids))
    
    tojson(final_records, args.output_file)

if __name__ == "__main__":
    main()
