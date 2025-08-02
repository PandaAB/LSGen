from utils.jsonTools import load_json
from trl.data_utils import maybe_apply_chat_template, apply_chat_template
from transformers import AutoTokenizer
import os
import re
import json

def load_problem(problem_description_file):
    with open(problem_description_file, "r", encoding="utf-8") as f:
            problem_info = json.load(f)
    problem_description = {item["Pid"]: item["ProblemText"] for item in problem_info}
    return problem_description

def load_retrieval_data(retrieval_data_file):
    if not os.path.exists(retrieval_data_file):
        raise FileNotFoundError(f"Retrieval data file {retrieval_data_file} does not exist.")
    retrieval_data = load_json(retrieval_data_file)
    retrieval_data_dict = {item["submission1_id"]: item for item in retrieval_data}
    return retrieval_data_dict

def make_conversation(example, system_prompt):
    prompt = []
    if system_prompt is not None:
        prompt.append({"role": "system", "content": system_prompt})
    prompt.append({"role": "user", "content": example["prompt"]})
    return {"prompt": prompt}

def load_eval_dataset(system_prompt, data_dir_path, language, model_path, max_input_tokens, prompt_mode, without_context = False, topk = 5, retrieval_data_file = None):
    problem_description = load_problem("./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json")
    retrieval_data_dict = load_retrieval_data(retrieval_data_file) if retrieval_data_file else None
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    data_list = []
    # Load the dataset
    ori_data_list = load_json(data_dir_path)
    data_num = len(data_list)
    for idx, data in enumerate(ori_data_list):
        temp_data = {}
        temp_prompt = construct_model_prompt(data, language, tokenizer, max_input_tokens, system_prompt, without_context,prompt_mode, problem_description, topk, retrieval_data_dict)
        exceed_token_nums = len(tokenizer.encode(temp_prompt)) - max_input_tokens
        if exceed_token_nums > 0:
            temp_prompt_lines = temp_prompt.split("\n")
            extra_token_num = exceed_token_nums
            # drop lines from end until the extra token number is less than 0
            for i in range(len(temp_prompt_lines)-1, -1, -1):
                extra_token_num -= len(tokenizer.encode(temp_prompt_lines[i]))
                if extra_token_num < 0:
                    break
            # join the lines back
            cutting_prompt = "\n".join(temp_prompt_lines[:i]) + "\n\n"
        else:
            cutting_prompt = temp_prompt
        temp_data['prompt'] = cutting_prompt
        temp_data['id'] = idx + data_num
        temp_data['submission1_id'] = data["submission1_id"]
        data_list.append(temp_data)
    print("the number of data_list:", len(data_list))
    #input()
    return data_list

