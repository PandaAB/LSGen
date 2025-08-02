import os
import json
import random
import pandas as pd
import argparse
from tqdm import tqdm
from utils.Retention_rate_compute import get_file_line_count, get_diff_stats, get_diff_code, save_temp_file
from utils.jsonTools import CustomEncoder

def load_problem_ids(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def read_python_code(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def find_matching_files(folder_path, submission_id1, submission_id2):
    py_file1 = None
    py_file2 = None
    for file in os.listdir(folder_path):
        if file.endswith('.py'):
            if file.startswith(submission_id1):
                py_file1 = os.path.join(folder_path, file)
            elif file.startswith(submission_id2):
                py_file2 = os.path.join(folder_path, file)
    return py_file1, py_file2

def process_single_csv(csv_file_path, problem_id, data_folder_path, threshold, pair_results, language='Python', lines_threshold=20) :
    df = pd.read_csv(csv_file_path)

    filtered_df = df[df['language'] == language]
    
    filtered_df = filtered_df.sort_values(by='date')

    for user_id, user_df in tqdm(filtered_df.groupby('user_id'), desc=f"Processing Users({problem_id})", unit="user", colour="blue"):
        process_user_submissions(user_id, user_df, problem_id, data_folder_path, threshold, pair_results, language, lines_threshold)

def process_user_submissions(user_id, user_df, problem_id, data_folder_path, threshold, pair_results, language='Python', lines_threshold=20):
    submissions = user_df.to_dict(orient='records')

    for i in range(len(submissions)):
        for j in range(i + 1, len(submissions)):
            status1, status2 = submissions[i]['status'], submissions[j]['status']
            
            if status1 != 'Accepted' and status2 == 'Accepted':
                submission_pair = {
                    'user_id': user_id,
                    'problem_id': problem_id,
                    'submission1_id': submissions[i]['submission_id'],
                    'submission2_id': submissions[j]['submission_id'],
                    'status1': status1,
                    'status2': status2,
                    'data1': submissions[i]['date'],
                    'data2': submissions[j]['date'],
                    'original_language1': submissions[i]['original_language'],
                    'original_language2': submissions[j]['original_language'],
                    'original_code1': '',
                    'original_code2': '',
                    'code1': '',
                    'code2': '',
                    'diff_code': '',
                    'code1_lines': 0,
                    'code2_lines': 0,
                    'added_lines': 0,
                    'removed_lines': 0,
                    'retention_rate': 0.0,
                    # 'flag': False,
                }

                folder_path = os.path.join(data_folder_path, f'{problem_id}', language)
                py_file1, py_file2 = find_matching_files(folder_path, submissions[i]['submission_id'], submissions[j]['submission_id'])
                
                if py_file1 and py_file2:
                    submission_pair['original_code1'] = read_python_code(py_file1)
                    submission_pair['original_code2'] = read_python_code(py_file2)
                    py_file1, py_file2 = save_temp_file(py_file1, py_file2, "ProcessData/Get_Filtered_Data/temp")
                    submission_pair['code1'] = read_python_code(py_file1)
                    submission_pair['code2'] = read_python_code(py_file2)
                    submission_pair['code1_lines'] = get_file_line_count(py_file1)
                    submission_pair['code2_lines'] = get_file_line_count(py_file2)
                    added_lines, removed_lines = get_diff_stats(py_file1, py_file2)
                    submission_pair['added_lines'] = added_lines
                    submission_pair['removed_lines'] = removed_lines
                    a = submission_pair['added_lines']
                    b = submission_pair['removed_lines']
                    s = submission_pair['code1_lines']
                    retention_rate = (s - b) * 1.0 / (s + a - b)

                    submission_pair['retention_rate'] = retention_rate
                    submission_pair['diff_code'] = get_diff_code(py_file1, py_file2)

                    pair_results.append(submission_pair)


def process_csv_files(csv_folder_path, data_folder_path, output_file, problem_ids, threshold, language='Python', lines_threshold=20):
    pair_results = []

    num = 0
    for csv_file in tqdm(sorted(os.listdir(csv_folder_path)), desc="Processing CSVs", unit="file", colour="red"):
        if csv_file.endswith('.csv'):
            problem_id = csv_file.split('.')[0]

            if problem_id in problem_ids:
                num += 1
                csv_file_path = os.path.join(csv_folder_path, csv_file)
                process_single_csv(csv_file_path, problem_id, data_folder_path, threshold, pair_results, language = language, lines_threshold=lines_threshold)
                
    
    print(f"Total pairs: {len(pair_results)}")
    print(f"Total problems: {num}")


    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pair_results, f, indent=4, cls=CustomEncoder)

def parse_args():
    parser = argparse.ArgumentParser(description="Process CSV files and match Python submissions.")
    parser.add_argument('--csv_folder', required=True, help='Path to the folder containing CSV files.')
    parser.add_argument('--data_folder', required=True, help='Path to the folder containing data.')
    parser.add_argument('--json_file', required=True, help='Path to the JSON file with problem IDs.')
    parser.add_argument('--output_file', required=True, help='Path to save the output JSON file.')
    parser.add_argument('--language', required=True, help='This specifies the programming language to filter the submissions.')
    parser.add_argument('--threshold', type=float, default=0.5, help='Threshold for saving pairs.')
    parser.add_argument('--lines_threshold', type=int, default=20, help='Threshold for saving pairs.')

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    problem_ids = load_problem_ids(args.json_file)
    process_csv_files(args.csv_folder, args.data_folder, args.output_file, problem_ids, args.threshold, args.language, args.lines_threshold)
