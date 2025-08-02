#!/usr/bin/env python3
import json
import random
from collections import defaultdict
import argparse
from utils.jsonTools import CustomEncoder, load_json, tojson

# 尝试导入 extract_diff_sequence 中的 process_all_diff_folders（用于 direct 模式）
try:
    from extract_diff_sequence import process_all_diff_folders
except ImportError:
    process_all_diff_folders = None

def filter_and_partition(diff_data, retrieval_data, min_count = 1, max_count = 10):
    """
    过滤出：
      1. submission1_id 必须在 diff_data 中；
      2. diff_data 对应的 error_count 在 [1, 10] 范围内；
      3. 排除 problem_id 为 "p02974" 的记录。
    并把 RetrievaledData 按 error_count 分为三组：
      group1: error_count == 1
      group2: error_count == 2
      group3: error_count >= 3
    同时将 error_count 信息附加到记录中。
    """
    filtered = []
    for record in retrieval_data:
        sub_id = record.get("submission1_id")
        if sub_id in diff_data:
            ec = diff_data[sub_id].get("error_count")
            if ec is not None and min_count <= ec <= max_count and record["problem_id"] != "p02974":
                record["error_count"] = ec  # 附加错误数信息
                filtered.append(record)
    group1 = [r for r in filtered if r["error_count"] == 1]
    group2 = [r for r in filtered if r["error_count"] == 2]
    group3 = [r for r in filtered if r["error_count"] >= 3]
    return group1, group2, group3, filtered

def select_with_diversity(records, required_count):
    """
    尽量覆盖不同的 problem_id：
      1. 先按 problem_id 分组，每个题目随机选1条；
      2. 如果数量不足，再从剩余记录中随机补足到 required_count 条。
    """
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
    """
    检查最终选取的记录是否覆盖至少 min_problem_count 个不同的 problem_id，
    若不满足，尝试从 all_filtered 中找到未覆盖题目的记录，并替换部分重复记录。
    """
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
    parser.add_argument("--mode", type=str, choices=["file", "direct"], default="file",
                        help="mode: 'file' 从 diff JSON 文件加载数据，'direct' 直接处理 diff 文件夹")
    parser.add_argument("--diff_json_path", type=str, default="diff_error_counts.json", help="Diff JSON 文件路径（file 模式）")
    parser.add_argument("--diff_root", type=str, default="dataset/diff_code", help="diff 文件夹根目录（direct 模式）")
    parser.add_argument("--direct_diff_output", type=str, default="temp_diff_error_counts.json", help="direct 模式时的临时输出 JSON 文件")
    parser.add_argument("--retrieval_json_path", type=str, default="dataset/RetrievaledData/Retrievaled_1011_test_Top3.json", help="待挑选数据")
    parser.add_argument("--group1_count", type=int, default=100, help="error_count==1 select numbers")
    parser.add_argument("--group2_count", type=int, default=200, help="error_count==2 select numbers")
    parser.add_argument("--group3_count", type=int, default=200, help="error_count>=3 select numberss")
    parser.add_argument("--total_count", type=int, default=500, help="Final recorded total")
    parser.add_argument("--min_problem_count", type=int, default=85, help="Minimum number of different problems to cover")
    parser.add_argument("--output_file", type=str, default="final_selected_records.json", help="The final output JSON file")
    parser.add_argument("--min_error_count", type=int, default=1, help="挑选过程中error_count的最小值")
    parser.add_argument("--max_error_count", type=int, default=10, help="挑选过程中error_count的最大值")
    args = parser.parse_args()

    # 获取 diff_data：若 direct 模式，则调用 extract_diff_sequence 直接处理 diff 文件夹
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
