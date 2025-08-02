import json
from tqdm import tqdm
from utils.jsonTools import CustomEncoder, load_json
import argparse

def filter_submission_pairs(pair_results, RE_threshold=0.0, lines_threshold = 0, mode="dev"):

    filtered_results = {}

    for pair in tqdm(pair_results, desc="Filtering pairs", unit="pair"):
        submission_id = pair['submission1_id']
        retention_rate = pair['retention_rate']
        
        if submission_id not in filtered_results:
            filtered_results[submission_id] = pair
        else:
            if retention_rate > filtered_results[submission_id]['retention_rate']:
                filtered_results[submission_id] = pair

    final_results = []

    for entries in tqdm(filtered_results.values(), desc="Collecting max pairs", unit="submission", colour="green"):
        if entries['retention_rate'] >= RE_threshold and entries['status1'] == "Wrong Answer" and not entries['original_language1'].startswith("Python (2"):
            if mode == "test":
                if entries['code1_lines'] >= lines_threshold:
                    final_results.append(entries)
            else:
                final_results.append(entries)

    print(f">>> Total valid pairs: {len(final_results)}")
    return final_results

def filter_EVAL_data(data, mode="dev"):
    """
    Filter the data in the JSON file to remove items where code_test_score is not equal to TotalScore or code_test_score is 0
    :param input_file: indicates the path of the input JSON file
    :param output_file: indicates the path of the output JSON file
    """

    filtered_data = [
        item for item in tqdm(data, desc="Filtering Data", unit="item")
        if item.get('code_test_score') == item.get('TotalScore') and item.get('code_test_score') != 0
    ]
    for item in filtered_data:
        item.pop('TotalScore', None)
        item.pop('code_test_score', None)
        item.pop('code_test_status', None)

    print(f">>> Total valid eval pairs: {len(filtered_data)}")

    return filtered_data
    
def parse_args():
    parser = argparse.ArgumentParser(description="Process each record.")
    parser.add_argument('--json_file', required=True, help='JSON file path of all pairs filtered out.')
    parser.add_argument('--output_file', required=True, help='Path to save the output JSON file.')
    parser.add_argument('--mode', required=True, help='dev or train or test')
    parser.add_argument('--threshold', type=float, default=0.6, help='Threshold for saving pairs.')
    parser.add_argument('--lines_threshold', type=int, default=20, help='Lines threshold for saving pairs.')
    parser.add_argument('--IS_SAVE', action='store_true', help='Whether to save the processed data')
    parser.add_argument('--IS_EVAL', action='store_true', help='Whether to filter the evaluated code')

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    pair_results = load_json(args.json_file)

    if args.IS_EVAL:
        filtered_data = filter_EVAL_data(data=pair_results, mode=args.mode)
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=4, cls=CustomEncoder)
        print(f">>> The filtered eval file have saved in {args.output_file}!!!")

    else:
        final_data = filter_submission_pairs(pair_results, mode=args.mode, RE_threshold=args.threshold, lines_threshold=args.lines_threshold)
        if args.IS_SAVE:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                    json.dump(final_data, f, indent=4, cls=CustomEncoder)
            print(f">>> The filtered file have saved in {args.output_file}!!!")