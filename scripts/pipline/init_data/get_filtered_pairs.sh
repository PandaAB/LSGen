#!/bin/bash

JSON_AVAILABLE_PID_DIR="dataset/Filtered_pair/ALL_pairs"
OUTPUT_DIR="dataset/Filtered_pair/Processed_pair"
MODE="test"  # Can be "train" or "dev" or "test" or "demo"
THRESHOLD=0.65
LINES_THRESHOLD=0
EXEC_EVAL=true
EXEC_EVAL_Write_prefix_url="dataset/Filtered_pair/code2_Added_testScore_pairs/"
TEMP_OUTPUT_DIR="dataset/Filtered_pair/temp/"
FINAL_OUTPUT="dataset/Filtered_pair/code1_Added_testScode_pairs/"

# Declare an associative array for mode-specific JSON files
declare -A MODE_FILES=(
    ["train"]="train_pair.json"
    ["dev"]="dev_pair.json"
    ["test"]="test_pair.json"
    ["demo"]="demo_pair.json"
)

if [[ -n "${MODE_FILES[$MODE]}" ]]; then
    JSON_FILE="$JSON_AVAILABLE_PID_DIR/${MODE_FILES[$MODE]}"
    OUTPUT_FILE="$OUTPUT_DIR/${MODE}_processed_pair.json"
else
    echo -e "\033[31mError: Unsupported MODE '$MODE'. Please set it to 'train', 'dev', or 'test'.\033[0m"
    exit 1
fi

echo "JSON File: $JSON_FILE"
echo "Output File: $OUTPUT_FILE"
echo "Threshold: $THRESHOLD"
echo "Lines Threshold: $LINES_THRESHOLD"
echo "IS SAVE: $IS_SAVE"
echo -e "\033[33mProcessing $MODE............\033[0m"

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Output directory does not exist. Creating it: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

python3 -m ProcessData.Get_Filtered_Data.filter_submission_pairs \
    --json_file "$JSON_FILE" \
    --output_file "$OUTPUT_FILE" \
    --mode "$MODE" \
    --threshold "$THRESHOLD" \
    --lines_threshold "$LINES_THRESHOLD" \
    --IS_SAVE

if [ $? -eq 0 ]; then
    echo -e "\033[32mFilter_submission_pairs executed successfully.\033[0m"
else
    echo -e "\033[31mFilter_submission_pairs execution failed.\033[0m"
    exit 1
fi

if [ "$EXEC_EVAL" = true ]; then
    echo -e "\033[33mStarting Evaluation...\033[0m"
    python3 -m Eval.Eval_Code_Generation-Mprocess \
        --EvalOject_Path "$OUTPUT_FILE" \
        --Write_prefix_url "$EXEC_EVAL_Write_prefix_url" \
        --CODE_KEY "code2"
    
    echo -e "\033[32mEvaluation completed successfully.\033[0m"

    TEMP_OUTPUT_FILE="${TEMP_OUTPUT_DIR}${MODE}_processed_pair.json"

    python3 -m ProcessData.Get_Filtered_Data.filter_submission_pairs \
    --json_file "${EXEC_EVAL_Write_prefix_url}Exec_${MODE}_processed_pair.json" \
    --output_file "$TEMP_OUTPUT_FILE" \
    --mode "$MODE" \
    --threshold "$THRESHOLD" \
    --lines_threshold "$LINES_THRESHOLD" \
    --IS_EVAL

    python3 -m Eval.Eval_Code_Generation-Mprocess \
        --EvalOject_Path "$TEMP_OUTPUT_FILE" \
        --Write_prefix_url "$FINAL_OUTPUT" \
        --CODE_KEY "code1"

    if [ -f "$TEMP_OUTPUT_FILE" ]; then
        echo -e "\033[33mDeleting output file: $TEMP_OUTPUT_FILE\033[0m"
        rm "$TEMP_OUTPUT_FILE"
        if [ $? -eq 0 ]; then
            echo -e "\033[32mFile deleted successfully.\033[0m"
        else
            echo -e "\033[31mFailed to delete the file.\033[0m"
        fi
    fi

    if [ $? -eq 0 ]; then
        echo -e "\033[32mEvaluation filter completed successfully.\033[0m"
    else
        echo -e "\033[31mEvaluation filter failed.\033[0m"
    fi
else
    echo -e "\033[33mSkipping evaluation step...\033[0m"
fi
