import argparse
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.jsonTools import tojson
from Chunker import Chunker
from utils.jsonTools import load_json, tojson

API_KEY = ""
API_URL = ""

class RepairManager:
    def __init__(self, prompt_template: str, language: str, test_dataset_file: str,
            to_dir: str, save_file_name: str, num_thread: int = 10, model="gpt-4o-ca", iter=1) -> None:
        
        self.prompt_template = prompt_template
        self.language = language
        self.test_dataset_file = test_dataset_file
        self.to_dir = to_dir
        self.num_thread = num_thread
        self.model = model
        self.save_file_name = save_file_name
        self.iter = iter

        os.makedirs(self.to_dir, exist_ok=True)

        self.data = load_json(self.test_dataset_file)
        self.submission_info = {item["submission1_id"]: item for item in self.data}
        self.results = []

    def _process_submission(self, info: dict) -> dict:
        submission_id = info["submission1_id"]
        buggy_code = info["code1"]
        status = info["code1_compile_status"]

        if status == "Compile Success":
            repaired = buggy_code
        else:
            chunker = Chunker(buggy_code, status)
            sub = chunker.get_chunk()
            prompts = []
            prompts.append(self.prompt_template.replace("<ERRORMSG></ERRORMSG>", ""))
            prompts.append(self.prompt_template.replace("<ERRORMSG></ERRORMSG>", "Error message will be provided to you, please refer to them selectively.\n[Error message]:\n<Error></Error>\n").replace("<Error></Error>", status))
            repair = Repair(self.model, API_KEY, API_URL)
            code_res = []
            for p in prompts:
                patched, _ = repair.post(p, submission_id)
                if patched:
                    full = chunker.reintegrate(patched)
                    code_res.append(full)

        result = info.copy()
        firstcode = f"iter{self.iter}_wo_msg"
        secondcode = f"iter{self.iter}_w_msg"
        result[firstcode] = code_res[0]
        result[secondcode] = code_res[1]
        return result

    def start(self):
        submission_list = self.submissions
        with ThreadPoolExecutor(max_workers=self.num_thread) as executor:
            futures = {executor.submit(self._process_submission, info): info for info in submission_list}
            for future in as_completed(futures):
                self.results.append(future.result())
        output_path = os.path.join(self.to_dir, self.save_file_name)
        tojson(self.results, output_path)

class Repair:
    def __init__(self, model_type, api_key, api_url, temperature=0.2):
        self.temperature = temperature
        self.model_type = model_type
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": self.api_key, 
            "User-Agent": "",
            "Content-Type": "application/json"}

    def post(self, prompt: str, submission_id: str):
        import requests, re
        payload = json.dumps({
            "model": self.model_type,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        })
        for attempt in range(5):
            try:
                r = requests.post(self.api_url, headers=self.headers, data=payload)
                if r.status_code == 200:
                    content = json.loads(r.text)["choices"][0]["message"]["content"]
                    if '```' in content:
                        parts = content.split('```')
                        code_block = parts[1]
                        lang_prefix = f" {self.language}" if f" {self.language}" in code_block else self.language
                        repaired_code = code_block.removeprefix(lang_prefix)
                    else:
                        repaired_code = ''
                    return repaired_code, content
            except Exception:
                time.sleep(1)
        return "", ""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RepairSyntaxError')
    parser.add_argument('--language', type=str, default='python', help='Language')
    parser.add_argument('--model', type=str, default='gpt-4o-ca', help='Model type')
    parser.add_argument("--test_dataset_file", type=str, default='./test.json', help='test dataset file')
    parser.add_argument("--to_dir", type=str, default='./baseline', help="Directory to save results")
    parser.add_argument("--prompt_template", type=str, default="""You are a skilled programmer experienced in debugging and providing optimal code fixes. Given a code snippet with syntax errors written in <LANGUAGE>, you are required to fix syntax errors in the code snippet, correct only the syntax errors and return only the corrected snippet—nothing else.
    <ERRORMSG></ERRORMSG>
[code snippet]: 
```python
<CODE_SNIPPET>
```
[Please answer in the following format]:
Repaired Code:
```python
```
""", help="prompt template")
    parser.add_argument("--save_file_name", type=str, default="result.json", help="The path to save data")
    parser.add_argument("--iter", default=1, help="iter")
    args = parser.parse_args()
    
    print(f"@@ iter: {args.iter} @@")
    print(f"@@ model: {args.model} @@")
    RepairManager(prompt_template=args.prompt_template, 
                  language=args.language, 
                  test_dataset_file=args.test_dataset_file, 
                  to_dir=args.to_dir, model=args.model, num_thread=10, 
                  save_file_name=args.save_file_name,
                  iter=args.iter).start()
