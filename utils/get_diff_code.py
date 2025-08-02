import os
import json
import argparse
from utils.Retention_rate_compute import get_diff_code
from utils.jsonTools import load_json
from tqdm import tqdm

def process_submission_info(submission_info_list, output_root, top_k_len, min_code_lines):
    os.makedirs(output_root, exist_ok=True)

    for record in tqdm(submission_info_list, colour="red", desc="Processing items"):
        if "top_k_results" in record:
            if len(record["top_k_results"]) == top_k_len and record["code1_lines"] >= min_code_lines:
                process_record(record, output_root)
        else:
            if record["code1_lines"] >= min_code_lines:
                process_record(record, output_root)

def process_record(record, output_root):
    submission1_id = record["submission1_id"]
    code1 = record["code1"] + "\n"
    code2 = record["code2"] + "\n"
    
    code1_filename, code2_filename = f"{submission1_id}_code1.py", f"{submission1_id}_code2.py"
    
    output_folder = os.path.join(output_root, submission1_id)
    os.makedirs(output_folder, exist_ok=True)
    code1_output_path = os.path.join(output_folder, code1_filename)
    code2_output_path = os.path.join(output_folder, code2_filename)
    
    with open(code1_output_path, "w", encoding="utf-8") as f:
        f.write(code1)
    with open(code2_output_path, "w", encoding="utf-8") as f:
        f.write(code2)

    diff_code = get_diff_code(code1_output_path, code2_output_path)
    diff_code_output_path = os.path.join(output_folder, f"{submission1_id}_diff_code.py")

    with open(diff_code_output_path, "w", encoding="utf-8") as f:
        f.write(diff_code)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process code submissions and generate diff files.")
    parser.add_argument("--json_path", type=str, help="Path to the input JSON file")
    parser.add_argument("--output_root", type=str, help="Root directory to save the output")
    parser.add_argument("--top_k_len", type=int, default=3, help="Length of top_k_results to filter by (default is 3)")
    parser.add_argument("--min_code_lines", type=int, default=10, help="Minimum number of lines for code1 (default is 10)")
    
    args = parser.parse_args()

    submission_info_list = load_json(args.json_path)
    process_submission_info(submission_info_list, args.output_root, args.top_k_len, args.min_code_lines)
