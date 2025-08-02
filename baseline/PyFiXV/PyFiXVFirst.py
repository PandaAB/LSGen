import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm
from utils.jsonTools import tojson
import re
from utils.Retention_rate_compute import save_python_file, get_diff_stats, save_temp_file, get_diff_code
import requests

API_KEY = ""
API_URL = ""

class RepairManager:
    def __init__(
        self,
        prompt_template: str,
        language: str,
        test_dataset_file: str,
        problem_description_file: str,
        to_dir: str,
        save_file_name: str,
        num_thread: int = 10,
        model="gpt-4o-ca",
    ) -> None:
        self.prompt_template = prompt_template
        self.language = language
        self.to_dir = to_dir
        self.num_thread = num_thread
        self.model = model
        self.save_file_name = save_file_name

        os.makedirs(self.to_dir, exist_ok=True)

        with open(problem_description_file, "r", encoding="utf-8") as f:
            problem_info = json.load(f)
        self.problem_description = {item["Pid"]: item["ProblemText"] for item in problem_info}

        with open(test_dataset_file, "r", encoding="utf-8") as f:
            submission_info = json.load(f)
        self.submission_info = {item["submission1_id"]: item for item in submission_info}
        self.results = []

    def _process_submission(self, submission_id: str) -> dict:
        info = self.submission_info[submission_id]
        problem_id = info.get("problem_id", "")
        user_id = info.get("user_id", "")
        description = self.problem_description.get(problem_id, "")
        buggy_code = info.get("code1", "")
        prompt = (
            self.prompt_template.replace("<LANGUAGE>", self.language)
            .replace("<TASK_DESCRIPTION>", description)
            .replace("<BUGGY_CODE>", buggy_code)
        )

        repair = Repair(self.language, API_KEY, API_URL, model_type=self.model)
        repaired_code, full_content = repair.post(prompt, submission_id)

        temp_dir = os.path.join(self.to_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        code1_fn, code2_fn = save_python_file(
            buggy_code, repaired_code, temp_dir,
            name1=f"{submission_id}_code1.py", name2=f"{submission_id}_code2.py"
        )
        py1, py2 = save_temp_file(
            code1_fn, code2_fn, temp_dir,
            name1=f"{submission_id}_code1.py", name2=f"{submission_id}_code2.py"
        )
        diff_code = get_diff_code(py1, py2)
        added, removed = get_diff_stats(py1, py2)
        s = info.get("code1_lines", 0)
        consistency = (s - removed) * 1.0 / (s + added - removed) if (s + added - removed) != 0 else 0.0

        for fpath in (code1_fn, code2_fn):
            try: os.remove(fpath)
            except: pass

        return {
            "user_id": user_id,
            "problem_id": problem_id,
            "submission1_id": submission_id,
            "code1": buggy_code,
            "code2": info.get("code2", ""),
            "code1_bug_descriptions": info.get("code1_bug_descriptions", ""),
            "code1_lines": s,
            "code1_test_status": info.get("code1_test_status", ""),
            "user_consistency": info.get("user_consistency", 0),
            "code_content": repaired_code,
            "diff_code": diff_code,
            "repaired_consistency": consistency,
            "code_ori_content": full_content,
        }

    def start(self):
        all_ids = list(self.submission_info.keys())
        processed = []
        for attempt in range(5):
            current = None
            try:
                with ThreadPoolExecutor(max_workers=self.num_thread) as executor:
                    futures = {executor.submit(self._process_submission, sid): sid for sid in all_ids}
                    for fut in tqdm.tqdm(as_completed(futures), total=len(all_ids), colour="red", desc="Processing submissions"):
                        current = futures[fut]
                        self.results.append(fut.result())
                        processed.append(current)
                break
            except KeyboardInterrupt:
                print(f"KeyboardInterrupt at submission {current}")
                ts = time.strftime("%m%d%H%M%S")
                tmp_res = os.path.join(self.to_dir, f"{ts}_temp.json")
                tojson(self.results, tmp_res)
                unproc = [sid for sid in all_ids if sid not in processed]
                with open(os.path.join(self.to_dir, "unprocessed_ids.json"), "w", encoding="utf-8") as f:
                    json.dump(unproc, f, ensure_ascii=False, indent=2)
                if attempt != 4 and unproc:
                    print(">>> Retrying unprocessed submissions...")
                    all_ids = unproc
                    continue
                else:
                    print(">>> No more retries or nothing to retry. Exiting.")
                    break
        out = os.path.join(self.to_dir, self.save_file_name)
        tojson(self.results, out)

class Repair:
    def __init__(self, language, api_key, api_url, temperature=0.2, max_tokens=4096,
                 model_type="gpt-4o-ca", error_log_path="./error.log"):
        self.language = language
        self.api_key = api_key
        self.model_type = model_type
        self.api_url = api_url
        self.temperature = temperature
        self.headers = {"Authorization": self.api_key, "User-Agent": "", "Content-Type": "application/json"}
        self.error_log_path = error_log_path

    def post(self, prompt: str, submission_id: str) -> tuple[str, str]:
        payload = json.dumps({"model": self.model_type, "messages": [{"role": "user", "content": prompt}], "temperature": self.temperature})
        for attempt in range(1, 6):
            try:
                resp = requests.request("POST", self.api_url, headers=self.headers, data=payload)
                if resp.status_code == 200:
                    content = json.loads(resp.text)["choices"][0]["message"]["content"]
                    if '```' in content:
                        block = content.split('```')[1]
                        prefix = f" {self.language}" if f" {self.language}" in block else self.language
                        code = block.removeprefix(prefix)
                        return code, content
                else:
                    print(f"Error {resp.status_code} on {submission_id}, attempt {attempt}")
            except Exception as e:
                with open(self.error_log_path, "a", encoding="utf-8") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {submission_id} - {e}\n")
            time.sleep(1)
        print(f"Failed after retries for {submission_id}")
        return "", ""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Repair')
    parser.add_argument('--language', type=str, default='python')
    parser.add_argument('--model', type=str, default='gpt-4o-ca')
    parser.add_argument("--problem_description_file", type=str, default='./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json')
    parser.add_argument("--test_dataset_file", type=str, default='./test.json')
    parser.add_argument("--to_dir", type=str, default='./baseline')
    parser.add_argument("--prompt_template", type=str, default="""You are a skilled programmer experienced in debugging and providing optimal code fixes. Given a programming problem and a piece of buggy code written in <LANGUAGE>, you are required to fix the buggy code to meet the problem's requirements, please ensuring that the changes are minimal to preserve the original structure and logic as much as possible.
[Programming Problem]: <TASK_DESCRIPTION>
[Buggy Code]: <BUGGY_CODE>
[Please answer in the following format]:
Repaired Code:
```python
```
""")
    parser.add_argument("--save_file_name", type=str, default="result.json")
    args = parser.parse_args()


    RepairManager(
        prompt_template=args.prompt_template,
        language=args.language,
        test_dataset_file=args.test_dataset_file,
        problem_description_file=args.problem_description_file,
        to_dir=args.to_dir,
        save_file_name=args.save_file_name,
        model=args.model
    ).start()
