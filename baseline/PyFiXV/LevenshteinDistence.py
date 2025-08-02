import Levenshtein
import argparse
from utils.jsonTools import load_json, tojson
from tqdm import tqdm


def retrieval_similarity(data: list, retrieval_file: str, topk: int) -> list:
    pool = load_json(retrieval_file)
    for record in tqdm(data, desc="Retrieval"):
        query_diff = record["diff_code"]
        distences_list = []
        for entry in pool:
            if entry["user_id"] == record["user_id"]:
                continue
            retrieval_diff = entry["diff_code"]
            try:
                distence = Levenshtein.distance(query_diff, retrieval_diff)
            except ValueError:
                continue
            distences_list.append((distence, entry))
        # The editing distance increases from small to large
        distences_list.sort(key=lambda x: x[0])
        topk_entries = [(_, entry) for _, entry in distences_list[:topk]]
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
    parser.add_argument('--query_file', type=str,help='query file')
    parser.add_argument('--retrieval_file', type=str, help='retrieval file')
    parser.add_argument("--output_file", type=str, default='./test.json', help='output file path')
    parser.add_argument("--topk", default=5, help="Topk")
    args = parser.parse_args()

    data = load_json(args.query_file)
    results = retrieval_similarity(data, args.retrieval_file, int(args.topk))
    tojson(results, args.output_file)