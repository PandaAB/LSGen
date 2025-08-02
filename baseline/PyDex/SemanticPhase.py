import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm
from utils.jsonTools import tojson
from utils.Retention_rate_compute import (
    save_python_file,
    get_diff_stats,
    save_temp_file,
    get_diff_code
)

API_KEY = ""
API_URL = ""


class RepairManager:
    def __init__(self, prompt_template: str, language: str, test_dataset_file: str, problem_description_file: str,
                 to_dir: str, save_file_name: str, num_thread: int = 10, model="gpt-4o-ca", topk=5) -> None:
        self.prompt_template = prompt_template
        self.language = language
        self.to_dir = to_dir
        self.num_thread = num_thread
        self.model = model
        self.save_file_name = save_file_name
        self.topk = int(topk)

        if not os.path.exists(self.to_dir):
            os.mkdir(self.to_dir)

        # Load problem descriptions
        with open(problem_description_file, "r", encoding="utf-8") as f:
            problem_info = json.load(f)
        self.problem_description = {item["Pid"]: item["ProblemText"] for item in problem_info}

        # Load submission info
        with open(test_dataset_file, "r", encoding="utf-8") as f:
            submission_info = json.load(f)
        self.submission_info = {item["submission1_id"]: item for item in submission_info}

        self.results = []

    def _process_submission(self, submission_id: str) -> dict:
        # (unchanged implementation)
        info = self.submission_info[submission_id]
        problem_id = info["problem_id"]
        user_id = info["user_id"]
        description = self.problem_description[problem_id]
        top_k_results = info["top_k_results"]

        buggy_code = info["code1"]
        all_references = [(entry['RetrievalCode'], entry['RetrievalCodeCorrect']) for entry in top_k_results]
        all_references_code = []
        for each in all_references:
            t = f"Buggy Code:\n{each[0]}\nCorrect Code:\n{each[1]}"
            all_references_code.append(t)
        references_code = "\n".join(all_references_code[:self.topk])

        prompt = (
            self.prompt_template.replace("<LANGUAGE>", self.language)
            .replace("<TASK_DESCRIPTION>", description)
            .replace("<BUGGY_CODE>", buggy_code)
            .replace("<REFERENCES>", references_code)
        )
        if not prompt:
            print("\033[34m>>>Error! Prompt is None!\033[0m")

        repair = Repair(self.language, API_KEY, API_URL)
        gen_bug_desc, repaired_code, full_content = repair.post(prompt, submission_id=submission_id)

        temp_dir = os.path.join(self.to_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        code1_filename, code2_filename = save_python_file(
            buggy_code,
            repaired_code,
            temp_dir,
            name1=f"{submission_id}_code1.py",
            name2=f"{submission_id}_code2.py",
        )

        py_file1, py_file2 = save_temp_file(
            code1_filename,
            code2_filename,
            temp_dir,
            name1=f"{submission_id}_code1.py",
            name2=f"{submission_id}_code2.py",
        )
        diff_code = get_diff_code(py_file1, py_file2)
        added_lines, removed_lines = get_diff_stats(py_file1, py_file2)
        a = added_lines
        b = removed_lines
        s = info.get("code1_lines", 0)
        consistency = (s - b) * 1.0 / (s + a - b) if (s + a - b) != 0 else 0.0

        for fpath in (code1_filename, code2_filename):
            try:
                os.remove(fpath)
            except Exception:
                pass

        return {
            "user_id": user_id,
            "problem_id": problem_id,
            "submission1_id": submission_id,
            "code1": info["code1"],
            "code2": info.get("code2", ""),
            "code1_bug_descriptions": info.get("code1_bug_descriptions", ""),
            "code1_lines": info.get("code1_lines", 0),
            "code1_test_status": info.get("code1_test_status", ""),
            "user_consistency": info.get("user_consistency", 0),
            "code_content": repaired_code,
            "diff_code": diff_code,
            "repaired_consistency": consistency,
            "gen_code1_bug_descriptions": gen_bug_desc,
            "ori_content": full_content,
            "top_k_results": info.get("top_k_results", []),
            "retrieval_code_bug_desc": info.get("retrieval_code_bug_desc", [])
        }

    def start(self):
        """
        Process submissions, retry unprocessed once after KeyboardInterrupt.
        """
        submission_list = list(self.submission_info.keys())
        retry = False
        processed_ids = []

        for attempt in range(2):  # allow one retry
            current_id = None
            try:
                with ThreadPoolExecutor(max_workers=self.num_thread) as executor:
                    future_to_id = {executor.submit(self._process_submission, sid): sid for sid in submission_list}
                    for future in tqdm.tqdm(as_completed(future_to_id), total=len(submission_list),
                                             colour="red", desc="Processing submissions"):
                        current_id = future_to_id[future]
                        processed_ids.append(current_id)
                        self.results.append(future.result())
                break
            except KeyboardInterrupt:
                print(f"KeyboardInterrupt at submission {current_id}")
                # save progress
                timestamp = time.strftime("%m%d%H%M%S")
                temp_results = os.path.join(self.to_dir, f"{timestamp}_temp.json")
                tojson(self.results, temp_results)
                unprocessed = [sid for sid in submission_list if sid not in processed_ids]
                with open(os.path.join(self.to_dir, "unprocessed_ids.json"), "w", encoding="utf-8") as uf:
                    json.dump(unprocessed, uf, ensure_ascii=False, indent=2)
                if attempt == 0:
                    print("Retrying unprocessed submissions...")
                    submission_list = unprocessed
                    retry = True
                    continue
                else:
                    print("\033[91mAlready retried once. Exiting.\033[0m")
                    break

        # final save
        output_path = os.path.join(self.to_dir, self.save_file_name)
        tojson(self.results, output_path)


class Repair:
    # unchanged
    def __init__(self, language, api_key, api_url, temperature=0.2, model_type="gpt-4o-ca",
                 error_log_path="./error.log"):
        self.temperature = temperature
        self.language = language
        self.api_key = api_key
        self.model_type = model_type
        self.api_url = api_url
        self.headers = {
            "Authorization": self.api_key,
            "User-Agent": "",
            "Content-Type": "application/json",
        }
        self.error_log_path = error_log_path

    def post(self, prompt: str, submission_id: str) -> tuple[str, str, str]:
        import requests, re
        payload = json.dumps({
            "model": self.model_type,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        })
        for attempt in range(1, 6):
            try:
                response = requests.request("POST", self.api_url, headers=self.headers, data=payload)
                if response.status_code == 200:
                    content = json.loads(response.text)["choices"][0]["message"]["content"]
                    match = re.search(r'<DESCRIPTIONS_LIST>.*?</DESCRIPTIONS_LIST>', content, re.DOTALL)
                    bug_description = match.group(0) if match else ""
                    if '```' in content:
                        parts = content.split('```')
                        code_block = parts[1]
                        lang_prefix = f" {self.language}" if f" {self.language}" in code_block else self.language
                        repaired_code = code_block.removeprefix(lang_prefix)
                    else:
                        repaired_code = ""
                    if repaired_code != "" and bug_description != "":
                        return bug_description, repaired_code, content
                    else:
                        print(f"Warning: No code block or bug description found in response for {submission_id}, attempt {attempt}")
                else:
                    print(f"Error {response.status_code} on {submission_id}, attempt {attempt}")
            except Exception as e:
                with open(self.error_log_path, "a", encoding="utf-8") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {submission_id} - {e}\n")
            time.sleep(1)
        print(f"Failed after retries for {submission_id}")
        return "", "", ""


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Repair')
    parser.add_argument('--language', type=str, default='python', help='Language')
    parser.add_argument('--model', type=str, default='gpt-4o', help='Model type')
    parser.add_argument("--problem_description_file", type=str, default='./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json', help="Problem description file")
    parser.add_argument("--test_dataset_file", type=str, default='./test.json', help='test dataset file')
    parser.add_argument("--to_dir", type=str, default='./baseline', help="Directory to save results")
    parser.add_argument("--prompt_template", type=str, default="""You are a skilled programmer experienced in debugging and providing optimal code fixes. Given a programming problem and a piece of buggy code written in <LANGUAGE>, you are required to perform the following tasks: 
    1. Fix the Buggy Code: Fix the buggy code to meet the problem's requirements, ensuring that the changes are minimal to preserve the original structure and logic as much as possible.
    2. Provide Bug Descriptions: Provide clear and complete point-by-point descriptions of the bugs present in the buggy code. Please do not include any fix suggestions in each description. Each bug description should be wrapped with <DESCRIPTION></DESCRIPTION> tags. All bug descriptions should be wrapped in <DESCRIPTIONS_LIST></DESCRIPTIONS_LIST> tags.
Reference buggy code and corresponding correct code will be provided to you, please refer to them selectively.
[Programming Problem]: <TASK_DESCRIPTION>
[Reference buggy code and corresponding correct code]: <REFERENCES>
[Buggy Code]: <BUGGY_CODE>
[Please answer in the following format]:
Repaired Code:
```python
```
Bug Descriptions:
<DESCRIPTIONS_LIST></DESCRIPTIONS_LIST>
""", help="prompt template")
    parser.add_argument("--save_file_name", type=str, default="result.json", help="The path to save data")
    parser.add_argument("--topk", default=5, help="Topk")
    args = parser.parse_args()

    print(f"@@ TopK: {args.topk} @@")
    print(f"@@ model: {args.model} @@")
    RepairManager(prompt_template=args.prompt_template, 
                  language=args.language, 
                  test_dataset_file=args.test_dataset_file, 
                  problem_description_file=args.problem_description_file,
                  to_dir=args.to_dir, model=args.model, num_thread=10, 
                  save_file_name=args.save_file_name,
                  topk=args.topk).start()