#!/bin/bash

MODE="test"
BUG_CODE_FILE="dataset/repairDataset/RepairData-PythonLevel/Dataset/${MODE}.json"
JSON_DIR="dataset/Filtered_pair/code1_Added_testScode_pairs"
RETRIEVAL_CODE_NAME="Exec_${MODE}_processed_pair.json"
RETRIEVAL_CODE_FILE="${JSON_DIR}/${RETRIEVAL_CODE_NAME}"
OUTPUT_DIR="dataset/RetrievaledData"
LANGUAGE="python"
k=5
# The weights are test point match score, data stream match score, AST match score, and BM25 match score. However, the result of data stream match score has some randomness. Therefore, set it to 0
weight="1111"
 m 
OUTPUT_FILE="$OUTPUT_DIR/Retrievaled_${weight}_${MODE}_Top${k}_1.json"

echo "Language: $LANGUAGE"
echo "Top-k: $k"
echo "Retrieval Code File: $RETRIEVAL_CODE_FILE"
echo "BUG CODE FILE: $BUG_CODE_FILE"
echo "Output File: $OUTPUT_FILE"
echo -e "\033[34mRetrievaling Code............\033[0m"

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Output directory does not exist. Creating it: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

#python -m RetrievalRefCode.Get_Retrieval_ScoreMultiProcess \
python -m RetrievalRefCode.Get_Retrieval_ScoreTopk \
    --bug_code_file "$BUG_CODE_FILE" \
    --retrieval_code_file "$RETRIEVAL_CODE_FILE" \
    --output_file "$OUTPUT_FILE" \
    --language "$LANGUAGE" \
    --weight "$weight" \
    --top_k "$k"

if [ $? -eq 0 ]; then
    echo -e "\033[32mScript executed successfully.\033[0m"
else
    echo -e "\033[31mScript execution failed.\033[0m"
    exit 1
fi