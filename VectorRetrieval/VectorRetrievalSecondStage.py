import os
import json
import argparse
import torch
import torch.nn.functional as F
from tqdm import tqdm

from torch import Tensor
from transformers import AutoTokenizer, AutoModel
from UniXcoder.unixcoder import UniXcoder
from utils.jsonTools import load_json, tojson
# import faiss
from vllm import LLM

def build_problemid_index(dataset):
    index = {}
    for item in dataset:
        pid = item["problem_id"]
        if pid not in index:
            index[pid] = []
        index[pid].append(item)
    return index

def calculate_similarity(query_vecs, candidate_vecs):
    query_vecs = F.normalize(query_vecs, p=2, dim=1)
    candidate_vecs = F.normalize(candidate_vecs, p=2, dim=1)
    return torch.matmul(query_vecs, candidate_vecs.t())  # (query_size, candidate_size)

def retrieve_topk(query_vec, candidate_vecs, topk=5):
    sim = calculate_similarity(query_vec.unsqueeze(0), candidate_vecs)
    topk_scores, topk_indices = torch.topk(sim, topk, dim=-1)
    return topk_scores.squeeze(0), topk_indices.squeeze(0)

def get_core_model(model):
    return model.module if isinstance(model, torch.nn.DataParallel) else model

# ---------- Unixcoder ----------
def encode_unixcoder(model, device, code_list, max_length=512, batch_size=32):
    # 兼容 DataParallel
    core_model = get_core_model(model)
    embeddings = []
    for i in range(0, len(code_list), batch_size):
        batch = code_list[i:i+batch_size]
        inputs = core_model.tokenize(batch, max_length=max_length, mode="<encoder-only>", padding=True)
        source_ids = torch.tensor(inputs).to(device)
        with torch.no_grad():
            _, batch_embeddings = model(source_ids)
        # embeddings.append(batch_embeddings.cpu())
        embeddings.append(batch_embeddings)
    return torch.cat(embeddings, dim=0)

# ---------- Qwen3 ------------
def encode_qwen(tokenizer, model, device, code_list, max_length=8192, batch_size=2):
    embeddings = []
    for i in range(0, len(code_list), batch_size):
        batch = code_list[i:i+batch_size]
        encoded = tokenizer(batch, padding=True, truncation=True, max_length=max_length, return_tensors="pt")
        for k, v in encoded.items():
            encoded[k] = v.to(device)
        with torch.no_grad():
            out = model(**encoded)
            vecs = last_token_pool(out.last_hidden_state, encoded['attention_mask'])
            embeddings.append(vecs)
    return torch.cat(embeddings, dim=0)

# ---------- Qwen3 vLLM ------------
def encode_qwen_vllm(tokenizer, model, device, code_list, max_length=8192, batch_size=4):
    embeddings = []
    for i in range(0, len(code_list), batch_size):
        batch = code_list[i : i + batch_size]
        outputs = model.embed(batch)
        vecs = torch.stack(
            [
                torch.tensor(out.outputs.embedding, dtype=torch.float32, device=device)
                for out in outputs
            ],
            dim=0,
        )
        embeddings.append(vecs)
    return torch.cat(embeddings, dim=0)

# ---------- pooling ------------
def last_token_pool(last_hidden_states: Tensor,
                 attention_mask: Tensor) -> Tensor:
    left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    else:
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]
# -----------------------------------

# ---------- inf-retriever-v1 ------------
def encode_infv1(tokenizer, model, device, code_list, max_length=8192, batch_size=2):
    embeddings = []
    for i in range(0, len(code_list), batch_size):
        batch = code_list[i:i+batch_size]
        encoded = tokenizer(batch, padding=True, truncation=True, max_length=max_length, return_tensors="pt")
        for k, v in encoded.items():
            encoded[k] = v.to(device)
        with torch.no_grad():
            out = model(**encoded)
            vecs = last_token_pool(out.last_hidden_state, encoded['attention_mask'])
            embeddings.append(vecs)
    return torch.cat(embeddings, dim=0)

# ---------- inf-retriever-v1 vLLM ------------
def encode_infv1_vllm(tokenizer, model, device, code_list, max_length=8192, batch_size=4):
    embeddings = []
    for i in range(0, len(code_list), batch_size):
        batch = code_list[i : i + batch_size]
        outputs = model.embed(batch)
        vecs = torch.stack(
            [
                torch.tensor(out.outputs.embedding, dtype=torch.float32, device=device)
                for out in outputs
            ],
            dim=0,
        )
        embeddings.append(vecs)
    return torch.cat(embeddings, dim=0)


