#!/bin/bash

ALL_DATA_DIR="dataset/Project_CodeNet"
JSON_AVAILABLE_PID_DIR="dataset/Available_PID"
OUTPUT_DIR="dataset/Filtered_pair/ALL_pairs"
LANGUAGE="Python"
CSV_FOLDER="$ALL_DATA_DIR/metadata"
DATA_FOLDER="$ALL_DATA_DIR/data"
MODE="test" # "train" or "dev" or "test" or "demo"
THRESHOLD=0.5
LINES_THRESHOLD=20

declare -A MODE_FILES=(
    ["train"]="train_Available_PID.json"
    ["dev"]="dev_Available_PID.json"
    ["test"]="test_Available_PID.json"
    ["demo"]="demo_Available_PID.json"
)

if [[ -n "${MODE_FILES[$MODE]}" ]]; then
    JSON_FILE="$JSON_AVAILABLE_PID_DIR/${MODE_FILES[$MODE]}"
    OUTPUT_FILE="$OUTPUT_DIR/${MODE}_pair.json"
else
    echo -e "\033[31mError: Unsupported MODE '$MODE'. Please set it to 'train', 'dev', or 'test'.\033[0m"
    exit 1
fi

# Print input parameter
echo "Language: $LANGUAGE"
echo "CSV Folder: $CSV_FOLDER"
echo "Data Folder: $DATA_FOLDER"
echo "Problem ID JSON File: $JSON_FILE"
echo "Output File: $OUTPUT_FILE"
echo "Threshold: $THRESHOLD"
echo "Lines Threshold: $LINES_THRESHOLD"
echo -e "\033[34mProcessing $MODE............\033[0m"

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Output directory does not exist. Creating it: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

python -m ProcessData.Get_Filtered_Data.get_pairs \
    --csv_folder "$CSV_FOLDER" \
    --data_folder "$DATA_FOLDER" \
    --json_file "$JSON_FILE" \
    --output_file "$OUTPUT_FILE" \
    --language "$LANGUAGE" \
    --threshold "$THRESHOLD" \
    --lines_threshold "$LINES_THRESHOLD"

if [ $? -eq 0 ]; then
    # echo "Script executed successfully."
    echo -e "\033[32mScript executed successfully.\033[0m"
else
    # echo "Script execution failed."
    echo -e "\033[31mScript execution failed.\033[0m"
    exit 1
fi
# echo "Processing completed successfully!"