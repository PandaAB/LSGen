INPUT_FILE="./baseline/results/AblationStudy/RetrievalMethod/EVAL/top5/CodeLlama-7b-Instruct-hf/Init/Execution/Exec_Res_code1-code2.json"
OUTPUT_DIR="./baseline/results/AblationStudy/RetrievalMethod/EVAL/top5/CodeLlama-7b-Instruct-hf/Init/EvaluateDesc"
OUTPUT_FILE="Init_Res_code1-code2_2.json"
MODEL="gpt-4o-mini-ca"
NUM_THREADS=10

python -m Eval.Evaluate_DescriptionsRetry \
  --input_file "$INPUT_FILE" \
  --output_dir "$OUTPUT_DIR" \
  --output_file "$OUTPUT_FILE" \
  --model "$MODEL" \
  --num_threads "$NUM_THREADS"
