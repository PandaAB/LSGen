from utils.jsonTools import load_json, tojson
import argparse

def filter_results(eval_file, initial_file, output_temp, output_passed):
    """
    1. 从 eval_file 中筛选：
       - 通过数据（A）：code_test_score == TotalScore 且不等于 0
       - 失败数据（B）：其余数据
    2. 从 initial_file 中提取失败数据的 base submission_id 对应的数据
    """
    eval_data = load_json(eval_file)
    initial_data = load_json(initial_file)

    passed_data = []
    failed_base_ids = set()
    t = set()

    # Filter passed (A) and failed (B) data
    for record in eval_data:
        if record.get("code_test_score") == record.get("TotalScore") and record.get("code_test_score") != 0:
            passed_data.append(record)
            t.add((record.get("submission1_id", "")).split("_")[0])
        else:
            submission_id = record.get("submission1_id", "")
            base_id = submission_id.split("_")[0]
            if base_id not in t:
                failed_base_ids.add(base_id)
    
    intersection = failed_base_ids & t
    failed_base_ids = failed_base_ids - intersection

    # If new data passes, it is appended to the final output file
    try:
        existing_passed = load_json(output_passed)
    except FileNotFoundError:
        existing_passed = []

    final_passed = existing_passed + passed_data
    tojson(final_passed, output_passed)
    print(f">>> Number of passed records: {len(final_passed)}, Saved to {output_passed}")

    new_repair_data = [rec for rec in initial_data if rec.get("submission1_id", "").split("_")[0] in failed_base_ids]

    if new_repair_data:
        tojson(new_repair_data, output_temp)
        print(f"=== Filtered {len(new_repair_data)} repair ids to be repired, saved to {output_temp} ===")
    else:
        open(output_temp, "w").close()
        print("\033[34mAll data is passed, ending the loop. \033[0m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter assessment results and generate data to be repaired")
    parser.add_argument("--eval_file", type=str, required=True, help="Evaluation result JSON file")
    parser.add_argument("--initial_file", type=str, required=True, help="Initial data set JSON file")
    parser.add_argument("--output_temp", type=str, required=True, help="JSON file of the data to be repaired")
    parser.add_argument("--output_passed", type=str, required=True, help="Final data through JSON file")

    args = parser.parse_args()
    filter_results(args.eval_file, args.initial_file, args.output_temp, args.output_passed)
