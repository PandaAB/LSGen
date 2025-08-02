from utils.jsonTools import load_json
import argparse
from tqdm import tqdm
from PSM.calc_metrics.calc_match_data_flow import corpus_dataflow_match
from PSM.calc_metrics.calc_match_ast import corpus_syntax_match
from PSM.calc_metrics.calc_match_bm25 import corpus_bm25_match
import numpy as np
import warnings
import json
from utils.utils import save_data_to_json
from multiprocessing import Pool, Manager, cpu_count
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("RetrievalRefCode/retrieval.log"),
        # logging.StreamHandler() # Displays on the console
    ]
)

warnings.filterwarnings("ignore")


def calc_match_test_case(data1, data2):
    try:
        if not isinstance(data1, dict) or not isinstance(data2, dict):
            raise TypeError("Input data1 and data2 must be dictionaries.")

        required_keys = ['code_test_status', 'submission1_id', 'submission2_id']
        flag = 0
        for key in required_keys:
            if key not in data1:
                if key == "code_test_status":
                    if "code1_test_status" not in data1:
                        raise KeyError(f"Missing key '{key}' in data1.")
                    else:
                        flag = 1
                else:
                    raise KeyError(f"Missing key '{key}' in data1.")
            if key not in data2:
                raise KeyError(f"Missing key '{key}' in data2.")

        if flag == 0:
            code_test_status1 = data1['code_test_status']
        else:
            code_test_status1 = data1['code1_test_status']
        code_test_status2 = data2['code_test_status']

        if not isinstance(code_test_status1, list) or not isinstance(code_test_status2, list):
            raise TypeError("code_test_status must be a list in both data1 and data2.")

        if not code_test_status1 or not code_test_status2:
            raise ValueError("code_test_status in data1 or data2 cannot be empty.")

        data1_case_num = len(code_test_status1)
        data2_case_num = len(code_test_status2)
        if data1_case_num!= data2_case_num:
            raise ValueError(
                "code1 and code2 have different number of test points, please check whether they are the same question!"
            )

        pass_1, pass_2, same = 0, 0, 0
        for k in range(data1_case_num):
            if code_test_status1[k] == 1 and code_test_status2[k] == 1:
                same += 1
            if code_test_status1[k] == 1:
                pass_1 += 1
            if code_test_status2[k] == 1:
                pass_2 += 1

        if pass_2 + pass_1 == 0:
            test_cases_score = 0
        else:
            test_cases_score = (same * 2) / (pass_2 + pass_1)

        return test_cases_score

    except TypeError as te:
        print(f"\033[31mTypeError: {te}\033[0m")
        return -1
    except KeyError as ke:
        print(f"\033[31mKeyError: {ke}\033[0m")
        return -1
    except ValueError as ve:
        print(f"\033[31mValueError: {ve}\033[0m")
        return -1
    except Exception as e:
        print(f"\033[31mUnexpected error: {e}\033[0m")
        return -1


