import os
import json
from collections import OrderedDict
from utils.Retention_rate_compute import save_python_file, get_diff_stats, get_file_line_count, save_temp_file
from utils.jsonTools import tojson
from tqdm import tqdm

def insert_user_consistency(record, consistency_value):
    new_record = OrderedDict()
    for key, value in record.items():
        new_record[key] = value
        if key == "code1_lines":
            new_record["user_consistency"] = consistency_value
    return new_record

def process_json():
    with open(input_json_file, "r", encoding="utf-8") as f:
        data = json.load(f, object_pairs_hook=OrderedDict)

    new_data = []
    for record in tqdm(data):
        submission1_id = record.get("submission1_id")
        folder_path = os.path.join("temp_output_folder", submission1_id)
        py_file1 = os.path.join(folder_path, f"{submission1_id}_code1.py")
        py_file2 = os.path.join(folder_path, f"{submission1_id}_code2.py")
        
        if not os.path.exists(py_file1) or not os.path.exists(py_file2):
            print(f"Warning: file not found {py_file1} or {py_file2}")
            consistency = None
        else:
            try:
                a, b = get_diff_stats(py_file1, py_file2)
                s = get_file_line_count(py_file1)
                if (s + a - b) != 0:
                    consistency = (s - b) * 1.0 / (s + a - b)
                else:
                    consistency = 0
            except Exception as e:
                print(f"Error processing {submission1_id}: {e}")
                consistency = None

        new_record = insert_user_consistency(record, consistency)
        new_data.append(new_record)

    tojson(new_data, output_json_file)

if __name__ == "__main__":
    input_json_file = "data/427/427.json"
    output_json_file = "data/427/new_427.json"
    process_json()
