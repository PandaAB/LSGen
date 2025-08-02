from typing import Sequence
from utils.jsonTools import load_json, tojson
import argparse
from tqdm import tqdm

def normalized_hamming_distance(a: Sequence, b: Sequence) -> float:
    if len(a) != len(b):
        raise ValueError("The lengths of the input sequences must be the same!")
    n = len(a)
    diff = sum(1 for x, y in zip(a, b) if x != y)
    return diff / n

def similarity_from_hamming(a: Sequence, b: Sequence) -> float:
    return 1.0 - normalized_hamming_distance(a, b)

def retrieval_similarity(data: list, retrieval_file: str, topk: int) -> list:
    pool = load_json(retrieval_file)
    for record in tqdm(data):
        status1 = record["code1_test_status"]
        sims = []
        for entry in pool:
            if entry["user_id"] == record["user_id"]:
                continue
            status2 = entry["code_test_status"]
            try:
                sim = similarity_from_hamming(status1, status2)
            except ValueError:
                continue
            sims.append((sim, entry))
        sims.sort(key=lambda x: x[0], reverse=True)
        topk_entries = [(_, entry) for _, entry in sims[:topk]]
        top_k_results = []
        for e in topk_entries:
            top_k_results.append(
                {
                    "MATCH_SCORE": e[0],
                    "RetrievalCode": e[1]["code1"],
                    "RetrievalCodeCorrect": e[1]["code2"],
                    "RetrievalSubmission1_id": e[1]["submission1_id"]
                }
            )
        record["top_k_results"] = top_k_results
    return data

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Retrieval')
    parser.add_argument('--query_file', type=str, default='python', help='query file')
    parser.add_argument('--retrieval_file', type=str, default='gpt-4o-ca', help='retrieval file')
    parser.add_argument("--output_file", type=str, default='./test.json', help='output file path')
    parser.add_argument("--topk", default=5, help="Topk")
    args = parser.parse_args()

    data = load_json(args.query_file)
    results = retrieval_similarity(data, args.retrieval_file, int(args.topk))
    tojson(results, args.output_file)