def construct_model_prompt(data, language, tokenizer = None, max_input_tokens = None, system_prompt = "", without_context = False,prompt_mode = "TextRef", problem_description = None, topk = 5, retrieval_data_dict = None):
    """
        ```maybe_apply_chat_template
        >>> from transformers import AutoTokenizer
        >>> tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-128k-instruct")
        >>> example = {
        ...     "prompt": [{"role": "user", "content": "What color is the sky?"}],
        ...     "completion": [{"role": "assistant", "content": "It is blue."}]
        ... }
        >>> apply_chat_template(example, tokenizer)
        {'prompt': '<|user|>\nWhat color is the sky?<|end|>\n<|assistant|>\n', 'completion': 'It is blue.<|end|>\n<|endoftext|>'}
        ```
    """
    example = {}
    # OurMethod
    if prompt_mode == "TextRef":
        example['prompt'] = construct_TextRef_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk)
        system_prompt = system_prompt.replace("<task></task>", "Reference bug descriptions and corresponding fix suggestions will be provided to you, please refer to them selectively.")
    elif prompt_mode =="TextRefDiff":
        example['prompt'] = construct_TextRefDiff_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict)
        system_prompt = system_prompt.replace("<task></task>", "Reference bug descriptions, suggested fixes, and the code diffs highlighting corrections will be provided for you to consult selectively.")
    elif prompt_mode =="CommentTextRefDiff":
        example['prompt'] = construct_CommentTextRefDiff_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict)
        system_prompt = system_prompt.replace("<task></task>", "You will receive one or more diff files. In these files, '-' marks lines deleted from the buggy code, and '+' marks lines added in the correct code, refer to them selectively.")
        # u will receive one or more diff files, each annotated with comments that describe each bug and its corresponding fix suggestion. Please review these descriptions before examining the related code changes, refer to them selectively.
    elif prompt_mode == "DiffRef":
        example['prompt'] = construct_DiffRef_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict)
        system_prompt = system_prompt.replace("<task></task>", "You will receive one or more diff files. In these files, '-' marks lines deleted from the buggy code, and '+' marks lines added in the correct code, refer to them selectively.")
    # NoRef
    elif prompt_mode == "NoRef":
        problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
        example['prompt'] = f"""{problem_prompt}\n{buggy_code_prompt}"""
        system_prompt = system_prompt.replace("<task></task>", "")
    # CoT:
    elif prompt_mode == "CoT":
        problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
        example['prompt'] = f"""{problem_prompt}\n{buggy_code_prompt}"""
        system_prompt = system_prompt.replace("<task></task>", "Let’s think step by step.")
    # CodeRef
    elif prompt_mode == "CodeRef":
        example['prompt'] = construct_CodeRef_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict)
        system_prompt = system_prompt.replace("<task></task>", "Reference codes will be provided to you, please refer to them selectively.")
        # "Reference buggy code and corresponding correct code will be provided to you, please refer to them selectively."
    # AdaPatcher
    elif prompt_mode == "AdaPatcherFirst":
        problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
        example['prompt'] = f"""{problem_prompt}\n{buggy_code_prompt}"""
    elif prompt_mode == "AdaPatcherSecond":
        example['prompt'] = construct_AdaPatcherSecond_prompt(data, language, tokenizer, max_input_tokens, problem_description)
        system_prompt = system_prompt.replace("<task></task>", "You will be provided with a file containing bug location markers; any line starting with “-” denotes a buggy line.")
    # PAR
    elif prompt_mode == "PAR":
        example['prompt'] = construct_PAR_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict)
        system_prompt = system_prompt.replace("<task></task>", "Reference correct code will be provided to you, please refer to them selectively.")
    # PyDex
    elif prompt_mode == "PyDex":
        # PyDex Use Same Prompt Template
        example['prompt'] = construct_CodeRef_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict)
        system_prompt = system_prompt.replace("<task></task>", "Reference buggy code and corresponding correct code will be provided to you, please refer to them selectively.")
    # PyFiXV
    elif prompt_mode == "PyFiXVFirst":
        problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
        example['prompt'] = f"""{problem_prompt}\n{buggy_code_prompt}"""
    elif prompt_mode == "PyFiXVSecond":
        example['prompt'] = construct_PyFiXVSecond_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict)
   
    example = make_conversation(example, system_prompt) #constrcut conversation based on input
    model_prompt = maybe_apply_chat_template(example, tokenizer)["prompt"]  # construct input of model
    return model_prompt

def construct_TextRef_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk):
    problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
    retrieval_code_bug_desc = data["retrieval_code_bug_desc"]
    all_references = [entry['bug_description'] for entry in retrieval_code_bug_desc]
    bug_description = "\n".join(all_references[:topk])
    reference_prompt = f"""[Reference bug descriptions and corresponding fix suggestions]:\n{bug_description}\n"""

    model_prompt = f"""{problem_prompt}\n{buggy_code_prompt}\n{reference_prompt}"""
    return model_prompt

def construct_TextRefDiff_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict):
    problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
    retrieval_code_bug_desc = data["retrieval_code_bug_desc"]
    all_references = []
    for entry in retrieval_code_bug_desc:
        retrieval_diff = retrieval_data_dict[entry["re_submission_id"]]["diff_code"]
        single_ref = f"Diff Code:\n{retrieval_diff}\n Reference Bug Descriptions, Corresponding Fixes: {entry['bug_description']}"
        all_references.append(single_ref)
    
    bug_description = "\n".join(all_references[:topk])
    reference_prompt = f"""[Reference Bug Descriptions, Corresponding Fixes and Diff Code]: \n{bug_description}\n"""

    model_prompt = f"""{problem_prompt}\n{buggy_code_prompt}\n{reference_prompt}"""
    return model_prompt

