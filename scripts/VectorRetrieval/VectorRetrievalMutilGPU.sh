QUERY_FILE="data/ALL/origin_dataset_407.json"
RETRIEVAL_FILE="dataset/Filtered_pair/code1_Added_testScode_pairs/Exec_test_processed_pair.json"
MODE="code1+diff-code1"
OUTPUT_FILE="data/ALL/Qwen3-Embedding-0.6BData/${MODE}.json"
TOPK=5
GPUS="1"
MODE_TYPE="qwen_vllm"

CUDA_VISIBLE_DEVICES=0 python -m VectorRetrieval.VectorRetrieval_vllm \
  --query_file "$QUERY_FILE" \
  --retrieval_file "$RETRIEVAL_FILE" \
  --mode "$MODE" \
  --model_type "${MODE_TYPE}" \
  --topk "$TOPK" \
  --output_file "$OUTPUT_FILE" \
  --gpus "$GPUS"