def process_single_element(arg_tuple):
    each, data, language, w1, w2, w3, w4, k = arg_tuple
    PID = each["problem_id"]
    submission1_id = each["submission1_id"]
    user_id = each["user_id"]
    corpus = []
    MATCH_TESR_CASE = []
    MATCH_DATA_FLOW = []
    MATCH_AST_SCORE = []
    submission = []
    t = 0
    for ref in data:
        # if ref["problem_id"] == PID and ref["submission1_id"]!= submission1_id and ref["user_id"]!= user_id:
        if ref["problem_id"] == PID and ref["submission1_id"]!= submission1_id:
            MATCH_TESR_CASE.append(calc_match_test_case(each, ref))
            MATCH_DATA_FLOW.append(corpus_dataflow_match([[ref["code2"]]], [each["code1"]], language))
            MATCH_AST_SCORE.append(corpus_syntax_match([[ref["code2"]]], [each["code1"]], language))
            corpus.append(ref["code2"])
            submission.append(ref)

    RetrievalScore = None
    if len(corpus) > 0:
        if len(corpus) == 1:
            logging.info(f"Marked Case: PID = {PID}, submission1_id = {submission1_id} only one ref code.")
        MATCH_BM25_SCORE = corpus_bm25_match(corpus, each["code1"])
        if not (len(MATCH_TESR_CASE) == len(MATCH_DATA_FLOW) == len(MATCH_AST_SCORE) == len(MATCH_BM25_SCORE)):
            raise ValueError("All lists must have the same length.")

        RetrievalScore = [(a * w1 + b * w2 + c * w3 + d * w4) / (w1 + w2 + w3 + w4) for a, b, c, d in zip(MATCH_TESR_CASE, MATCH_DATA_FLOW, MATCH_AST_SCORE, MATCH_BM25_SCORE)]
        top_k_indices = np.argsort(RetrievalScore)[::-1][:k]

        top_k_results = []
        for index in top_k_indices:
            top_k_results.append({
                "MATCH_TESR_CASE": MATCH_TESR_CASE[index],
                "MATCH_DATA_FLOW": MATCH_DATA_FLOW[index],
                "MATCH_AST_SCORE": MATCH_AST_SCORE[index],
                "MATCH_BM25_SCORE": MATCH_BM25_SCORE[index],
                "RetrievalCode": submission[index]["code2"],
                "RetrievalScore": RetrievalScore[index], 
                "RetrievalSubmission1_id": submission[index]["submission1_id"]
            })

    else:
        logging.info(f"Marked Case: PID = {PID}, submission1_id = {submission1_id} no ref code.")
        top_k_results = []

    return {
        **each, 
        "top_k_results": top_k_results
    }


def calc_all_metrics(bug_code_data, retrieval_code_data, weight, language="python", k=3):
    manager = Manager()
    # data_dict = manager.dict()
    # lock = manager.Lock()
    a, b, c, d = [int(i) for i in weight]

    completed_tasks = 0
    total_tasks = len(bug_code_data)
    with tqdm(total=total_tasks, desc="Processing submissions", unit="submission", colour="yellow") as pbar:
        def update_progress(_):
            nonlocal completed_tasks
            completed_tasks += 1
            pbar.update(1)

        with Pool(processes=cpu_count()) as pool:
            results = []
            args_list = [(each, retrieval_code_data, language, a, b, c, d, k) for each in bug_code_data]
            for arg in args_list:
                result = pool.apply_async(process_single_element, (arg,), callback=update_progress)
                results.append(result)

            all_processed_data = []
            for result in results:
                try:
                    processed_data = result.get()
                    all_processed_data.append(processed_data)
                except Exception as e:
                    print(f"Exception occurred in a process: {e}")

    return all_processed_data


def parse_args():
    parser = argparse.ArgumentParser(description="Calculates four metrics for retrieving reference code")
    parser.add_argument('--bug_code_file', required=True, help='Path to the JSON file with data.')
    parser.add_argument('--retrieval_code_file', required=True, help='Path to the JSON file with data.')
    parser.add_argument('--output_file', required=True, help='Path to save the output JSON file.')
    parser.add_argument('--language', default="python", required=True, help='This specifies the programming language to filter the submissions.')
    parser.add_argument('--weight', default="1011", required=True, help="The binary form of the indicator needs to be calculated.")
    parser.add_argument('--top_k', type=int, default=3, help='Number of top results to retrieve')
    return parser.parse_args()


if __name__ == '__main__':
    start_time = time.time()
    args = parse_args()
    bug_code_data = load_json(args.bug_code_file)
    retrieval_code_data = load_json(args.retrieval_code_file)
    final_data = calc_all_metrics(bug_code_data=bug_code_data, retrieval_code_data=retrieval_code_data, weight=args.weight, language=args.language, k=args.top_k)
    save_data_to_json(final_data, args.output_file)
    print(">>> Code successfully retrieved!")
    print(f"Total time taken: {time.time() - start_time} seconds")