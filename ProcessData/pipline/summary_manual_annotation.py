import os
from utils.jsonTools import load_json, tojson

json_file_path = 'final_selected_records.json'
output_folder = 'Eval/create_data/output_398'
output_json_path = 'summary_398_2.json'

records = load_json(json_file_path)

filtered_records = []

for record in records:
    submission1_id = record.get("submission1_id")
    if not submission1_id:
        continue

    folder_path = os.path.join(output_folder, submission1_id)
    standard_answer_path = os.path.join(folder_path, 'Standard_answer.txt')

    if not os.path.isfile(standard_answer_path):
        continue

    with open(standard_answer_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    if not content:
        continue

    record["code1_bug_explanations"] = content
    filtered_records.append(record)

tojson(filtered_records, output_json_path)