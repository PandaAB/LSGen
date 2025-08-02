import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from utils.jsonTools import tojson
import re
import tqdm

API_KEY = ""  
API_URL = ""

class DescManager:
    def __init__(self, prompt_template: str, language: str,
                 test_dataset_file: str, problem_description_file: str, to_dir: str, save_file_name: str, retrieval_desc_dataset: str,
                 num_workers: int = 10, model='gpt-4o', retrieval_data_file: str = "", temperature = 0.2) -> None:
        self.prompt_template = prompt_template
        self.language = language
        self.to_dir = to_dir
        self.num_workers = num_workers
        self.model = model
        self.retrieval_data_file = retrieval_data_file
        self.save_file_name = save_file_name
        self.temperature = temperature
        self.retrieval_desc_dataset = retrieval_desc_dataset
        if not os.path.exists(self.to_dir):
            os.makedirs(self.to_dir)

        # Load data
        with open(problem_description_file, 'r', encoding='utf-8') as f:
            problem_info = json.load(f)
        with open(test_dataset_file, 'r', encoding='utf-8') as f:
            submission_info = json.load(f)
        with open(retrieval_data_file, 'r', encoding='utf-8') as f:
            self.retrieval_data = json.load(f)
        with open(retrieval_desc_dataset, 'r', encoding='utf-8') as f:
            self.retrieval_desc_data = json.load(f)
        

        self.problem_description = {item['Pid']: item['ProblemText'] for item in problem_info}
        self.submission_info = {item['submission1_id']: item for item in submission_info}
        self.results = []
        self.processed_ids = []

    def get_code_from_retrieval(self, submission_id: str):
        for entry in self.retrieval_data:
            if entry['submission1_id'] == submission_id:
                return entry['code1'], entry['code2']
        return "", ""

    def structure_prompt(self, sub_id, desc, mode="2"):
        if mode == "1":
            buggy_code, correct_code = self.submission_info[sub_id]["code1"], self.submission_info[sub_id]["code2"]
        else:
            buggy_code, correct_code = self.get_code_from_retrieval(sub_id)
        if not buggy_code or not correct_code:
            print(f"\033[31m### Warning: No code found for {sub_id}, skipping.\033[0m")
            return ""
        return (self.prompt_template
                .replace('<LANGUAGE>', self.language)
                .replace('<TASK_DESCRIPTION>', desc)
                .replace('<BUGGY_CODE>', buggy_code)
                .replace('<CORRECT_CODE>', correct_code))

    def start(self):
        submission_list = list(self.submission_info.keys())
        desc_client = Description(self.language, API_KEY, API_URL, temperature=self.temperature, model_type=self.model)

        try:
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                future_to_id = {}
                for sub_id in submission_list:
                    future = executor.submit(self.process_single, sub_id, desc_client)
                    future_to_id[future] = sub_id

                for future in tqdm.tqdm(as_completed(future_to_id), total= len(submission_list), colour="yellow", desc="Processing submissions"):
                    sub_id = future_to_id[future]
                    try:
                        result = future.result()
                        if result:
                            self.results.append(result)
                            self.processed_ids.append(sub_id)
                    except Exception as e:
                        print(f"Error processing {sub_id}: {e}")
        except KeyboardInterrupt:
            print(f"KeyboardInterrupt at submission {self.processed_ids[-1] if self.processed_ids else 'N/A'}")
            # Save processed and unprocessed IDs
            import datetime
            timestamp = datetime.datetime.now().strftime("%m%d%H%M%S")
            temp_results = os.path.join(self.to_dir, f"{timestamp}_temp.json")
            temp_unprocessed = os.path.join(self.to_dir, "unprocessed_ids.json")

            tojson(self.results, temp_results)
            unprocessed = [sid for sid in submission_list if sid not in self.processed_ids]
            with open(temp_unprocessed, 'w', encoding='utf-8') as uf:
                json.dump(unprocessed, uf, ensure_ascii=False, indent=2)
            print(f">>> Saved processed results to {temp_results} and unprocessed IDs to {temp_unprocessed}")

        # Final save
        tojson(self.results, os.path.join(self.to_dir, self.save_file_name))
        with open(self.retrieval_desc_dataset, 'w', encoding='utf-8') as f:
            json.dump(self.retrieval_desc_data, f, indent=4, ensure_ascii=False)
        print(f">>> The retrieved data has been updated! The number is {len(self.retrieval_desc_data)}.")

    def process_single(self, submission_id, desc_client):
        # Build main prompt and get description
        prob = self.submission_info[submission_id]
        problem_id = prob['problem_id']
        description_text = self.problem_description[problem_id]
        # prompt_main = self.structure_prompt(submission_id, description_text, mode="1")
        # if not prompt_main:
        #     return None
        # main_desc, main_content = desc_client.post_with_retries(prompt_main, submission_id)

        # Build retrieval descriptions
        top_k = prob['top_k_results']
        retrieval_list = []
        for item in top_k:
            rid = item['RetrievalSubmission1_id']
            if rid in self.retrieval_desc_data:
                retrieval_list.append({
                're_submission_id': rid,
                'bug_description': self.retrieval_desc_data[rid][0],
                'origin_generated_text': self.retrieval_desc_data[rid][1]
            })
            else:
                prompt_ret = self.structure_prompt(rid, description_text, mode="2")
                if not prompt_ret:
                    print(">>> No Prompt!")
                    continue
                desc_ret, content_ret = desc_client.post_with_retries(prompt_ret, rid)
                retrieval_list.append({
                    're_submission_id': rid,
                    'bug_description': desc_ret,
                    'origin_generated_text': content_ret
                })
                if rid not in self.retrieval_desc_data:
                    self.retrieval_desc_data[rid] = [desc_ret, content_ret]

        result = {
            **prob,
            'retrieval_code_bug_desc': retrieval_list
        }
        return result

