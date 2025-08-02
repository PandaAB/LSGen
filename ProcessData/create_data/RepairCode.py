import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm
from utils.jsonTools import tojson
import re
from utils.Retention_rate_compute import save_python_file, get_diff_stats, save_temp_file
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
        model="gpt-4o",
    ) -> None:
        self.prompt_template = prompt_template
        self.language = language
        self.to_dir = to_dir
        self.num_thread = num_thread
        self.model = model
        self.save_file_name = save_file_name

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
        info = self.submission_info[submission_id]
        problem_id = info["problem_id"]
        user_id = info["user_id"]
        description = self.problem_description.get(problem_id, "")
        buggy_code = info["code1"]

        prompt = (
            self.prompt_template.replace("<LANGUAGE>", self.language)
            .replace("<TASK_DESCRIPTION>", description)
            .replace("<BUGGY_CODE>", buggy_code)
        )
        if not prompt:
            print("\033[34m>>>Error! Prompt is None!\033[0m")

        repair = Repair(self.language, API_KEY, API_URL, model_type=self.model)
        gen_bug_desc, repaired_code, full_content = repair.post(prompt, submission_id)

        res = {
                "user_id": user_id,
                "problem_id": problem_id,
                "submission1_id": submission_id,
                "code1": buggy_code,
                "code2": info["code2"],
                "code1_bug_descriptions": info["code1_bug_descriptions"],
                "code1_lines": info["code1_lines"],
                "code1_test_status": info["code1_test_status"],
                "user_consistency": info["user_consistency"],
                "code_content": repaired_code,
                "gen_code1_bug_descriptions": gen_bug_desc,
                "ori_content": full_content,
        }
        return res

    def start(self):
        submission_list = list(self.submission_info.keys())
        total = len(submission_list)
        processed_ids = []
        current_id = None
        try:
            with ThreadPoolExecutor(max_workers=self.num_thread) as executor:
                future_to_id = {executor.submit(self._process_submission, sid): sid for sid in submission_list}
                for future in tqdm.tqdm(as_completed(future_to_id), total=total, colour="red", desc="Processing submissions"):
                    current_id = future_to_id[future]
                    res = future.result()
                    self.results.append(res)
                    processed_ids.append(current_id)
        except KeyboardInterrupt:
            print(f"KeyboardInterrupt at submission {current_id}")
            # Save processed and unprocessed IDs
            import datetime
            timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")
            temp_results = os.path.join(self.to_dir, f"{timestamp}_temp.json")
            temp_unprocessed = os.path.join(self.to_dir, "unprocessed_ids.json")

            tojson(self.results, temp_results)
            unprocessed = [sid for sid in submission_list if sid not in processed_ids]
            with open(temp_unprocessed, "w", encoding="utf-8") as uf:
                json.dump(unprocessed, uf, ensure_ascii=False, indent=2)
                
            print(f">>> Saved processed results to {temp_results} and unprocessed IDs to {temp_unprocessed}")

        output_path = os.path.join(self.to_dir, self.save_file_name)
        tojson(self.results, output_path)


class Repair:
    def __init__(self, language, api_key, api_url, temperature=0.2, max_tokens=4096,
        model_type="gpt-4o", error_log_path="./error.log"):
        self.language = language
        self.api_key = api_key
        self.model_type = model_type
        self.api_url = api_url
        self.temperature = temperature
        self.headers = {
            "Authorization": self.api_key,
            "User-Agent": "",
            "Content-Type": "application/json",
        }
        self.error_log_path = error_log_path

    def post(self, prompt: str, submission_id: str) -> tuple[str, str, str]:

        payload = json.dumps(
            {
                "model": self.model_type,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
            }
        )
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.request("POST", self.api_url, headers=self.headers, data=payload)
                if response.status_code == 200:
                    bug_description = ""
                    content = json.loads(response.text).get("choices")[0]["message"]["content"]
                    # Extract bug description
                    match = re.search(r'<DESCRIPTIONS_LIST>.*?</DESCRIPTIONS_LIST>', content, re.DOTALL)
                    bug_description = match.group(0) if match else ""
                    # Extract code
                    repaired_code = ""
                    if content.find('```') != -1:
                        if f' {self.language}' in content.split('```')[1]:
                            repaired_code = content.split('```')[1].removeprefix(f" {self.language}")
                        else:
                            repaired_code = content.split('```')[1].removeprefix(f"{self.language}")
                    if bug_description != "" and repaired_code != "":
                        return bug_description, repaired_code, content
                else:
                    print(f"Error with submission {submission_id}: Status {response.status_code}, attempt {attempt}")
            except Exception as e:
                print(f"Exception on submission {submission_id}: {e}, attempt {attempt}")
                with open(self.error_log_path, "a", encoding="utf-8") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Submission {submission_id} - Attempt {attempt}\n{prompt}\n{e}\n")
            time.sleep(1)  # brief pause before retry
        print(f"\033[31m>>> Failed after {max_retries} attempts for submission {submission_id}\033[0m")
        return "", "", "Request failed after retries"


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Repair')
    parser.add_argument('--language', type=str, default='python', help='Language')
    parser.add_argument('--model', type=str, default='gpt-4o-ca', help='Model type')
    parser.add_argument("--problem_description_file", type=str, default='./repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json', help="Problem description file")
    parser.add_argument("--test_dataset_file", type=str, default='./test.json', help='test dataset file')
    parser.add_argument("--to_dir", type=str, default='./baseline', help="Directory to save results")
    parser.add_argument("--prompt_template", type=str, default="""You are a skilled programmer experienced in debugging and providing optimal code fixes. Given a programming problem and a piece of buggy code written in <LANGUAGE>, you are required to perform the following tasks:
    1. Fix the Buggy Code: Fix the buggy code to meet the problem's requirements, ensuring that the changes are minimal to preserve the original structure and logic as much as possible.
    2. Provide Bug Descriptions: Provide clear and complete point-by-point descriptions of the bugs present in the buggy code. Please do not include any fix suggestions in each description. Each bug description should be wrapped with <DESCRIPTION></DESCRIPTION> tags.  All bug descriptions should be wrapped in <DESCRIPTIONS_LIST></DESCRIPTIONS_LIST> tags.
Programming Problem: <TASK_DESCRIPTION>
Buggy Code: <BUGGY_CODE>
Please answer in the following format:
Repaired Code:
```python
Bug Descriptions:
<DESCRIPTIONS_LIST></DESCRIPTIONS_LIST>
""", help="prompt template")
    parser.add_argument("--save_file_name", type=str, default="result.json", help="The path to save data")
    args = parser.parse_args()

    RepairManager(
        prompt_template=args.prompt_template,
        language=args.language,
        test_dataset_file=args.test_dataset_file,
        problem_description_file=args.problem_description_file,
        to_dir=args.to_dir,
        model=args.model,
        num_thread=10,
        save_file_name=args.save_file_name,
    ).start()