def construct_CommentTextRefDiff_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict):
    problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
    retrieval_code_bug_desc = data["retrieval_code_bug_desc"]
    all_references = []
    for entry in retrieval_code_bug_desc:
        retrieval_diff = retrieval_data_dict[entry["re_submission_id"]]["diff_code"]
        eb = entry['bug_description'].split("\n")
        eb1 = ["# Each bug and its corresponding fix suggestion: "]
        for e in eb:
            eb1.append("# " + e)
        comment_desc = "\n".join(eb1)
        single_ref = f"Diff Code:\n{comment_desc}\n{retrieval_diff}"
        all_references.append(single_ref)
    
    bug_description = "\n".join(all_references[:topk])
    reference_prompt = f"""[Reference Diff Files]: \n{bug_description}\n"""

    model_prompt = f"""{problem_prompt}\n{buggy_code_prompt}\n{reference_prompt}"""
    return model_prompt

def construct_DiffRef_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict):
    problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
    retrieval_code_bug_desc = data["retrieval_code_bug_desc"]
    all_references = []
    for entry in retrieval_code_bug_desc:
        retrieval_diff = retrieval_data_dict[entry["re_submission_id"]]["diff_code"]
        single_ref = f"Diff Code:\n{retrieval_diff}"
        all_references.append(single_ref)
    
    ref_prompt = "\n".join(all_references[:topk])
    reference_prompt = f"""[Reference Diff Codes]: \n{ref_prompt}\n"""

    model_prompt = f"""{problem_prompt}\n{buggy_code_prompt}\n{reference_prompt}"""
    return model_prompt

def construct_CodeRef_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict):
    problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
    top_k_results = data["top_k_results"]
    all_references = []
    for entry in top_k_results:
        retrieval_code1 = retrieval_data_dict[entry['RetrievalSubmission1_id']]["code1"]
        retrieval_code2 = retrieval_data_dict[entry['RetrievalSubmission1_id']]["code2"]
        all_references.append((retrieval_code1, retrieval_code2))
    all_references_code = []
    for each in all_references:
        t = f"Buggy Code:\n{each[0]}\nCorrect Code:\n{each[1]}"
        all_references_code.append(t)
    references_code = "\n".join(all_references_code[:topk])
    reference_prompt = f"""[Reference buggy code and corresponding correct code]:\n{references_code}\n"""

    model_prompt = f"""{problem_prompt}\n{buggy_code_prompt}\n{reference_prompt}"""
    return model_prompt

def construct_AdaPatcherSecond_prompt(data, language, tokenizer, max_input_tokens, problem_description):
    problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
    bug_locations = data["bug_locations"]
    location_prompt = f"[Bug Location]: {bug_locations}"
    model_prompt = f"""{problem_prompt}\n{buggy_code_prompt}\n{location_prompt}"""
    return model_prompt

def construct_PAR_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict=None):
    problem_prompt, buggy_code_prompt = construct_common_prompt(data, language, problem_description)
    top_k_results = data["top_k_results"]
    all_references = [retrieval_data_dict[entry['RetrievalSubmission1_id']]["code2"] for entry in top_k_results]
    reference_code = "\n".join(all_references[:topk])
    reference_prompt = f"""[reference correct code]:\n{reference_code}\n"""
    model_prompt = f"""{problem_prompt}\n{buggy_code_prompt}\n{reference_prompt}"""
    return model_prompt


def construct_common_prompt(data, language, problem_description):
    buggy_code = data["code1"]
    task_description = problem_description[data["problem_id"]]
    problem_prompt = f"""[programming problem]:\n{task_description}\n"""
    buggy_code_prompt = f"""[buggy code]:\n```{language}\n{buggy_code}\n```\n"""
    return problem_prompt, buggy_code_prompt