def main(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if args.model_type == "unixcoder":
        print("Using UniXcoder model...")
        model = UniXcoder("microsoft/unixcoder-base")
        if args.gpus and len(args.gpus.split(',')) > 1:
            model = torch.nn.DataParallel(model)
        model.to(device).eval()
        encoder = lambda codes: encode_unixcoder(model, device, codes)

    elif args.model_type == "qwen":
        print("Using Qwen3-Embedding model...")
        tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True, padding_side="left")
        qwen_model = AutoModel.from_pretrained('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True).cuda()
        if args.gpus and len(args.gpus.split(",")) > 1:
            qwen_model = torch.nn.DataParallel(qwen_model)
        # qwen_model.to(device).eval()
        qwen_model.to(device).eval()
        encoder = lambda codes: encode_qwen(tokenizer, qwen_model, device, codes)
    elif args.model_type == "qwen_vllm":
        print("Using Qwen3-Embedding model with vLLM...")
        qwen_llm = LLM(
            model="Qwen/Qwen3-Embedding-0.6B",
            task="embed",
            trust_remote_code=True,
            enforce_eager=True,
        )
        encoder = lambda codes: encode_qwen_vllm(None, qwen_llm, device, codes)
    elif args.model_type == "infv1":
        print("Using inf-retriever-v1 model...")
        tokenizer = AutoTokenizer.from_pretrained("infly/inf-retriever-v1", trust_remote_code=True, padding_side="left")
        infv1_model = AutoModel.from_pretrained("infly/inf-retriever-v1", trust_remote_code=True)
        if args.gpus and len(args.gpus.split(",")) > 1:
            infv1_model = torch.nn.DataParallel(infv1_model)
        infv1_model.to(device).eval()
        encoder = lambda codes: encode_infv1(tokenizer, infv1_model, device, codes)
    elif args.model_type == "infv1_vllm":
        print("Using inf-retriever-v1 model with vLLM...")
        infv1_llm = LLM(
            model="infly/inf-retriever-v1",
            task="embed",
            trust_remote_code=True,
            enforce_eager=True,
        )
        encoder = lambda codes: encode_infv1_vllm(None, infv1_llm, device, codes)
    else:
        raise ValueError(f"Unsupported model_type: {args.model_type}")

    retrieval_data = load_json(args.retrieval_file)
    retrieval_index = build_problemid_index(retrieval_data)
    query_data = load_json(args.query_file)

    results = []
    for item in tqdm(query_data, desc="Processing queries"):
        pid = item["problem_id"]
        if pid not in retrieval_index:
            print(">>> !!!No items!!!")
            continue
        candidates = [c for c in retrieval_index[pid]
                      if c.get("submission1_id") != item.get("submission1_id")]
        
        if args.mode == "code1+diff-code2":
            query_code = item["code1"]
            code1_list = [c["code1"] for c in candidates]
            code2_list = [c["code2"] for c in candidates]
            code1_vecs = encoder(code1_list)
            code2_vecs = encoder(code2_list)
            modify_vecs = code2_vecs - code1_vecs

            query_vec = encoder([query_code])[0]
            adjusted_queries = query_vec.unsqueeze(0) + modify_vecs
            sim_mat = calculate_similarity(adjusted_queries, code2_vecs)

            code_content = item["code_content"]
            content_vec = encoder([code_content])[0]
            error_vecs = content_vec.unsqueeze(0) - query_vec.unsqueeze(0)

            error_code1_vecs = error_vecs + code1_vecs
            error_sim_mat = calculate_similarity(error_code1_vecs, code2_vecs)


            diag_sim = sim_mat.diag()
            diag_error = error_sim_mat.diag()
            combined_scores = diag_sim + (1.0 - diag_error)


            k = min(args.topk, combined_scores.size(0))
            topk_scores, topk_indices = torch.topk(combined_scores, k)

        topk_results = []
        topk_scores = topk_scores.cpu().tolist()
        topk_indices = topk_indices.cpu().tolist()
        for s, idx in zip(topk_scores, topk_indices):
            topk_results.append({
                "MATCH_SCORE": float(s),
                "RetrievalCode": candidates[idx]["code1"],
                "RetrievalSubmission1_id": candidates[idx]["submission1_id"]
            })
        item["top_k_results"] = topk_results
        results.append(item)

    tojson(results, args.output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code Retrieval with Unixcoder & Qwen3-Embedding")
    parser.add_argument("--query_file", type=str, required=True, help="Path to query dataset (repairDataset)")
    parser.add_argument("--retrieval_file", type=str, required=True, help="Path to retrieval dataset (Filtered_pair)")
    parser.add_argument("--mode", type=str, choices=["code1+diff-code2"], required=True, help="Retrieval mode")
    parser.add_argument("--model_type", choices=["unixcoder","qwen","qwen_vllm","infv1","infv1_vllm"], required=True, help="Choose encoding model: unixcoder, qwen or snowflake")
    parser.add_argument("--topk", type=int, default=5, help="Number of top-k results to retrieve")
    parser.add_argument("--output_file", type=str, required=True, help="Path to output file")
    parser.add_argument("--gpus", type=str, help="Comma separated list of GPU ids to use, e.g. '0' or '0,1'")
    args = parser.parse_args()
    try:
        main(args)
    finally:
        import torch.distributed as dist
        if dist.is_initialized():
            dist.destroy_process_group()
