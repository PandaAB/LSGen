QUERY_FILE="data/ALL/origin_dataset_407.json"
RETRIEVAL_FILE="dataset/Filtered_pair/code1_Added_testScode_pairs/Exec_test_processed_pair.json"
OUTPUT_FILE="baseline/PyDex/RetrievalPyDex.json"
TOPK=5

python -m baseline.PyDex.similarity_from_hamming \
  --query_file "$QUERY_FILE" \
  --retrieval_file "$RETRIEVAL_FILE" \
  --topk "$TOPK" \
  --output_file "$OUTPUT_FILE"