def construct_PyFiXVSecond_prompt(data, language, tokenizer, max_input_tokens, problem_description, topk, retrieval_data_dict):
    buggy_code = data["code1"]
    code_content = data["code_content"]
    task_description = problem_description[data["problem_id"]]
    problem_prompt = f"""[programming problem]:\n{task_description}\n"""
    buggy_code_prompt = f"""[File 1 (Buggy Code)]:\n```{language}\n{buggy_code}\n```\n"""
    code_content_prompt = f"""[File 2 (Modified Code)]:\n```{language}\n{code_content}\n```\n"""

    retrieval_code_bug_desc = data["retrieval_code_bug_desc"]
    all_references = []
    for entry in retrieval_code_bug_desc:
        retrieval_code1 = retrieval_data_dict[entry['re_submission_id']]["code1"]
        retrieval_code2 = retrieval_data_dict[entry['re_submission_id']]["code2"]
        all_references.append((retrieval_code1, retrieval_code2, entry["bug_description"]))
    all_references_code = []
    for each in all_references:
        t = f"Buggy Code:\n{each[0]}\nCorrect Code:\n{each[1]}\nBug Explanations:{each[2]}"
        all_references_code.append(t)
    references_code = "\n".join(all_references_code[:topk])
    reference_prompt = f"""[Examples]:\n{references_code}\n"""

    model_prompt = f"""{reference_prompt}\n{problem_prompt}\n{buggy_code_prompt}\n{code_content_prompt}"""
    return model_prompt

def extract_result(result_data, language):
    res = []
    for each in result_data:
        td = {}
        content = each["generated_text"]
        match = re.search(r'<DESCRIPTIONS_LIST>.*?</DESCRIPTIONS_LIST>', content, re.DOTALL)
        bug_description = match.group(0) if match else ""
        if '```' in content:
            parts = content.split('```')
            code_block = parts[1]
            lang_prefix = f" {language}" if f" {language}" in code_block else language
            repaired_code = code_block.removeprefix(lang_prefix)
        else:
            repaired_code = ""
        if bug_description == "":
            bug_description = wrap_bug_descriptions(content)
        td["code_content"] = repaired_code.strip()
        td["gen_code1_bug_descriptions"] = bug_description.strip()
        td["submission1_id"] = each["submission1_id"]
        res.append(td)
    return res

def extract_code_result(result_data, language):
    res = []
    for each in result_data:
        td = {}
        content = each["generated_text"]
        if '```' in content:
            parts = content.split('```')
            code_block = parts[1]
            lang_prefix = f" {language}" if f" {language}" in code_block else language
            repaired_code = code_block.removeprefix(lang_prefix)
        else:
            repaired_code = ""
        td["code_content"] = repaired_code.strip()
        td["submission1_id"] = each["submission1_id"]
        res.append(td)
    return res

def extract_desc_result(result_data, language):
    res = []
    for each in result_data:
        td = {}
        content = each["generated_text"]
        match = re.search(r'<DESCRIPTIONS_LIST>.*?</DESCRIPTIONS_LIST>', content, re.DOTALL)
        bug_description = match.group(0) if match else ""
        if bug_description == "":
            bug_description = wrap_bug_descriptions(content)
        td["gen_code1_bug_descriptions"] = bug_description.strip()
        td["submission1_id"] = each["submission1_id"]
        res.append(td)
    return res

def wrap_bug_descriptions(text: str) -> str:
    start_keyword = "Bug Descriptions:"
    start_idx = text.find(start_keyword)
    if start_idx == -1:
        return ""
    desc_start = start_idx + len(start_keyword)
    desc_text = text[desc_start:].strip()
    desc_list = [line.strip() for line in desc_text.split('\n') if line.strip()]
    wrapped_desc = [f"<DESCRIPTION>{desc}</DESCRIPTION>" for desc in desc_list]
    final_output = "<DESCRIPTIONS_LIST>\n" + "\n".join(wrapped_desc) + "\n</DESCRIPTIONS_LIST>"

    return final_output

