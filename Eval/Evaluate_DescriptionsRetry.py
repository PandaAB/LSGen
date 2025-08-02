import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from utils.jsonTools import tojson
import tqdm

API_KEY = ""
API_URL = ""

class EvalManager:
    def __init__(
        self,
        prompt_template: str,
        input_file: str,
        output_dir: str,
        output_file: str,
        problem_description_file: str,
        model: str = "gpt-4o-mini-ca",
        num_threads: int = 10,
    ):
        self.prompt_template = prompt_template
        self.input_file = input_file
        self.output_dir = output_dir
        self.output_file = output_file
        self.api_key = API_KEY
        self.api_url = API_URL
        self.model = model
        self.num_threads = num_threads
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        os.makedirs(self.output_dir, exist_ok=True)

        with open(problem_description_file, "r", encoding="utf-8") as f:
            problem_info = json.load(f)
        self.problem_description = {item["Pid"]: item["ProblemText"] for item in problem_info}

        with open(self.input_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def extract_original(self, text: str):
        # parts = re.split(r"\d+\.\s*", text)
        # return [p.strip() for p in parts if p.strip()]
        parts = text.split("\n")
        return [p.strip() for p in parts if p.strip()]

    def extract_generated(self, text: str):
        return [match.strip() for match in re.findall(r"<DESCRIPTION>(.*?)</DESCRIPTION>", text, re.S)]

    def compare_pair(self, orig: str, gen: str, prompt_template: str):
        prompt = (
            prompt_template
            .replace("<DESCRIPTION_A>", orig)
            .replace("<DESCRIPTION_B>", gen)
        )
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        })

        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.request("POST", self.api_url, headers=self.headers, data=payload)
                if response.status_code == 200:
                    content = json.loads(response.text).get("choices")[0]["message"]["content"]
                    if content.upper() in ["YES", "NO"]:
                        return content.upper()
                    else:
                        print(f">>> Attempt {attempt}: Unexpected format: {content}")
                else:
                    print(f">>> Error {response.status_code} on attempt {attempt}: {response.text}")
            except Exception as e:
                print(f">>> Exception on attempt {attempt}: {e}")
            time.sleep(1)
        return "NO"

    def process_item(self, item: dict) -> dict:
        orig_list = self.extract_original(item["code1_bug_descriptions"])
        gen_list = self.extract_generated(item["gen_code1_bug_descriptions"])
        problem_id = item["problem_id"]

        problem_desc = self.problem_description[problem_id]
        buggy_code = item["code1"]

        prompt = (
            self.prompt_template
            .replace("<TASK_DESCRIPTION>", problem_desc)
            .replace("<BUGGY_CODE>", buggy_code)
        )

        matrix = []
        for orig in orig_list:
            row = []
            for gen in gen_list:
                ans = self.compare_pair(orig, gen, prompt)
                row.append(ans)
            matrix.append(row)
        item["GPT_Eval"] = matrix
        return item

    def start(self):
        all_indices = list(range(len(self.data)))
        evaluated = []
        processed_indices = []

        for attempt in range(2):  # allow one retry
            try:
                with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                    future_to_idx = {executor.submit(self.process_item, self.data[idx]): idx for idx in all_indices}
                    for future in tqdm.tqdm(as_completed(future_to_idx), total=len(all_indices), colour="blue", desc="Processing submissions"):
                        idx = future_to_idx[future]
                        processed_indices.append(idx)
                        try:
                            evaluated.append(future.result())
                        except Exception as e:
                            print(f"Processing error at index {idx}: {e}")
                break
            except KeyboardInterrupt:
                print(f"KeyboardInterrupt at index {idx}")
                timestamp = time.strftime("%m%d%H%M%S")
                temp_path = os.path.join(self.output_dir, f"{timestamp}_temp.json")
                tojson(evaluated, temp_path)
                unprocessed = [i for i in all_indices if i not in processed_indices]
                if attempt == 0 and unprocessed:
                    print("Retrying unprocessed items...")
                    all_indices = unprocessed
                    continue
                else:
                    print("No more retries or nothing to retry. Exiting.")
                    break

        # final save
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        output_path = os.path.join(self.output_dir, self.output_file)
        tojson(evaluated, output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate similarity between original and generated bug descriptions')
    parser.add_argument("--problem_description_file", type=str, default='./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json', help="Problem description file")
    parser.add_argument('--input_file', type=str, required=True, help='Path to input JSON file')
    parser.add_argument('--output_dir', type=str, default='./output', help='Directory to save results')
    parser.add_argument('--output_file', type=str, default='./output', help='The file path to save.')
    parser.add_argument('--model', type=str, default='gpt-4o-mini-ca', help='Model name')
    parser.add_argument('--num_threads', type=int, default=10, help='Number of threads for concurrency')
    parser.add_argument("--prompt_template", type=str, default="""You are a skilled programmer experienced in debugging and providing optimal code fixes.
    You will be given:
    1. A description of programming problem.
    2. A piece of buggy code written in python.
    3. Two bug descriptions of the buggy code, namely Description A and Description B.
    Your task is to determine whether these two bug descriptions describe the same bug of this buggy code.
    Instructions:
    1. Read the problem statement and the provided buggy code.
    2. Read Bug Description A and Bug Description B of the bug.
    3. Ignore any suggested fixes — focus solely on whether the two descriptions identify the same bug.
    4. If they describe the same bug, respond with 'Yes', otherwise respond with 'No'. Please only answer "YES" or "NO", and do not answer anything else.
    
Programming Problem: <TASK_DESCRIPTION>
Buggy Code: <BUGGY_CODE>
Bug Description A: <DESCRIPTION_A>
Bug Description B: <DESCRIPTION_B>
""", help="prompt template")
    args = parser.parse_args()

    manager = EvalManager(
        prompt_template=args.prompt_template,
        input_file=args.input_file,
        output_dir=args.output_dir,
        output_file=args.output_file,
        model=args.model,
        num_threads=args.num_threads,
        problem_description_file=args.problem_description_file
    )
    manager.start()