class Description:
    def __init__(self, language, api_key, api_url,temperature,
                 model_type='gpt-4o', error_log_path='./error.log', max_retries=5):
        self.language = language
        self.api_key = api_key
        self.api_url = api_url
        self.model_type = model_type
        self.error_log_path = error_log_path
        self.max_retries = max_retries
        self.temperature = temperature
        self.headers = {
            'Authorization': self.api_key,
            'User-Agent': '',
            'Content-Type': 'application/json'
        }

    def post_with_retries(self, prompt: str, submission_id: str):
        import requests
        for attempt in range(1, self.max_retries + 1):
            try:
                payload = json.dumps({
                    'model': self.model_type,
                    'messages': [
                        {'role': 'user', 
                         'content': prompt}
                        ],
                    "temperature": self.temperature,
                })
                response = requests.request("POST", self.api_url, headers=self.headers, data=payload)
                if response.status_code == 200:
                    content = json.loads(response.text).get("choices")[0]["message"]["content"]
                    # parse description
                    gen_descriptions = re.findall(r'<EXPLANATION>(.*?)</EXPLANATION>', content, re.DOTALL)
                    bug_desc = "\n".join([f"{i+1}. {desc.strip()}" for i, desc in enumerate(gen_descriptions)])
                    # start = content.find('Bug Description:')
                    # bug_desc = content[start:].split('\n', 1)[1].strip() if start != -1 else ''
                    return bug_desc, content
                else:
                    print(f"Attempt {attempt} failed for {submission_id}: Status {response.status_code}")
            except Exception as e:
                print(f"Attempt {attempt} exception for {submission_id}: {e}")
                # log exception
                with open(self.error_log_path, 'a', encoding='utf-8') as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {submission_id} | Attempt {attempt} | {e}\n")
        return '', 'Request failed after retries'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Desc')
    parser.add_argument('--language', type=str, default='python')
    parser.add_argument('--model', type=str, default='gpt-4o-ca')
    parser.add_argument("--problem_description_file", type=str, default='./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json', help="Problem description file")
    parser.add_argument('--test_dataset_file', type=str, default='./test.json')
    parser.add_argument('--to_dir', type=str, default='./baseline')
    parser.add_argument("--prompt_template", type=str, default="""You are an experienced programmer with a strong ability to analyze and debug code. You will be given a programming problem and a pair of <LANGUAGE> code snippets in the format <buggy code, correct code>. Your task is to generate point-by-point bug explanations for the buggy code based on the correct code.
All bug explanations should be wrapped in <EXPLANATIONS_LIST></EXPLANATIONS_LIST> tags. Each bug explanation should be wrapped with <EXPLANATION></EXPLANATION> tags.
[Programming Problem]
<TASK_DESCRIPTION>
[Buggy Code]
<BUGGY_CODE>
[Correct Code]
<CORRECT_CODE>
Please answer in the following format:
Bug Explanations:
<EXPLANATIONS_LIST></EXPLANATIONS_LIST>
""", help="prompt template")
    parser.add_argument('--retrieval_data_file', type=str, default='./retrieval_data.json')
    parser.add_argument('--retrieval_desc_dataset', type=str, default='./data/ALL/RetrievalDataSet/RetrievalData_Descriptions.json')
    parser.add_argument('--save_file_name', type=str, default='result.json')
    args = parser.parse_args()

    DescManager(
        prompt_template=args.prompt_template,
        language=args.language,
        test_dataset_file=args.test_dataset_file,
        problem_description_file=args.problem_description_file,
        to_dir=args.to_dir,
        save_file_name=args.save_file_name,
        num_workers=10,
        model=args.model,
        retrieval_data_file=args.retrieval_data_file,
        retrieval_desc_dataset=args.retrieval_desc_dataset
    ).start()
