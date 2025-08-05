#!/usr/bin/env python3
import os
import json
import argparse
from tqdm import tqdm

def extract_diff_sequence(diff_file_path):
    sequence = []
    with open(diff_file_path, "r", encoding="utf-8") as f:
        prev_char = None
        for line in f:
            if line.startswith("+") and not line.startswith("+++"):
                if prev_char != "+":
                    sequence.append("+")
                prev_char = "+"
            elif line.startswith("-") and not line.startswith("---"):
                if prev_char != "-":
                    sequence.append("-")
                prev_char = "-"
            else:
                prev_char = None
    return "".join(sequence)

def count_error_groups(merged_sequence: str) -> int:
    i = 0
    groups = 0
    while i < len(merged_sequence):
        if i + 1 < len(merged_sequence) and merged_sequence[i] != merged_sequence[i + 1]:
            groups += 1
            i += 2 
        else:
            groups += 1
            i += 1
    return groups

def process_all_diff_folders(diff_root: str, output_json_path: str):
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
    parser.add_argument("--output_json_path", type=str, default="diff_error_counts.json")
    args = parser.parse_args()
    process_all_diff_folders(args.diff_root, args.output_json_path)