def example1():
    example = {
        "user_id": "u531436689",
        "problem_id": "p03714",
        "submission1_id": "s358041239",
        "code1": "import math,string,itertools,fractions,heapq,collections,re,array,bisect,sys,random,time,copy,functools\nfrom collections import deque\n\nsys.setrecursionlimit(10**7)\ninf = 10**20\nmod = 10**9 + 7\n\nDR = [1, -1, 0, 0]\nDC = [0, 0, 1, -1]\n\ndef LI(): return [int(x) for x in sys.stdin.readline().split()]\ndef LI_(): return [int(x)-1 for x in sys.stdin.readline().split()]\ndef LF(): return [float(x) for x in sys.stdin.readline().split()]\ndef LS(): return sys.stdin.readline().split()\ndef I(): return int(sys.stdin.readline())\ndef F(): return float(sys.stdin.readline())\ndef S(): return input()\n     \ndef main():\n    N = I()\n    A = LI()\n    wakeme = N\n    Aleftsum = [0 for _ in range(3*N+1)]\n    leftA = [x for x in A[:N]]\n    heapq.heapify(leftA)\n    subsum = sum(leftA)\n    Aleftsum[wakeme] = subsum\n    for i in range(N):\n        heapq.heappush(leftA, A[wakeme + i])\n        subsum += A[wakeme + i]\n        subsum -= heapq.heappop(leftA)\n        Aleftsum[wakeme+i+1] = subsum\n\n    Arightsum = [0 for _ in range(3*N+1)]\n    rightA = [-x for x in A[-N:]]\n    heapq.heapify(rightA)\n    subsum = sum(rightA)\n    wakeme = 2*N\n    Arightsum[wakeme] = -subsum\n    for i in range(1, N+1):\n        heapq.heappush(rightA, -A[wakeme-i])\n        subsum -= A[wakeme - i]\n        subsum -= heapq.heappop(rightA)\n        Arightsum[wakeme - i] = -subsum\n    ans = -inf\n    for i in range(N, 2*N):\n        ans = max(ans, Aleftsum[i] - Arightsum[i])\n    print(ans)\nmain()\n\n",
        "code2": "import math,string,itertools,fractions,heapq,collections,re,array,bisect,sys,random,time,copy,functools\nfrom collections import deque\n\nsys.setrecursionlimit(10**7)\ninf = 10**20\nmod = 10**9 + 7\n\nDR = [1, -1, 0, 0]\nDC = [0, 0, 1, -1]\n\ndef LI(): return [int(x) for x in sys.stdin.readline().split()]\ndef LI_(): return [int(x)-1 for x in sys.stdin.readline().split()]\ndef LF(): return [float(x) for x in sys.stdin.readline().split()]\ndef LS(): return sys.stdin.readline().split()\ndef I(): return int(sys.stdin.readline())\ndef F(): return float(sys.stdin.readline())\ndef S(): return input()\n     \ndef main():\n    N = I()\n    A = LI()\n    wakeme = N\n    Aleftsum = [0 for _ in range(3*N+1)]\n    leftA = [x for x in A[:N]]\n    heapq.heapify(leftA)\n    subsum = sum(leftA)\n    Aleftsum[wakeme] = subsum\n    for i in range(N):\n        heapq.heappush(leftA, A[wakeme + i])\n        subsum += A[wakeme + i]\n        subsum -= heapq.heappop(leftA)\n        Aleftsum[wakeme+i+1] = subsum\n\n    Arightsum = [0 for _ in range(3*N+1)]\n    rightA = [-x for x in A[-N:]]\n    heapq.heapify(rightA)\n    subsum = sum(rightA)\n    wakeme = 2*N\n    Arightsum[wakeme] = -subsum\n    for i in range(1, N+1):\n        heapq.heappush(rightA, -A[wakeme-i])\n        subsum -= A[wakeme - i]\n        subsum -= heapq.heappop(rightA)\n        Arightsum[wakeme - i] = -subsum\n    ans = -inf\n    for i in range(N, 2*N+1):\n        ans = max(ans, Aleftsum[i] - Arightsum[i])\n    print(ans)\nmain()\n\n",
        "code1_bug_descriptions": "1. The loop for considering possible split points ends one index too early. In the original code, the loop `for i in range(N, 2*N)` stops at `2*N - 1`, but the maximum valid split point is `2*N`. The correct loop should be `range(N, 2*N + 1)` to include `i = 2*N` as a valid split point.",
        "code1_lines": 51,
        "code1_test_status": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1],
        "user_consistency": 0.98,
        "top_k_results": [{"MATCH_SCORE": 0.95556640625, "RetrievalCode": "import heapq\ndef main():\n    N = int(input())\n    A = list(map(int, input().split()))\n    fl = [i for i in A[:N]]\n    f = [sum(A[:N])]\n    heapq.heapify(fl)\n    ll = [-i for i in A[2*N:]]\n    l = [sum(A[2*N:])]\n    heapq.heapify(ll)\n    for i in range(N):\n        s = f[-1]\n        if A[N+i] > fl[0]:\n            s = s - fl[0] + A[N+i]\n            heapq.heappushpop(fl, A[N+i])\n        f.append(s)\n        s = l[-1]\n        if - A[2*N-1-i] > ll[0]:\n            s = s + ll[0] + A[2*N-1-i]\n            heapq.heappushpop(ll, -A[2*N-1-i])\n        l.append(s)\n    r = f[0] - l[-1]\n    for i in range(N):\n        r = max(r, f[i] - l[-1-i])\n    return r\nprint(main())\n\n", "RetrievalSubmission1_id": "s506053544"}, {"MATCH_SCORE": 0.95556640625, "RetrievalCode": "import heapq\ndef main():\n    N = int(input())\n    A = list(map(int, input().split()))\n    fl = [i for i in A[:N]]\n    f = [sum(A[:N])]\n    heapq.heapify(fl)\n    ll = [-i for i in A[2*N:]]\n    l = [sum(A[2*N:])]\n    heapq.heapify(ll)\n    for i in range(N):\n        s = f[-1]\n        if A[N+i] > fl[0]:\n            s = s - fl[0] + A[N+i]\n            heapq.heappushpop(fl, A[N+i])\n        f.append(s)\n        s = l[-1]\n        if - A[2*N-1-i] > ll[0]:\n            s = s + ll[0] + A[2*N-1-i]\n            heapq.heappushpop(ll, -A[2*N-1-i])\n        l.append(s)\n    r = -pow(10, 100)\n    for i in range(N):\n        r = max(r, f[i] - l[-1-i])\n    return r\nprint(main())\n\n", "RetrievalSubmission1_id": "s062626531"}, {"MATCH_SCORE": 0.9541015625, "RetrievalCode": "N=int(input())\nA=list(map(int,input().split()))\nh1=A[:N]\nL=[0 for i in range(N+1)]\nL[0]=sum(h1)\nimport heapq\nheapq.heapify(h1)\nfor i in range(N):\n  heapq.heappush(h1,A[N+i])\n  heapq.heappop(h1)\n  L[i+1]=sum(h1)\nh=A[2*N:]\nh2=[-i for i in h]\nR=[0 for i in range(N+1)]\nR[N]=-sum(h2)\nheapq.heapify(h2)\nfor i in range(N):\n  heapq.heappush(h2,-A[2*N-1-i])\n  heapq.heappop(h2)\n  R[N-i-1]=-sum(h2)\nimport math\nans=-math.inf\nfor i in range(N):\n  ans=max(ans,L[i]-R[i])\nprint(ans)\n", "RetrievalSubmission1_id": "s453281679"}, {"MATCH_SCORE": 0.947265625, "RetrievalCode": "from heapq import heappop,heappush,heapify\nn=int(input())\na=list(map(int,input().split()))\nleft=[0]*n\nlst=a[:n]\ns=sum(lst)\nheapify(lst)\nfor i in range(n):\n    heappush(lst,a[n+i])\n    x=heappop(lst)\n    if i==0:\n        left[0]=s+a[n]-x\n    else:\n        left[i]=left[i-1]+a[n+i]-x\nleft=[s]+left\nright=[0]*n\nlst=[]\nfor i in range(2*n,3*n):\n    lst.append(-a[i])\ns=-sum(lst)\nheapify(lst)\nfor i in range(n):\n    heappush(lst,-a[2*n-1+i])\n    x=-heappop(lst)\n    if i==0:\n        right[n-1]=s+a[2*n-1]-x\n    else:\n        right[n-1-i]=right[n-i]+a[2*n-1-i]-x\nright+=[s]\nans=-float(\"inf\")\nfor i in range(n):\n    ans=max(ans,left[i]-right[i])\nprint(ans)\n", "RetrievalSubmission1_id": "s062131069"}, {"MATCH_SCORE": 0.94677734375, "RetrievalCode": "from heapq import heappop,heappush,heapify\nn=int(input())\na=list(map(int,input().split()))\nleft=[0]*n\nlst=a[:n]\ns=sum(lst)\nheapify(lst)\nfor i in range(n):\n    heappush(lst,a[n+i])\n    x=heappop(lst)\n    if i==0:\n        left[0]=s+a[n]-x\n    else:\n        left[i]=left[i-1]+a[n+i]-x\nleft=[s]+left\nright=[0]*n\nlst=[]\nfor i in range(2*n,3*n):\n    lst.append(-a[i])\ns=-sum(lst)\nheapify(lst)\nfor i in range(n):\n    heappush(lst,-a[2*n-1-i])\n    x=-heappop(lst)\n    if i==0:\n        right[n-1]=s+a[2*n-1]-x\n    else:\n        right[n-1-i]=right[n-i]+a[2*n-1-i]-x\nright+=[s]\nans=-float(\"inf\")\nfor i in range(n):\n    ans=max(ans,left[i]-right[i])\nprint(ans)\n", "RetrievalSubmission1_id": "s724831910"}],
        "retrieval_code_bug_desc": [{"re_submission_id": "s506053544", "bug_description": "1. The loop iterating over the range `N` in the buggy code should actually iterate over `N+1` in the correct code. This is because the sequence `f` and `l` have `N+1` elements after the loop, and the comparison needs to include the last element in both sequences to correctly calculate the maximum possible score.", "origin_generated_text": "Bug Explanations:\n<EXPLANATIONS_LIST>\n    <EXPLANATION>\n    The loop iterating over the range `N` in the buggy code should actually iterate over `N+1` in the correct code. This is because the sequence `f` and `l` have `N+1` elements after the loop, and the comparison needs to include the last element in both sequences to correctly calculate the maximum possible score.\n    </EXPLANATION>\n</EXPLANATIONS_LIST>"}, {"re_submission_id": "s062626531", "bug_description": "1. The initial value of `r` in the buggy code is set to `-pow(10, 100)`, which is unnecessarily large and could lead to incorrect results or inefficiencies. In the correct code, `r` is initialized to `f[0] - l[-1]`, which is a more reasonable starting point based on the first possible score calculation.\n2. The loop in the buggy code iterates `N` times, which misses the last possible score calculation when `i = N`. The correct code iterates `N+1` times, ensuring all possible scores are considered, including the scenario where no elements are removed from the first and last segments.", "origin_generated_text": "Bug Explanations:\n<EXPLANATIONS_LIST>\n    <EXPLANATION>\n    The initial value of `r` in the buggy code is set to `-pow(10, 100)`, which is unnecessarily large and could lead to incorrect results or inefficiencies. In the correct code, `r` is initialized to `f[0] - l[-1]`, which is a more reasonable starting point based on the first possible score calculation.\n    </EXPLANATION>\n    <EXPLANATION>\n    The loop in the buggy code iterates `N` times, which misses the last possible score calculation when `i = N`. The correct code iterates `N+1` times, ensuring all possible scores are considered, including the scenario where no elements are removed from the first and last segments.\n    </EXPLANATION>\n</EXPLANATIONS_LIST>"}, {"re_submission_id": "s453281679", "bug_description": "1. In the buggy code, the sum of the elements in the heap `h1` is recalculated using `sum(h1)` in each iteration of the loop. This is inefficient and incorrect because it does not account for the changes in the heap correctly. The correct code maintains a running sum `sum1` and updates it incrementally by adding the new element and subtracting the popped element, which ensures the sum reflects the current state of the heap.\n2. Similarly, for the second half of the sequence, the buggy code recalculates the sum using `sum(h2)` in each iteration, which is inefficient and incorrect. The correct code uses a running sum `sum2` and updates it incrementally by adding the new element and subtracting the popped element (after converting it back from negative), ensuring the sum reflects the current state of the heap.\n3. The loop for calculating the maximum score in the buggy code iterates from `0` to `N-1`, which misses the last possible combination of elements. The correct code iterates from `0` to `N`, ensuring all combinations are considered, including the last one.", "origin_generated_text": "```xml\n<EXPLANATIONS_LIST>\n  <EXPLANATION>\n    In the buggy code, the sum of the elements in the heap `h1` is recalculated using `sum(h1)` in each iteration of the loop. This is inefficient and incorrect because it does not account for the changes in the heap correctly. The correct code maintains a running sum `sum1` and updates it incrementally by adding the new element and subtracting the popped element, which ensures the sum reflects the current state of the heap.\n  </EXPLANATION>\n  <EXPLANATION>\n    Similarly, for the second half of the sequence, the buggy code recalculates the sum using `sum(h2)` in each iteration, which is inefficient and incorrect. The correct code uses a running sum `sum2` and updates it incrementally by adding the new element and subtracting the popped element (after converting it back from negative), ensuring the sum reflects the current state of the heap.\n  </EXPLANATION>\n  <EXPLANATION>\n    The loop for calculating the maximum score in the buggy code iterates from `0` to `N-1`, which misses the last possible combination of elements. The correct code iterates from `0` to `N`, ensuring all combinations are considered, including the last one.\n  </EXPLANATION>\n</EXPLANATIONS_LIST>\n```"}, {"re_submission_id": "s062131069", "bug_description": "1. In the buggy code, the loop iterating over the range(n) for calculating the maximum score does not include the last element of the 'left' and 'right' lists. This is because the range is set to n, whereas it should be n+1 to include the additional element added to both lists. This causes the final comparison to miss the potential maximum score that includes the last element.\n2. In the buggy code, the index used for accessing elements in the 'right' list during its construction is incorrect. Specifically, the index used in the heappush operation is '2*n-1+i', which should be '2*n-1-i' to correctly iterate over the elements in reverse order. This mistake leads to incorrect values being pushed into the heap, affecting the calculation of the 'right' list.", "origin_generated_text": "```xml\n<EXPLANATIONS_LIST>\n    <EXPLANATION>\n        In the buggy code, the loop iterating over the range(n) for calculating the maximum score does not include the last element of the 'left' and 'right' lists. This is because the range is set to n, whereas it should be n+1 to include the additional element added to both lists. This causes the final comparison to miss the potential maximum score that includes the last element.\n    </EXPLANATION>\n    <EXPLANATION>\n        In the buggy code, the index used for accessing elements in the 'right' list during its construction is incorrect. Specifically, the index used in the heappush operation is '2*n-1+i', which should be '2*n-1-i' to correctly iterate over the elements in reverse order. This mistake leads to incorrect values being pushed into the heap, affecting the calculation of the 'right' list.\n    </EXPLANATION>\n</EXPLANATIONS_LIST>\n```"}, {"re_submission_id": "s724831910", "bug_description": "1. The loop iterating over the range `n` in the final section of the buggy code should iterate over `range(n+1)` instead. This is because the `left` and `right` lists have `n+1` elements, and the loop needs to consider all possible splits of the sequence to find the maximum score. The correct code uses `range(n+1)` to ensure all elements are considered.", "origin_generated_text": "Bug Explanations:\n<EXPLANATIONS_LIST>\n    <EXPLANATION>\n    The loop iterating over the range `n` in the final section of the buggy code should iterate over `range(n+1)` instead. This is because the `left` and `right` lists have `n+1` elements, and the loop needs to consider all possible splits of the sequence to find the maximum score. The correct code uses `range(n+1)` to ensure all elements are considered.\n    </EXPLANATION>\n</EXPLANATIONS_LIST>"}]
    }
    tokenizer = AutoTokenizer.from_pretrained("./Qwen2.5-Coder-32B-Instruct")
    system_prompt = """You are a skilled programmer experienced in debugging and providing optimal code fixes. 
 You are provided with a programming problem and a piece of buggy code written in python.  
 you are required to perform the following tasks:
 1. Fix the Buggy Code: Fix the buggy code to meet the problem's requirements, ensuring that the changes are minimal to preserve the original structure and logic as much as possible.
 2. Provide Bug Descriptions: Provide clear and complete point-by-point descriptions of the bugs present in the buggy code. Please do not include any fix suggestions in each description. Each bug description should be wrapped with <DESCRIPTION></DESCRIPTION> tags. All bug descriptions should be wrapped in <DESCRIPTIONS_LIST></DESCRIPTIONS_LIST> tags.
 <task></task>
 Please answer in the following format:
  Repaired Code:
  ```python
  ```
  Bug Descriptions:
  <DESCRIPTIONS_LIST></DESCRIPTIONS_LIST>"""
    problem_description = load_problem("./dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json")
    prompt = construct_model_prompt(example, "python", tokenizer=tokenizer, max_input_tokens=10000, system_prompt=system_prompt, without_context=False, prompt_mode="NoRef", problem_description=problem_description, topk=5, retrieval_data_dict=None)
    print(prompt)

if __name__ == "__main__":
    example1()
