QUERY_FILE="baseline/results/Retriever/gpt-4o-ca/UnixCoder/code1+diff-code2/Refine/top5/Refine3/Error_Res_code1+diff-code2.json"
RETRIEVAL_FILE="dataset/Filtered_pair/code1_Added_testScode_pairs/ReDiff_Exec_test_processed_pair.json"
MODE="code1+diff-code2"
OUTPUT_FILE="baseline/results/Retriever/gpt-4o-ca/UnixCoder/code1+diff-code2/Refine/top5/Refine3/ReRetrieval_code1+diff-code2.json"
TOPK=5
GPUS="1"
MODE_TYPE="unixcoder"

CUDA_VISIBLE_DEVICES=0 python -m VectorRetrieval.VectorRetrievalSecondStage \
  --query_file "$QUERY_FILE" \
  --retrieval_file "$RETRIEVAL_FILE" \
  --mode "$MODE" \
  --model_type "${MODE_TYPE}" \
  --topk "$TOPK" \
  --output_file "$OUTPUT_FILE" \
  --gpus "$GPUS"