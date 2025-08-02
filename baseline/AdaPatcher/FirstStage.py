import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm
from utils.jsonTools import tojson

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
        self.problem_description = {
            item["Pid"]: item["ProblemText"] for item in problem_info
        }

        # Load submission info
        with open(test_dataset_file, "r", encoding="utf-8") as f:
            submission_info = json.load(f)
        self.submission_info = {
            item["submission1_id"]: item for item in submission_info
        }

        self.results = []

    def _process_submission(self, submission_id: str) -> dict:
        info = self.submission_info[submission_id]
        problem_id = info["problem_id"]
        user_id = info["user_id"]
        description = self.problem_description[problem_id]
        buggy_code = info["code1"]

        prompt = (
            self.prompt_template.replace("<LANGUAGE>", self.language)
            .replace("<TASK_DESCRIPTION>", description)
            .replace("<BUGGY_CODE>", buggy_code)
        )
        if not prompt:
            print("\033[34m>>>Error! Prompt is None!\033[0m")

        # Call the Repair API
        repair = Repair(self.language, API_KEY, API_URL)
        bug_locations, full_content = repair.post(prompt, submission_id=submission_id)

        # Save intermediate files to compute diff
        temp_dir = os.path.join(self.to_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)


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
            "bug_locations": bug_locations,
            "full_bugloc_content": full_content,
        }

    def start(self):
        submission_list = list(self.submission_info.keys())
        all_ids = submission_list.copy()
        processed_ids = []
        retry = False

        for attempt in range(2):  # allow one retry
            current_id = None
            try:
                with ThreadPoolExecutor(max_workers=self.num_thread) as executor:
                    future_to_id = {executor.submit(self._process_submission, sid): sid for sid in all_ids}
                    for future in tqdm.tqdm(as_completed(future_to_id), total=len(all_ids), colour="red", desc="Processing submissions"):
                        current_id = future_to_id[future]
                        processed_ids.append(current_id)
                        self.results.append(future.result())
                break
            except KeyboardInterrupt:
                print(f"KeyboardInterrupt at submission {current_id}")
                timestamp = time.strftime("%m%d%H%M%S")
                temp_results = os.path.join(self.to_dir, f"{timestamp}_temp.json")
                temp_unprocessed = os.path.join(self.to_dir, "unprocessed_ids.json")

                tojson(self.results, temp_results)
                unprocessed = [sid for sid in all_ids if sid not in processed_ids]
                with open(temp_unprocessed, "w", encoding="utf-8") as uf:
                    json.dump(unprocessed, uf, ensure_ascii=False, indent=2)

                if attempt == 0 and unprocessed:
                    print(">>> Retry: processing unprocessed submissions")
                    all_ids = unprocessed
                    retry = True
                    continue
                else:
                    print(">>> No more retries or nothing to retry. Exiting.")
                    break

        # final save
        output_path = os.path.join(self.to_dir, self.save_file_name)
        tojson(self.results, output_path)

class Repair:
    def __init__(self,language,api_key,api_url,temperature=0.2,model_type="gpt-4o-ca",error_log_path="./error.log",):
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
        import requests
        import re
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
                    content = json.loads(response.text).get("choices")[0]["message"]["content"]
                    match = re.search(r'<BUG_LOCATIONS>.*?</BUG_LOCATIONS>', content, re.DOTALL)
                    bug_locations = match.group(0) if match else ""

                    return bug_locations, content
                else:
                    print(f"Error {response.status_code} on {submission_id}, attempt {attempt}")
            except Exception as e:
                with open(self.error_log_path, "a", encoding="utf-8") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {submission_id} - {e}\n")
            time.sleep(1)
        print(f"Failed after retries for {submission_id}")
        return "", ""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Repair')
    parser.add_argument('--language', type=str, default='python', help='Language')
    parser.add_argument('--model', type=str, default='gpt-4o-ca', help='Model type')
    parser.add_argument("--problem_description_file", type=str, default='./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json', help="Problem description file")
    parser.add_argument("--test_dataset_file", type=str, default=r'./test.json', help='test dataset file')
    parser.add_argument("--to_dir", type=str, default='./baseline', help="Directory to save results")
    parser.add_argument("--prompt_template", type=str, default="""You are a skilled programmer experienced in debugging code. Given a programming problem and a piece of buggy code written in <LANGUAGE>, you are required to perform the following tasks:
1. Analyze the code and identify every line that contains a bug.
2. Output only the buggy lines in diff style by prefixing each erroneous line with a single "-".
3. Do NOT provide any corrections or modified code—only mark the bug locations.
4. Wrap the diff output in <BUG_LOCATIONS></BUG_LOCATIONS> tags with no extra text.

[Programming Problem]: <TASK_DESCRIPTION>
[Buggy Code]: <BUGGY_CODE>

Please answer in the following format:
<BUG_LOCATIONS></BUG_LOCATIONS>
""", help="prompt template")
    parser.add_argument("--save_file_name", type=str, default="result.json", help="The path to save data")
    args = parser.parse_args()
    print(f"@@ model: {args.model} @@")
    RepairManager(prompt_template=args.prompt_template, 
                  language=args.language, 
                  test_dataset_file=args.test_dataset_file, 
                  problem_description_file=args.problem_description_file,
                  to_dir=args.to_dir, model=args.model, num_thread=10, 
                  save_file_name=args.save_file_name).start()