import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm
from utils.jsonTools import tojson, load_json
import re
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
        use_ref,
        num_thread: int = 10,
        topk = 5,
        model="gpt-4o-ca",
        retrieval_dataset=""
    ) -> None:
        self.prompt_template = prompt_template
        self.language = language
        self.to_dir = to_dir
        self.num_thread = num_thread
        self.model = model
        self.save_file_name = save_file_name
        self.topk = int(topk)
        self.use_ref = use_ref
        self.retrieval_dataset = retrieval_dataset

        os.makedirs(self.to_dir, exist_ok=True)
        self.retrieval_data = load_json(self.retrieval_dataset)
        self.retrieval_data_dict = {each["submission1_id"]: each for each in self.retrieval_data}

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
            self.prompt_template
            .replace("<TASK_DESCRIPTION>", description)
            .replace("<BUGGY_CODE>", buggy_code)
            .replace("<MODIFIED_CODE>", info.get("code_content", ""))
        )
        if self.use_ref:
            refs = info.get('top_k_results', [])
            all_refs = []
            for r in refs:
                ref_desc = r.get('bug_description', '') 
                ref_sub = r["RetrievalSubmission1_id"]
                ref_code1 = self.retrieval_data_dict[ref_sub]["code1"]
                ref_code2 = self.retrieval_data_dict[ref_sub]["code2"]
                all_refs.append(f"Buggy Code: {ref_code1}\nCorrect Code: {ref_code2}\n Bug Explanations: {ref_desc}")
            ref_text = "\n".join(all_refs[:self.topk])
            prompt = prompt.replace("<REFERENCES>", ref_text)

        repair = Repair(self.language, API_KEY, API_URL, model_type=self.model)
        gen_bug_desc, full_content = repair.post(prompt, submission_id)

        res = {
            **info,
            "gen_code1_bug_descriptions": gen_bug_desc,
            "desc_ori_content": full_content,
        }
        return res

    def start(self):
        all_ids = list(self.submission_info.keys())
        processed_ids = []

        for attempt in range(5):
            current_id = None
            try:
                with ThreadPoolExecutor(max_workers=self.num_thread) as executor:
                    futures = {executor.submit(self._process_submission, sid): sid for sid in all_ids}
                    for fut in tqdm.tqdm(as_completed(futures), total=len(all_ids), colour="green", desc="Processing submissions"):
                        current_id = futures[fut]
                        res = fut.result()
                        self.results.append(res)
                        processed_ids.append(current_id)
                break

            except KeyboardInterrupt:
                print(f"KeyboardInterrupt at submission {current_id}")
                ts = time.strftime("%m%d%H%M%S")
                tmp_file = os.path.join(self.to_dir, f"{ts}_temp.json")
                tojson(self.results, tmp_file)
                unprocessed = [sid for sid in all_ids if sid not in processed_ids]
                with open(os.path.join(self.to_dir, "unprocessed_ids.json"), "w", encoding="utf-8") as uf:
                    json.dump(unprocessed, uf, ensure_ascii=False, indent=2)
                if attempt != 4 and unprocessed:
                    print(">>> Retrying unprocessed submissions...")
                    all_ids = unprocessed
                    continue
                else:
                    print(">>> No more retries or nothing to retry. Exiting.")
                    break

        out_path = os.path.join(self.to_dir, self.save_file_name)
        tojson(self.results, out_path)

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
                    match = re.search(r'<DESCRIPTIONS_LIST>.*?</DESCRIPTIONS_LIST>', content, re.DOTALL)
                    bug_desc = match.group(0) if match else ""
                    if bug_desc:
                        return bug_desc, content
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
    parser.add_argument("--prompt_template", type=str, default="""You are an experienced programmer with a strong ability to analyze and debug code. You will be provided with a programming problem along with two files: one containing the buggy code, and one containing the modified code. Your task is to analyze both files and describe the bugs point by point. Any changes that are merely optimization suggestions and do not affect correctness should be ignored. Please wrap all bug descriptions in <DESCRIPTIONS_LIST></DESCRIPTIONS_LIST> tags.  Each individual bug description should be enclosed in <DESCRIPTION></DESCRIPTION> tags. 
    Some examples will be provided to you.
[Examples]: <REFERENCES>
[Programming Problem]:
<TASK_DESCRIPTION>
[File 1 (Buggy Code)]:
<BUGGY_CODE>
[File 2 (Modified Code)]:
<MODIFIED_CODE>
[Please answer in the following format]:
Bug Descriptions:
<DESCRIPTIONS_LIST></DESCRIPTIONS_LIST>""", help="prompt template")
    parser.add_argument("--save_file_name", type=str, default="result.json")
    parser.add_argument("--topk", type=int, default=5)
    parser.add_argument("--use_ref", action="store_true")
    parser.add_argument('--retrieval_dataset', type=str, default='./dataset/Filtered_pair/code1_Added_testScode_pairs/Exec_test_processed_pair.json')
    args = parser.parse_args()

    print(f"@@ TopK: {args.topk} @@")
    print(f"@@ Use Ref: {args.use_ref} @@")

    RepairManager(
        prompt_template=args.prompt_template,
        language=args.language,
        test_dataset_file=args.test_dataset_file,
        problem_description_file=args.problem_description_file,
        to_dir=args.to_dir,
        save_file_name=args.save_file_name,
        use_ref=args.use_ref,
        topk=args.topk,
        model=args.model,
        retrieval_dataset=args.retrieval_dataset
    ).start()
