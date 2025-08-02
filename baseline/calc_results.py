import os
import argparse
import json
import numpy as np

from utils.jsonTools import load_json
from tqdm import tqdm
import numpy as np
import warnings
warnings.filterwarnings("ignore")

def calculate_avg_consistency(data):
    """Calculate the average of all consistency"""
    total_consistency = 0
    for entry in data:
        if entry['repaired_consistency'] == 1.0:
            total_consistency += 0
        else:
            total_consistency += entry['repaired_consistency']

    avg_consistency = total_consistency / len(data)
    return avg_consistency

def calculate_correct_rate(data):
    """Correct rate of calculation"""
    correct_count = 0
    for entry in data:
        if entry["code_test_score"] == entry["TotalScore"] and entry["TotalScore"] != 0:
            correct_count += 1
    correct_rate = correct_count / len(data)
    return correct_rate

def calculate_improvement_rate(data):
    improve_score = 0
    for each in data:
        flag = 1
        m = 0
        n = 0
        code1_test_status = each["code1_test_status"]
        code_test_status = each["code_test_status"]
        for i in code1_test_status:
            if i != 1:
                m += 1
        for j in range(len(code_test_status)):
            if code1_test_status[j] == 1 and code_test_status[j] != 1:
                flag =0
                break
            elif code1_test_status[j] != 1 and code_test_status[j] == 1:
                n += 1
        improve_score += flag * (n / m)
    return improve_score / len(data)

def calculate_F1(data):
    total_F1 = 0
    total_MicroP = 0
    total_MicroR = 0

    for each in data:
        eval_list = np.array([[1 if value == "YES" else 0 for value in row] for row in each["GPT_Eval"]])
        TP = np.sum(np.any(eval_list == 1, axis=1))
        FP = len(eval_list[0]) - np.sum(np.any(eval_list == 1, axis=0))
        FN = len(eval_list) - TP

        MicroP = (TP / (TP + FP)) if (TP + FP) != 0 else 0
        MicroR = TP / (TP + FN)
        MicroF = (2 * MicroP * MicroR) / (MicroP + MicroR) if MicroP + MicroR != 0 else 0

        total_MicroP += MicroP
        total_MicroR += MicroR
        total_F1 += MicroF
    P = total_MicroP / len(data)
    R =total_MicroR / len(data)
    F = total_F1 / len(data)
    return P, R, F

def calculate_correctF1(data):
    total_F1 = 0
    total_MicroP = 0
    total_MicroR = 0

    for each in data:
        if each["code_test_score"] == each["TotalScore"] and each["TotalScore"] != 0:
            eval_list = np.array([[1 if value == "YES" else 0 for value in row] for row in each["GPT_Eval"]])
            TP = np.sum(np.any(eval_list == 1, axis=1))
            FP = len(eval_list[0]) - np.sum(np.any(eval_list == 1, axis=0))
            FN = len(eval_list) - TP

            MicroP = (TP / (TP + FP)) if (TP + FP) != 0 else 0
            MicroR = TP / (TP + FN)
            MicroF = (2 * MicroP * MicroR) / (MicroP + MicroR) if MicroP + MicroR != 0 else 0

            total_MicroP += MicroP
            total_MicroR += MicroR
            total_F1 += MicroF
        else:
            total_MicroP += 0
            total_MicroR += 0
            total_F1 += 0
    P = total_MicroP / len(data)
    R =total_MicroR / len(data)
    F = total_F1 / len(data)
    return P, R, F


def main(data):
    avg_retention_rate = calculate_avg_consistency(data)
    correct_rate = calculate_correct_rate(data)
    improvement_rate = calculate_improvement_rate(data)
    P, R, F1 = calculate_F1(data)
    CP, CR, CF1= calculate_correctF1(data)

    print(f">>> ✅ Average consistency: {avg_retention_rate:.4f}")
    print(f">>> ✅ Accuracy: {correct_rate:.4f}")
    print(f">>> ✅ Improvement rate: {improvement_rate:.4f}")
    print(f">>> 🌈 Precision: {P:.4f}, Recall: {R:.4f}, F1-score: {F1:.4f}")
    print(f">>> 🌈 Correct Precision: {CP:.4f}, Correct Recall: {CR:.4f}, Correct F1-score: {CF1:.4f}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--json_file", type=str, help="Json file Path")
    args = parser.parse_args()
    data = load_json(args.json_file)
    main(data)
