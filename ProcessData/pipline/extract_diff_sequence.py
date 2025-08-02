#!/usr/bin/env python3
import os
import json
import argparse
from tqdm import tqdm

def extract_diff_sequence(diff_file_path):
    """从 diff 代码文件中提取合并连续相同符号后的 + - 序列"""
    sequence = []
    with open(diff_file_path, "r", encoding="utf-8") as f:
        prev_char = None
        for line in f:
            # 只处理 diff 中真正的变更行，过滤掉文件头等
            if line.startswith("+") and not line.startswith("+++"):
                if prev_char != "+":
                    sequence.append("+")
                prev_char = "+"
            elif line.startswith("-") and not line.startswith("---"):
                if prev_char != "-":
                    sequence.append("-")
                prev_char = "-"
            else:
                # 碰到非 diff 行时，重置 prev_char 使得后续连续的 diff 行可再次合并
                prev_char = None
    return "".join(sequence)

def count_error_groups(merged_sequence: str) -> int:
    """
    根据已合并的序列计算错误组数：
    - 如果当前符号与下一个符号不同（即形成 "+-" 或 "-+"），认为它们构成一组错误，跳过这两个符号；
    - 否则当前符号单独算一组错误。
    """
    i = 0
    groups = 0
    while i < len(merged_sequence):
        if i + 1 < len(merged_sequence) and merged_sequence[i] != merged_sequence[i + 1]:
            groups += 1
            i += 2  # 跳过组成一对的两个符号
        else:
            groups += 1
            i += 1
    return groups

def process_all_diff_folders(diff_root: str, output_json_path: str):
    """
    遍历 diff 文件夹下所有子文件夹（子文件夹名为 submission1_id），
    对每个文件夹中的 {submission1_id}_diff_code.py 文件提取合并后的序列，
    并根据规则计算错误组数，将结果保存为 JSON 格式。
    
    JSON 格式示例：
    {
        "submission1_id": {
            "sequence": "-+--+-+-+--+",
            "error_count": 7
        },
        "another_submission_id": {
            "sequence": "++",
            "error_count": 2
        }
    }
    """
    results = {}
    for submission1_id in tqdm(os.listdir(diff_root), desc="Processing diff folders"):
        folder_path = os.path.join(diff_root, submission1_id)
        if os.path.isdir(folder_path):
            diff_file = os.path.join(folder_path, f"{submission1_id}_diff_code.py")
            if os.path.exists(diff_file):
                merged_sequence = extract_diff_sequence(diff_file)
                error_count = count_error_groups(merged_sequence)
                results[submission1_id] = {
                    "sequence": merged_sequence,
                    "error_count": error_count
                }
            else:
                print(f"Warning: file {submission1_id}_diff_code.py not exist in {folder_path}")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"Processing complete, result saved to {output_json_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract diff sequences and compute error counts")
    parser.add_argument("--diff_root", type=str, default="dataset/diff_code", help="Directory: Store diff folder (each subfolder is a submission1_id)")
    parser.add_argument("--output_json_path", type=str, default="diff_error_counts.json", help="输出 JSON 文件路径")
    args = parser.parse_args()
    process_all_diff_folders(args.diff_root, args.output_json_path)
